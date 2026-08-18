#!/usr/bin/env python3
"""Require a version bump when a shipped asset changes.

    python3 .github/scripts/check_version_bump.py [base-ref] [--fix]

`--fix` raises the versions this run would otherwise complain about, so nobody —
person or agent — has to hold "which of three manifests needs what" in their
head. CI never passes it: the gate stays a gate.

The skills and the connector are written once and read by every client, but the
clients do not agree on what a version is. Claude Code resolves a plugin's
version from the commit SHA, so no field here needs touching for it. Cursor and
Gemini CLI resolve updates against the manifest `version` field, so for those two
a change ships only if that field changes.

That asymmetry is documented in CONTRIBUTING.md, and documentation is not a
control: adding a skill and forgetting the bump passes every other check in this
repo, and the skill then reaches Claude Code users and nobody else, silently.
This closes that gap — change a shipped asset, bump the manifests that carry it,
or the build goes red.

Exits 0 when the base ref cannot be resolved, printing why. That is a real gap
in coverage, not a pass, so it says so rather than staying quiet.
"""

# `X | None` annotations are 3.10+ at runtime; this repo's checks must run on the
# python3 a contributor already has, which on current macOS is 3.9.
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Manifests whose client resolves updates from the `version` field, and the name
# to blame in the error. The Claude manifest is deliberately absent from both: it
# must not carry a version at all.
CLIENT = {
    ".cursor-plugin/plugin.json": "Cursor",
    "gemini-extension.json": "Gemini CLI",
}

# What each client actually ships to a user, and which manifests must therefore
# show a new version when it moves. A change here is a change to what that client
# ships, whether or not any manifest was touched.
#
# GEMINI.md is Gemini-only, and mapped only to Gemini on purpose. It loads as
# always-on context in every session the extension is enabled, so editing it
# changes what every Gemini user's agent sees — but Cursor never reads it, and
# demanding a Cursor bump for a file Cursor cannot see teaches contributors to
# bump the field without asking who the change is for.
SHIPPED_ASSETS = {
    "skills/": (".cursor-plugin/plugin.json", "gemini-extension.json"),
    ".mcp.json": (".cursor-plugin/plugin.json", "gemini-extension.json"),
    "GEMINI.md": ("gemini-extension.json",),
}

errors: list[str] = []
fixed: list[str] = []


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


def ordered(version: str | None) -> tuple[int, ...] | None:
    """A dotted-integer version as a comparable tuple, or None if it isn't one.

    Both clients compare versions to decide whether an update exists, so a
    version that moves backwards reads as "no update" and ships to nobody — the
    same silent failure a missing bump causes. Anything that isn't plain dotted
    integers is left to the differs-from-base rule alone rather than guessed at.
    """
    if not isinstance(version, str):
        return None
    parts = version.split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def next_after(version: str | None) -> str | None:
    """The smallest version above `version`, or None if it isn't dotted integers."""
    parts = ordered(version)
    if not parts:
        return None
    return ".".join(str(p) for p in parts[:-1] + (parts[-1] + 1,))


def set_version(path: Path, value: str) -> bool:
    """Rewrite just the version string, leaving the rest of the file byte-identical.

    A json.dumps round-trip would reformat a hand-maintained manifest, so this
    edits the one value in place. It refuses when the file holds more than one
    `version` key, rather than guessing which was meant.
    """
    text = path.read_text()
    pattern = r'("version"\s*:\s*)"[^"]*"'
    if len(re.findall(pattern, text)) != 1:
        return False
    path.write_text(re.sub(pattern, lambda m: m.group(1) + json.dumps(value), text, count=1))
    return True


def main() -> int:
    argv = sys.argv[1:]
    fix = "--fix" in argv
    positional = [a for a in argv if not a.startswith("--")]
    base = positional[0] if positional else "origin/main"

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

        # manifest -> the changed files that oblige it to carry a new version
        required: dict[str, set[str]] = {}
        for asset, manifests in SHIPPED_ASSETS.items():
            touched = {f for f in changed_files if f.startswith(f"{rel}/{asset}")}
            if not touched:
                continue
            for manifest in manifests:
                required.setdefault(manifest, set()).update(touched)

        for manifest, touched in sorted(required.items()):
            path = f"{rel}/{manifest}"
            if not (ROOT / path).is_file():
                continue
            existed, old = version_at(base, path)
            if not existed:
                continue  # new manifest — nothing to bump from
            new = json.loads((ROOT / path).read_text()).get("version")
            old_t, new_t = ordered(old), ordered(new)

            if old == new:
                problem = (
                    f"version is still {new!r}, but this change touches what it ships "
                    f"({', '.join(sorted(touched))}). {CLIENT[manifest]} resolves updates from "
                    "this field, so its users would never receive the change. Bump it."
                )
            elif old_t and new_t and new_t <= old_t:
                problem = (
                    f"version went backwards, {old!r} -> {new!r}. {CLIENT[manifest]} compares "
                    "this field to decide an update exists, so a lower version ships to nobody "
                    "just as surely as no bump at all."
                )
            else:
                continue

            if not fix:
                errors.append(f"{path}: {problem}")
                continue

            target = next_after(old)
            if target is None or not set_version(ROOT / path, target):
                errors.append(
                    f"{path}: {problem} Could not fix it automatically — set the version by hand."
                )
            else:
                fixed.append(f"{path}: {new!r} -> {target!r}")

    for f in fixed:
        print(f"bumped: {f}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"\n{len(errors)} error(s)")
        return 1
    if fixed:
        print(f"\n{len(fixed)} version(s) bumped — review the diff and commit it.")
        return 0
    print(f"ok — shipped assets and client manifest versions are consistent with {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
