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
    if mcp_path.exists():
        mcp = load_json(mcp_path) or {}
        for server, cfg in (mcp.get("mcpServers") or {}).items():
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", server):
                err(
                    f"{rel}: MCP server name {server!r} must be lower-case kebab-case. Other "
                    "characters are rewritten in the mcp__<server>__<tool> prefix, so user "
                    "permission rules stop matching."
                )
            if "command" in cfg:
                err(
                    f"{rel}: MCP server {server!r} declares `command`, which runs a local process. "
                    "Only remote `http`/`sse` servers belong in this marketplace."
                )
            url = cfg.get("url", "")
            if url and not url.startswith("https://"):
                err(f"{rel}: MCP server {server!r} url is not https: {url}")
            for key in set(cfg) - ALLOWED_MCP_KEYS:
                warn(f"{rel}: MCP server {server!r} has unrecognized key `{key}`")

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
