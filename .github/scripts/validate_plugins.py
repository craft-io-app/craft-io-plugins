#!/usr/bin/env python3
"""Structural and safety checks for the craft-io plugin marketplace.

Runs with no third-party dependencies so it works in CI and locally:

    python3 .github/scripts/validate_plugins.py

Exits non-zero on the first class of problem it finds. The executable-component
check is a security control: this marketplace is public, and every plugin in it
is meant to stay declarative — markdown and JSON only, nothing that runs.

The same plugin ships to Claude Code, Cursor and Gemini CLI from one set of
assets. Each client reads a different manifest, so every rule below is applied
to every manifest that can reach a user, including the ones that point at a
shared file by path rather than declaring servers inline.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Plugin components that execute code or reach outside the plugin. Adding any of
# these changes the trust model of the marketplace, so it takes a deliberate
# edit to this list plus a security review.
EXECUTABLE_COMPONENTS = ("hooks", "bin", "agents", "monitors", ".lsp.json", "settings.json")

ALLOWED_MCP_KEYS = {"type", "url", "command", "args", "env", "headers"}

# Gemini CLI's extension mcpServers schema (docs/extensions/reference.md +
# docs/tools/mcp-server.md in google-gemini/gemini-cli). Extensions support every
# MCP server config key documented there EXCEPT `trust` — see FORBIDDEN_MCP_KEYS.
ALLOWED_GEMINI_MCP_KEYS = {
    "command", "url", "httpUrl", "args", "headers", "env", "cwd", "timeout",
    "includeTools", "excludeTools", "authProviderType", "targetAudience",
    "targetServiceAccount", "oauth",
}

# Not merely unrecognized — actively unsafe here, so these fail the build rather
# than warn. `trust` bypasses every tool-call confirmation, and that confirmation
# is the last control a user still has once a server is installed (SECURITY.md).
# Gemini documents it as unsupported for extensions, so shipping one would be
# inert today; CI holds the intent regardless of which client honours it.
FORBIDDEN_MCP_KEYS = {"trust"}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(f"{path.relative_to(ROOT)}: missing")
    except json.JSONDecodeError as e:
        err(f"{path.relative_to(ROOT)}: invalid JSON — {e}")
    return None


def frontmatter(path: Path) -> dict[str, str]:
    """Parse top-level `key:` pairs out of YAML frontmatter. Good enough to check
    which keys are present and to read single-line scalars."""
    text = path.read_text()
    if not text.startswith("---\n"):
        err(f"{path.relative_to(ROOT)}: no YAML frontmatter")
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        err(f"{path.relative_to(ROOT)}: unterminated frontmatter")
        return {}
    out: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def check_marketplace(rel_path: Path, client: str, required: bool) -> list[Path]:
    """Validate one marketplace catalog. Claude Code and Cursor both read a
    repo-root `<dot-dir>/marketplace.json` listing plugins by subdirectory, so
    the same rules apply to both."""
    mp_path = ROOT / rel_path
    if not mp_path.exists():
        if required:
            err(f"{rel_path}: missing")
        return []
    mp = load_json(mp_path)
    if not mp:
        return []

    for field in ("name", "owner", "plugins"):
        if field not in mp:
            err(f"{rel_path}: missing required field `{field}`")
    if "description" not in mp and "description" not in (mp.get("metadata") or {}):
        warn(f"{rel_path}: no `description` — it renders in the {client} plugin browser")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(mp.get("name", ""))):
        err(f"{rel_path}: name {mp.get('name')!r} must be kebab-case")
    if "name" not in (mp.get("owner") or {}):
        err(f"{rel_path}: owner.name is required")

    plugin_root = (mp.get("metadata") or {}).get("pluginRoot", ".")
    dirs = []
    for entry in mp.get("plugins", []):
        name = entry.get("name")
        if not name:
            err(f"{rel_path}: a plugin entry has no `name`")
            continue
        if "source" not in entry:
            err(f"{rel_path}: plugin `{name}` has no `source`")
            continue
        if "version" in entry:
            err(
                f"{rel_path}: plugin `{name}` sets `version`, which pins it. "
                "Omit it so each commit ships as a new version."
            )
        source = str(entry["source"])
        # `source` names the plugin's own subdirectory. "./" points at whatever
        # directory the catalog happens to sit in, which is the repository root
        # here — it would install the whole repo rather than the plugin.
        if source.strip("/") in ("", "."):
            err(
                f"{rel_path}: plugin `{name}` source {source!r} does not name a plugin "
                "directory. Use the path to the plugin, e.g. `plugins/craft-guru`."
            )
            continue
        d = (ROOT / plugin_root / source).resolve()
        if not d.is_relative_to(ROOT):
            err(f"{rel_path}: plugin `{name}` source {source!r} escapes the repository")
            continue
        if not d.is_dir():
            err(f"{rel_path}: plugin `{name}` source does not resolve to a directory: {d}")
        else:
            dirs.append(d)
    return dirs


def check_mcp_servers(rel: Path, servers: dict, url_key: str = "url") -> None:
    """Shared MCP-server validation. url_key lets callers with a different transport
    field name (e.g. Gemini's `httpUrl`) reuse the same rules.

    Every manifest that can put a server in front of a user goes through here —
    including one that reaches its servers through a path reference, because a
    rule only enforced on the file we happen to ship is not enforced at all."""
    for server, cfg in servers.items():
        if not isinstance(cfg, dict):
            err(f"{rel}: MCP server {server!r} is not an object")
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", server):
            err(
                f"{rel}: MCP server name {server!r} must be lower-case kebab-case. Other "
                "characters are rewritten in the mcp__<server>__<tool> prefix, so user "
                "permission rules stop matching."
            )
        if "command" in cfg:
            err(
                f"{rel}: MCP server {server!r} declares `command`, which runs a local process. "
                "Only remote http/sse servers belong in this marketplace."
            )
        url = cfg.get(url_key) or cfg.get("url") or ""
        if not url and "command" not in cfg:
            err(f"{rel}: MCP server {server!r} declares no `{url_key}` — it would never connect")
        if url and not url.startswith("https://"):
            err(f"{rel}: MCP server {server!r} url is not https: {url}")
        for key in sorted(FORBIDDEN_MCP_KEYS & set(cfg)):
            err(
                f"{rel}: MCP server {server!r} sets `{key}`, which bypasses tool-call "
                "confirmation. That confirmation is the control SECURITY.md promises users."
            )


def check_path_ref(rel: Path, field: str, base: Path, ref: str, expect_dir: bool):
    """Resolve a manifest path reference and prove it stays inside the plugin.

    Cursor's own authoring guidance is that manifest paths stay relative and
    within the plugin directory — no absolute paths, no `..` traversal."""
    if Path(ref).is_absolute() or ref.startswith("~"):
        err(f"{rel}: `{field}` path {ref!r} must be relative to the plugin directory")
        return None
    target = (base / ref).resolve()
    if not target.is_relative_to(base.resolve()):
        err(f"{rel}: `{field}` path {ref!r} escapes the plugin directory: {target}")
        return None
    if not (target.is_dir() if expect_dir else target.is_file()):
        err(
            f"{rel}: `{field}` path {ref!r} does not resolve to a "
            f"{'directory' if expect_dir else 'file'}: {target}"
        )
        return None
    return target


def check_endpoint_parity(rel: Path, label: str, servers: dict, url_key: str, baseline: dict) -> None:
    """Prove a client manifest reaches the same servers, at the same URLs, as
    `.mcp.json`. Checked in both directions: a server added on one side only is
    a silent capability gap for that client's users, not a cosmetic drift.

    Compares the resolved URL rather than raw JSON, since the manifests use
    different field names (`url` vs `httpUrl`) by design."""
    for server, cfg in servers.items():
        base_cfg = baseline.get(server)
        if base_cfg is None:
            err(f"{rel}: {label} declares MCP server {server!r} not present in .mcp.json")
            continue
        url = cfg.get(url_key) or cfg.get("url")
        base_url = base_cfg.get("url")
        if url and base_url and url != base_url:
            err(
                f"{rel}: {label} server {server!r} endpoint {url!r} "
                f"does not match .mcp.json's {base_url!r} — keep them in sync."
            )
    for server in baseline:
        if server not in servers:
            err(
                f"{rel}: .mcp.json declares MCP server {server!r} that {label} is missing — "
                "that client's users would silently never get it."
            )


def check_plugin(d: Path) -> None:
    rel = d.relative_to(ROOT)
    manifest = load_json(d / ".claude-plugin" / "plugin.json")
    if manifest:
        check_manifest_identity(rel / ".claude-plugin" / "plugin.json", manifest, d)
        if "version" in manifest:
            err(
                f"{rel}: plugin.json sets `version`, which pins the plugin — users who already "
                "installed it never receive new skills. Omit it so the commit SHA is the version."
            )
        if "license" not in manifest:
            warn(f"{rel}: plugin.json has no `license`")

    for comp in EXECUTABLE_COMPONENTS:
        if (d / comp).exists():
            err(
                f"{rel}: contains `{comp}`. Plugins in this marketplace are declarative — "
                "markdown and JSON only. Adding an executable component needs a security review."
            )

    mcp_path = d / ".mcp.json"
    claude_mcp_servers: dict = {}
    if mcp_path.exists():
        mcp = load_json(mcp_path) or {}
        claude_mcp_servers = mcp.get("mcpServers") or {}
        check_mcp_servers(rel, claude_mcp_servers)
        for server, cfg in claude_mcp_servers.items():
            for key in set(cfg) - ALLOWED_MCP_KEYS:
                warn(f"{rel}: MCP server {server!r} has unrecognized key `{key}`")

    check_gemini_extension(d, rel, claude_mcp_servers)
    check_cursor_plugin(d, rel, claude_mcp_servers)

    skills = sorted((d / "skills").glob("*/"))
    if not skills:
        err(f"{rel}: no skills found under skills/")
    for s in skills:
        check_skill(s)


def check_manifest_identity(rel: Path, manifest: dict, d: Path) -> None:
    """`name` and `description` are required in every client's manifest, and the
    name identifies the plugin to the user. Gemini CLI additionally expects it to
    match the extension directory name; letting the three manifests drift apart
    means the same plugin installs under different names per client."""
    if "name" not in manifest:
        err(f"{rel}: missing `name`")
    elif manifest["name"] != d.name:
        err(f"{rel}: name {manifest['name']!r} does not match the plugin directory {d.name!r}")
    if "description" not in manifest:
        err(f"{rel}: missing `description`")


def check_gemini_extension(d: Path, rel: Path, claude_mcp_servers: dict) -> None:
    gemini_path = d / "gemini-extension.json"
    if not gemini_path.exists():
        return
    gem_rel = rel / "gemini-extension.json"
    gem = load_json(gemini_path) or {}
    check_manifest_identity(gem_rel, gem, d)
    # Unlike the Claude manifest, Gemini documents `version` as a manifest field
    # and `gemini extensions update` compares against it, so it is required here.
    # See CONTRIBUTING.md for why the two clients differ.
    if "version" not in gem:
        err(f"{gem_rel}: missing `version` — Gemini CLI resolves updates against it")

    gem_servers = gem.get("mcpServers") or {}
    check_mcp_servers(gem_rel, gem_servers, url_key="httpUrl")
    for server, cfg in gem_servers.items():
        for key in set(cfg) - ALLOWED_GEMINI_MCP_KEYS - FORBIDDEN_MCP_KEYS:
            warn(f"{gem_rel}: MCP server {server!r} has unrecognized key `{key}`")
    check_endpoint_parity(gem_rel, "gemini-extension.json", gem_servers, "httpUrl", claude_mcp_servers)

    ctx = gem.get("contextFileName")
    if ctx:
        check_path_ref(gem_rel, "contextFileName", d, ctx, expect_dir=False)


def check_cursor_plugin(d: Path, rel: Path, claude_mcp_servers: dict) -> None:
    stray_mp = d / ".cursor-plugin" / "marketplace.json"
    if stray_mp.exists():
        err(
            f"{rel}: .cursor-plugin/marketplace.json belongs at the repository root, next to "
            ".claude-plugin/marketplace.json. Cursor resolves a catalog's `source` entries "
            "from the repo root, so a catalog nested inside a plugin is never found."
        )

    cursor_plugin_path = d / ".cursor-plugin" / "plugin.json"
    if not cursor_plugin_path.exists():
        return
    cp_rel = rel / ".cursor-plugin" / "plugin.json"
    cp = load_json(cursor_plugin_path) or {}
    check_manifest_identity(cp_rel, cp, d)
    # Cursor resolves plugin versions from the manifest rather than the commit,
    # so unlike the Claude manifest this one must pin. See CONTRIBUTING.md.
    if "version" not in cp:
        err(f"{cp_rel}: missing `version` — Cursor resolves plugin updates against it")

    for key in EXECUTABLE_COMPONENTS:
        if key in cp:
            err(
                f"{cp_rel}: declares `{key}`, an executable component. Plugins in this "
                "marketplace are declarative — markdown and JSON only."
            )

    # Field names per cursor/plugins' own manifests (third_party/gmail, apollo-io):
    # `skills` points at a directory, `mcpServers` at an MCP config file — both
    # resolved relative to the plugin root (one level up from .cursor-plugin/).
    if cp.get("skills"):
        check_path_ref(cp_rel, "skills", d, cp["skills"], expect_dir=True)

    ref = cp.get("mcpServers")
    if not ref:
        return
    target = check_path_ref(cp_rel, "mcpServers", d, ref, expect_dir=False)
    if not target:
        return
    # The path resolving is not the check that matters. Cursor loads whatever is
    # in that file, so the file's contents go through exactly the same rules as
    # an inline declaration — otherwise this manifest is a way around all of them.
    target_rel = target.relative_to(ROOT)
    cursor_mcp = load_json(target) or {}
    cursor_servers = cursor_mcp.get("mcpServers")
    if not isinstance(cursor_servers, dict) or not cursor_servers:
        err(f"{cp_rel}: `mcpServers` file {ref!r} declares no `mcpServers` object")
        return
    check_mcp_servers(target_rel, cursor_servers)
    for server, cfg in cursor_servers.items():
        for key in set(cfg) - ALLOWED_MCP_KEYS:
            warn(f"{target_rel}: MCP server {server!r} has unrecognized key `{key}`")
    check_endpoint_parity(cp_rel, f"`mcpServers` file {ref}", cursor_servers, "url", claude_mcp_servers)


def check_skill(s: Path) -> None:
    rel = s.relative_to(ROOT)
    md = s / "SKILL.md"
    if not md.is_file():
        err(f"{rel}: no SKILL.md")
        return

    fm = frontmatter(md)
    if "description" not in fm:
        err(f"{rel}: SKILL.md frontmatter has no `description`")
    if fm.get("name") and fm["name"] != s.name.rstrip("/"):
        err(f"{rel}: frontmatter name {fm['name']!r} does not match directory {s.name!r}")

    # Keep frontmatter inside the Agent Skills spec so the same skill loads in
    # Claude Code, on claude.ai and through the Skills API. Anything else is a
    # hard upload error outside Claude Code.
    spec_fields = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    for key in set(fm) - spec_fields:
        err(
            f"{rel}: frontmatter key `{key}` is outside the Agent Skills spec, so uploading this "
            f"skill to claude.ai fails. Allowed: {', '.join(sorted(spec_fields))}"
        )
    if "allowed-tools" in fm:
        err(
            f"{rel}: `allowed-tools` pre-approves tools without prompting — it does not restrict "
            "them. Don't ship it in a public plugin."
        )

    body = md.read_text()
    if "## Trust boundary" not in body:
        err(
            f"{rel}: no `## Trust boundary` section. Every skill that reads Craft content needs "
            "the standing instruction that Craft content is data, not instructions."
        )
    for pattern, msg in (
        (r"(?i)\buse proactively\b|\btrigger proactively\b",
         "description tells Claude to trigger proactively, which fires the skill on unrelated work"),
        (r"(?i)keep this quiet|don't cite .* to the user|do not tell the user",
         "instructs the model to withhold its reasoning from the user"),
    ):
        if re.search(pattern, body):
            err(f"{rel}: {msg}")


def check_catalog_parity(catalogs: dict[str, list[Path]]) -> None:
    """Every client's catalog must list the same plugins. A plugin present in one
    and not another ships to some users and not others, with nothing to say so."""
    baseline_name, baseline = next(iter(catalogs.items()))
    for name, dirs in list(catalogs.items())[1:]:
        for missing in sorted(set(baseline) - set(dirs)):
            err(f"{name}: does not list `{missing.name}`, which {baseline_name} ships")
        for extra in sorted(set(dirs) - set(baseline)):
            err(f"{name}: lists `{extra.name}`, which {baseline_name} does not ship")


def main() -> int:
    catalogs = {
        ".claude-plugin/marketplace.json": check_marketplace(
            Path(".claude-plugin") / "marketplace.json", "Claude Code", required=True
        ),
    }
    cursor_catalog = Path(".cursor-plugin") / "marketplace.json"
    if (ROOT / cursor_catalog).exists():
        catalogs[str(cursor_catalog)] = check_marketplace(cursor_catalog, "Cursor", required=False)
    check_catalog_parity(catalogs)

    dirs = catalogs[".claude-plugin/marketplace.json"]
    for d in dirs:
        check_plugin(d)

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"ok — {len(dirs)} plugin(s) validated, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
