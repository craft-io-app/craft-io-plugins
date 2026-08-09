#!/usr/bin/env python3
"""Require a version bump when shared assets change.

    python3 .github/scripts/check_version_bump.py [base-ref]

The skills and the connector are written once and read by every client, but the
clients do not agree on what a version is. Claude Code resolves a plugin's
version from the commit SHA, so a merge to `main` reaches existing installs on
its own. Cursor and Gemini CLI resolve updates against the manifest `version`
field, so for those two a new skill ships only if that field changes.

That asymmetry is documented in CONTRIBUTING.md, and documentation is not a
control: adding a skill and forgetting the bump passes every other check in this
repo, and the skill then reaches Claude Code users and nobody else, silently.
This closes that gap — change a shared asset, bump the two manifests that need
it, or the build goes red.

Exits 0 when the base ref cannot be resolved, printing why. That is a real gap
in coverage, not a pass, so it says so rather than staying quiet.
"""

# `X | None` annotations are 3.10+ at runtime; this repo's checks must run on the
# python3 a contributor already has, which on current macOS is 3.9.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Manifests whose client resolves updates from the `version` field. The Claude
# manifest is deliberately absent: it must not carry a version at all.
VERSIONED_MANIFESTS = (".cursor-plugin/plugin.json", "gemini-extension.json")

# Assets shared by every client. A change to one of these is a change to what
# every client ships, whether or not any manifest was touched.
SHARED_ASSETS = ("skills/", ".mcp.json")

errors: list[str] = []


def git(*args: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


def version_at(ref: str, path: str) -> tuple[bool, str | None]:
    """Return (existed, version) for a manifest at a git ref."""
    raw = git("show", f"{ref}:{path}")
    if raw is None:
        return False, None
    try:
        return True, json.loads(raw).get("version")
    except json.JSONDecodeError:
        return True, None


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    if git("rev-parse", "--verify", f"{base}^{{commit}}") is None:
        print(f"notice: base ref {base!r} does not resolve — version-bump check SKIPPED, not passed.")
        print("        In CI, check out with fetch-depth: 0 so the base branch is available.")
        return 0

    changed = git("diff", "--name-only", f"{base}...HEAD")
    if changed is None:
        print(f"notice: could not diff against {base} — version-bump check SKIPPED, not passed.")
        return 0
    changed_files = [line for line in changed.splitlines() if line]

    for plugin_dir in sorted((ROOT / "plugins").glob("*/")):
        rel = f"plugins/{plugin_dir.name}"
        touched = sorted(
            f for f in changed_files
            if any(f.startswith(f"{rel}/{asset}") for asset in SHARED_ASSETS)
        )
        if not touched:
            continue

        for manifest in VERSIONED_MANIFESTS:
            path = f"{rel}/{manifest}"
            if not (ROOT / path).is_file():
                continue
            existed, old = version_at(base, path)
            if not existed:
                continue  # new manifest — nothing to bump from
            new = json.loads((ROOT / path).read_text()).get("version")
            if old == new:
                errors.append(
                    f"{path}: version is still {new!r}, but this change touches shared assets "
                    f"({', '.join(touched)}). Cursor and Gemini CLI resolve updates from this "
                    "field, so their users would never receive the change. Bump it."
                )

    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"\n{len(errors)} error(s)")
        return 1
    print(f"ok — shared assets and client manifest versions are consistent with {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
