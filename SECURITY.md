# Security

## Reporting a vulnerability

Email **security@craft.io**. Please don't open a public issue for a security
report. We'll acknowledge within three business days.

## What this repository ships

Every plugin here is **declarative**: markdown and JSON only. There is no
`hooks/`, `bin/`, `agents/`, `monitors/`, `settings.json` or `.lsp.json` in any
plugin, so installing one adds no code that runs on your machine. CI enforces
this — `.github/scripts/validate_plugins.py` fails the build if an executable
component appears in a plugin directory.

The only network component is the Craft.io MCP server, declared in
[`plugins/craft-guru/.mcp.json`](plugins/craft-guru/.mcp.json):

- `https://mcp.craft.io/mcp` over HTTPS, Craft.io's own domain.
- Authentication is per-user OAuth. This repository contains no API keys, no
  tokens and no environment-variable secrets, and it never asks you for any.
- The server sees what your own Craft.io account can see. The plugin adds no
  permissions to your account.

## The trust boundary you should know about

The skills in `craft-guru` read Craft.io content and can write back to it. Some
of that content is written by people outside your team — customer feedback
submitted through a public feedback portal, and item titles, descriptions and
comments from anyone with workspace access.

Text like that can try to steer a language model. Every skill therefore carries
a standing `## Trust boundary` section instructing Claude to treat Craft content
as data rather than instructions, to stay inside the Craft MCP, and to surface
anything that reads like an injected instruction to you instead of acting on it.
CI fails if a skill is missing that section.

That instruction is a strong mitigation, not a hard sandbox. Nothing in the
skill format can technically prevent a model from calling a tool. Two things to
know:

1. **Every write is gated.** No skill writes to Craft without asking you first.
   Read the summary before you approve it — that confirmation step is the last
   line of defence, and it works.
2. **You can enforce the boundary yourself.** If you want the restriction to be
   structural rather than instructional, add deny rules to your own Claude Code
   [permission settings](https://code.claude.com/docs/en/permissions), which
   apply across all skills and prompts. For example, in
   `~/.claude/settings.json`:

   ```json
   {
     "permissions": {
       "deny": ["Bash", "WebFetch", "WebSearch"]
     }
   }
   ```

   Scope that to a project if you only want it while doing product work.

We deliberately do **not** use the `allowed-tools` skill frontmatter field.
Despite the name it grants tools without prompting rather than restricting them,
which would weaken your defaults, not strengthen them.

## Verifying what you install

```
python3 .github/scripts/validate_plugins.py     # structural + safety checks
claude plugin validate .                        # marketplace manifest
claude plugin validate ./plugins/craft-guru     # plugin manifest
```

Every skill is a plain markdown file. Read the one you plan to use — it is the
complete set of instructions Claude receives.
