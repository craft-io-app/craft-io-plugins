# Contributing

This repository is a public plugin marketplace for Claude Code, Cursor and
Gemini CLI. Anything merged here is installable by Craft.io customers within
minutes, so the bar is the same as for shipped product.

## One set of assets, three manifests

The skills in `skills/` and the connector in `.mcp.json` are written once. Each
client gets a thin manifest that points at them:

| Client | Catalog | Manifest |
|---|---|---|
| Claude Code / Cowork | `.claude-plugin/marketplace.json` | `plugins/craft-guru/.claude-plugin/plugin.json` |
| Cursor | `.cursor-plugin/marketplace.json` | `plugins/craft-guru/.cursor-plugin/plugin.json` |
| Gemini CLI | — (installed by path) | `plugins/craft-guru/gemini-extension.json` |

Both catalogs live at the **repository root** and name the plugin by
subdirectory. A catalog nested inside a plugin directory is never found, because
each client resolves a catalog's `source` entries from the repo root. CI rejects
one in the wrong place.

**Never fork a skill or the connector per client.** If a client needs something
different, add it to that client's manifest, not to a second copy of the asset.
CI cross-checks that every manifest points at the same MCP server names and the
same endpoint URLs, in both directions.

## Add a skill

1. Create `plugins/craft-guru/skills/<skill-name>/SKILL.md`.
2. Write frontmatter with `name` (matching the directory) and `description`.
3. Write the body.
4. Bump `version` in `.cursor-plugin/plugin.json` and `gemini-extension.json`
   (see below).
5. Run the checks below.
6. Open a PR.

## Versions differ by client, deliberately

Claude Code resolves a plugin's version from the commit SHA, so
`.claude-plugin/plugin.json` **must not** set `version` — pinning it freezes the
plugin and users who already installed it stop receiving new skills. CI fails if
a `version` appears there or in a marketplace entry.

Cursor and Gemini CLI work the other way round: both resolve updates against the
manifest `version`, and `gemini extensions update` compares against it directly.
Those two manifests **must** set it, and CI fails if they don't. So a new skill
needs a version bump in those two files and no edit at all to the Claude
manifest. It is an asymmetry, not an oversight.

## Run the checks

```
python3 .github/scripts/validate_plugins.py       # structure, safety, cross-manifest parity
python3 .github/scripts/test_validate_plugins.py  # proves those rules actually fire
claude plugin validate .
claude plugin validate ./plugins/craft-guru
```

The second one matters more than it looks. Every rule the validator enforces is
mutation-tested against a scratch copy of the repo — break the rule, assert the
build goes red. A review once found seven rules that had silently never fired;
each looked correct in the source, and a clean tree passed either way. If you add
a rule, add its mutation.

`claude plugin validate` reports one warning — that no `version` is set. That is
deliberate, per the note above, so don't pass `--strict` and don't "fix" it by
adding a version to the Claude manifest.

Then load it for real before opening the PR:

```
claude --plugin-dir ./plugins/craft-guru
```

## Rules the validator enforces

**Plugins stay declarative.** No `hooks/`, `bin/`, `agents/`, `monitors/`,
`settings.json` or `.lsp.json`. Markdown and JSON only, so installing a plugin
from this marketplace never runs code on a customer's machine. Changing that
means changing the security promise in [SECURITY.md](SECURITY.md) — raise it as
a discussion first.

**Frontmatter stays inside the [Agent Skills](https://agentskills.io) spec** —
`name`, `description`, `license`, `compatibility`, `metadata`. Claude Code
accepts many more fields, but claude.ai and the Skills API reject anything else
with a hard error, and these skills are meant to work on every surface. In
particular, `disallowed-tools` is Claude Code-only, and `allowed-tools` grants
tools without prompting rather than restricting them, so neither is used here.

**Every skill needs a `## Trust boundary` section.** Copy it verbatim from an
existing skill. It is what tells Claude to treat customer-submitted feedback as
data rather than instructions.

**No proactive triggers.** Don't write "use proactively" or "trigger
proactively" in a description. This plugin installs at user scope across all of
someone's projects; a skill that fires on loose phrasing hijacks unrelated work.
Describe what the skill does and list the explicit phrases that should trigger
it.

**Never tell the model to withhold reasoning from the user.** No "keep this
quiet" or "don't cite the threshold". If a heuristic drives a decision, the user
may know what it was.

**MCP servers are remote and HTTPS-only**, named in lower-case kebab-case.
A `command` field would launch a local process; a name with other characters gets
rewritten inside the `mcp__<server>__<tool>` prefix, which silently breaks user
permission rules. This applies to every manifest, including one that reaches its
servers through a path reference — the referenced file is loaded and checked, not
just resolved, because a rule enforced only on the file we happen to ship today
is not enforced at all.

**No `trust`.** Gemini CLI's `trust` key bypasses every tool-call confirmation,
and that confirmation is the last control a user has once a server is installed.
Gemini documents it as unsupported for extensions, so it would be inert — CI
rejects it anyway, on any manifest.

**Manifest paths stay inside the plugin.** Relative only: no absolute paths and
no `..` traversal, which is also Cursor's own authoring rule.

## Writing a good skill

- Gate every Craft write behind an explicit confirmation, and show the user what
  will be written before you ask. Every existing skill does this; match it.
- Never probe for write access by performing a write. Attempt the action the user
  actually asked for and handle the permission error.
- Keep the description tight. It sits in every user's context on every turn, so
  aim for two or three sentences plus trigger phrases. The body is free — it only
  loads when the skill runs.
- Never invent Craft data. If a field is missing, say so.
