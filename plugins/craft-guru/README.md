# Craft Guru

A plugin for Craft.io users, for Claude Code, Cowork, Cursor and Gemini CLI.
Packages the Craft.io MCP connector together with guided, skill-driven workflows
for common product-management tasks.

Every client reads the same `skills/` directory and the same connector endpoint.
The per-client manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`,
`gemini-extension.json`) only point at them.

## What's included

**MCP connector**

- `craft-io` — HTTP connector to `https://mcp.craft.io/mcp`, giving the agent
  access to your Craft workspaces, portfolio items and feedback portals. Its
  tools appear as `mcp__craft-io__*`.

**Skills**

- `prd-generator` — Generates a PRD through a structured guided discovery workflow using Craft MCP tools and interactive questioning.
- `break-to-stories` — Breaks a PRD, feature spec or Craft item into well-structured, sprint-ready child stories through guided discovery.
- `feedback-analyzer` — Analyzes customer and user feedback from Craft feedback portals to surface the most impactful problems to solve.
- `find-related-items` — Finds items across Craft workspaces related to a given item (duplicates, adjacent work, thematic overlap) and documents the relationships.
- `release-notes` — Writes customer-facing product release notes for a new feature or release through a structured guided workflow.
- `sprint-planning` — Runs a full sprint/iteration planning workflow: capacity review, goal synthesis, story point estimation, load balancing and risk identification.

More skills land over time. Adding one needs no manifest change on any client — a
new `skills/<name>/SKILL.md` folder is enough. Whether a new skill reaches you is
a separate question from whether it has shipped, and the answer differs by
client; see [Staying up to date](#staying-up-to-date).

## Requirements

- A Craft.io account (any plan that supports MCP/API access).
- One of: Claude Code, Cowork with plugin support enabled, Cursor 3.13.0+, or
  Gemini CLI.

## Installing

**Claude Code, Cowork and Cursor** read a marketplace catalog from this repo's
root, so the commands are the same in all three:

```
/plugin marketplace add craft-io-app/craft-io-plugins
/plugin install craft-guru@craft-io-app
```

**Gemini CLI** installs an extension from a repository root, and this repo is a
multi-plugin marketplace, so clone and link the plugin directory:

```
git clone https://github.com/craft-io-app/craft-io-plugins
gemini extensions link craft-io-plugins/plugins/craft-guru
```

## Connecting to Craft.io

After installing, run `/mcp` and follow the OAuth prompt to connect your own
Craft.io account. No org-level admin step is required in Claude Code.

Through claude.ai in a Team or Enterprise organization, an Owner or Admin must
first enable the Craft.io connector in Admin Settings before individual members
can connect their accounts.

## Staying up to date

**Claude Code** keeps background auto-update off for third-party marketplaces,
and this is one, so a new skill does not arrive on its own. Turn it on once: run
`/plugin`, open the **Marketplaces** tab, select `craft-io-app` and choose
**Enable auto-update**. To pull the latest right now instead:

```
/plugin marketplace update craft-io-app
```

Either way the new version loads on your next launch, or immediately if you run
`/reload-plugins`. If your organization manages Claude Code settings, an admin
can set `"autoUpdate": true` on the marketplace entry once and nobody has to do
this themselves.

**Cursor** compares the `version` in the plugin manifest and updates when it
changes.

**Gemini CLI** reads a linked extension straight from your clone, so `git pull`
in that clone is the update.

## Using the skills

Describe what you want in plain language and Claude picks the right skill:

- "Generate a PRD for this feature"
- "Break this PRD into stories"
- "Analyze our feedback and tell me what to prioritize"
- "Find items related to CRK-1234"
- "Write release notes for this feature"
- "Let's plan the next sprint"

You can also invoke one directly. Plugin skills are namespaced by plugin name, so
it's `/craft-guru:break-to-stories`, not `/break-to-stories`.

## Writes are always confirmed

Several of these skills can create and update Craft items, wire up dependencies
and link feedback. None of them writes anything without showing you what it's
about to write and waiting for your approval. Read the summary before you approve
it. See [SECURITY.md](../../SECURITY.md) for why that step matters when the input
includes feedback submitted by people outside your team.
