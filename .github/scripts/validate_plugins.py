#!/usr/bin/env python3
"""Structural and safety checks for the craft-io plugin marketplace.

Runs with no third-party dependencies so it works in CI and locally:

    python3 .github/scripts/validate_plugins.py

Exits non-zero on the first class of problem it finds. The executable-component
check is a security control: this marketplace is public, and every plugin in it
is meant to stay declarative — markdown and JSON only, nothing that runs.
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
# MCP server config key documented there EXCEPT `trust` — that one is explicitly
# called out as unsupported for extensions (it would let an extension silently
# bypass tool-call confirmations), so it is deliberately left out of this set.
ALLOWED_GEMINI_MCP_KEYS = {
    "command", "url", "httpUrl", "args", "headers", "env", "cwd", "timeout",
    "includeTools", "excludeTools", "authProviderType", "targetAudience",
    "targetServiceAccount", "oauth",
}

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


def check_marketplace() -> list[Path]:
    mp_path = ROOT / ".claude-plugin" / "marketplace.json"
    mp = load_json(mp_path)
    if not mp:
        return []

    for field in ("name", "owner", "plugins"):
        if field not in mp:
            err(f"marketplace.json: missing required field `{field}`")
    if "description" not in mp:
        warn("marketplace.json: no `description` — it renders in the /plugin Discover pane")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(mp.get("name", ""))):
        err(f"marketplace.json: name {mp.get('name')!r} must be kebab-case")
    if "name" not in (mp.get("owner") or {}):
        err("marketplace.json: owner.name is required")

    plugin_root = (mp.get("metadata") or {}).get("pluginRoot", ".")
    dirs = []
    for entry in mp.get("plugins", []):
        name = entry.get("name")
        if not name:
            err("marketplace.json: a plugin entry has no `name`")
            continue
        if "source" not in entry:
            err(f"marketplace.json: plugin `{name}` has no `source`")
            continue
        if "version" in entry:
            err(
                f"marketplace.json: plugin `{name}` sets `version`, which pins it. "
                "Omit it so each commit ships as a new version."
            )
        d = (ROOT / plugin_root / str(entry["source"])).resolve()
        if not d.is_dir():
            err(f"marketplace.json: plugin `{name}` source does not resolve to a directory: {d}")
        else:
            dirs.append(d)
    return dirs


def check_mcp_servers(rel: Path, servers: dict, url_key: str = "url") -> None:
    """Shared MCP-server validation. url_key lets callers with a different transport
    field name (e.g. Gemini's `httpUrl`) reuse the same rules."""
    for server, cfg in servers.items():
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
        url = cfg.get(url_key, "") or cfg.get("url", "")
        if url and not url.startswith("https://"):
            err(f"{rel}: MCP server {server!r} url is not https: {url}")


def check_plugin(d: Path) -> None:
    rel = d.relative_to(ROOT)
    manifest = load_json(d / ".claude-plugin" / "plugin.json")
    if manifest:
        if "name" not in manifest:
            err(f"{rel}: plugin.json missing `name`")
        if "description" not in manifest:
            err(f"{rel}: plugin.json missing `description`")
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

    gemini_path = d / "gemini-extension.json"
    if gemini_path.exists():
        gem = load_json(gemini_path) or {}
        if "name" not in gem:
            err(f"{rel}: gemini-extension.json missing `name`")
        if "description" not in gem:
            err(f"{rel}: gemini-extension.json missing `description`")
        gem_servers = gem.get("mcpServers") or {}
        check_mcp_servers(rel, gem_servers, url_key="httpUrl")
        for server, cfg in gem_servers.items():
            for key in set(cfg) - ALLOWED_GEMINI_MCP_KEYS:
                warn(f"{rel}: gemini-extension.json MCP server {server!r} has unrecognized key `{key}`")
        # Cross-check endpoint parity with .mcp.json instead of raw JSON equality —
        # the two manifests use different field names (url vs httpUrl) by design.
        for server, cfg in gem_servers.items():
            claude_cfg = claude_mcp_servers.get(server)
            if claude_cfg is None:
                err(f"{rel}: gemini-extension.json declares MCP server {server!r} not present in .mcp.json")
                continue
            gem_url = cfg.get("httpUrl") or cfg.get("url")
            claude_url = claude_cfg.get("url")
            if gem_url and claude_url and gem_url != claude_url:
                err(
                    f"{rel}: gemini-extension.json server {server!r} endpoint {gem_url!r} "
                    f"does not match .mcp.json's {claude_url!r} — keep them in sync."
                )
        ctx = gem.get("contextFileName")
        if ctx and not (d / ctx).is_file():
            err(f"{rel}: gemini-extension.json contextFileName {ctx!r} does not exist")

    cursor_plugin_path = d / ".cursor-plugin" / "plugin.json"
    if cursor_plugin_path.exists():
        cp = load_json(cursor_plugin_path) or {}
        if "name" not in cp:
            err(f"{rel}: .cursor-plugin/plugin.json missing `name`")
        if "description" not in cp:
            err(f"{rel}: .cursor-plugin/plugin.json missing `description`")
        # Field names per cursor/plugins' own manifests (continual-learning, gmail):
        # `skills` points at a directory, `mcpServers` at an MCP config file — both
        # resolved relative to the plugin root (one level up from .cursor-plugin/),
        # confirmed by fetching real plugin.json files from that repo.
        for field, expect_dir in (("skills", True), ("mcpServers", False)):
            ref = cp.get(field)
            if not ref:
                continue
            target = (d / ref).resolve()
            ok = target.is_dir() if expect_dir else target.is_file()
            if not ok:
                err(
                    f"{rel}: .cursor-plugin/plugin.json `{field}` path {ref!r} does not resolve to a "
                    f"{'directory' if expect_dir else 'file'}: {target}"
                )

    cursor_mp_path = d / ".cursor-plugin" / "marketplace.json"
    if cursor_mp_path.exists():
        load_json(cursor_mp_path)  # just structural/JSON validity for now

    skills = sorted((d / "skills").glob("*/"))
    if not skills:
        err(f"{rel}: no skills found under skills/")
    for s in skills:
        check_skill(s)


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


def main() -> int:
    dirs = check_marketplace()
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
