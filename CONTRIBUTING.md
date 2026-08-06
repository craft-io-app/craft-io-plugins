# Contributing

This repository is a public Claude Code plugin marketplace. Anything merged here
is installable by Craft.io customers within minutes, so the bar is the same as
for shipped product.

## Add a skill

1. Create `plugins/craft-guru/skills/<skill-name>/SKILL.md`.
2. Write frontmatter with `name` (matching the directory) and `description`.
3. Write the body.
4. Run the checks below.
5. Open a PR.

No manifest edit is needed. The plugin does not pin a `version`, so Claude Code
resolves the version from the commit SHA and every merge to `main` reaches
existing installs on their next update. **Do not add a `version` field** to
`plugin.json` or to the marketplace entry — setting it freezes the plugin, and
users who already installed it stop receiving new skills. CI fails if either
appears.

## Run the checks

```
python3 .github/scripts/validate_plugins.py
claude plugin validate .
claude plugin validate ./plugins/craft-guru
```

Both report one warning — that no `version` is set. That is deliberate, per the
note above, so don't pass `--strict` and don't "fix" it by adding a version.

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
permission rules.

## Writing a good skill

- Gate every Craft write behind an explicit confirmation, and show the user what
  will be written before you ask. Every existing skill does this; match it.
- Never probe for write access by performing a write. Attempt the action the user
  actually asked for and handle the permission error.
- Keep the description tight. It sits in every user's context on every turn, so
  aim for two or three sentences plus trigger phrases. The body is free — it only
  loads when the skill runs.
- Never invent Craft data. If a field is missing, say so.
