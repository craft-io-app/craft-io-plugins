# Craft Guru

A Claude Code / Cowork plugin for Craft.io users. Packages the Craft.io MCP
connector together with guided, skill-driven workflows for common
product-management tasks.

## What's included

**MCP connector**

- `craft-io` — HTTP connector to `https://mcp.craft.io/mcp`, giving Claude access
  to your Craft workspaces, portfolio items and feedback portals. Its tools appear
  as `mcp__craft-io__*`.

**Skills**

- `prd-generator` — Generates a PRD through a structured guided discovery workflow using Craft MCP tools and interactive questioning.
- `break-to-stories` — Breaks a PRD, feature spec or Craft item into well-structured, sprint-ready child stories through guided discovery.
- `feedback-analyzer` — Analyzes customer and user feedback from Craft feedback portals to surface the most impactful problems to solve.
- `find-related-items` — Finds items across Craft workspaces related to a given item (duplicates, adjacent work, thematic overlap) and documents the relationships.
- `identify-blockers` — Identifies cross-item blockers within a planned set of work and documents dependency relationships to prevent scheduling conflicts.
- `release-notes` — Writes customer-facing product release notes for a new feature or release through a structured guided workflow.
- `sprint-planning` — Runs a full sprint/iteration planning workflow: capacity review, goal synthesis, story point estimation, load balancing and risk identification.

More skills land over time. Adding one needs no manifest change — a new
`skills/<name>/SKILL.md` folder is enough, and because the plugin doesn't pin a
version, each release reaches existing installs on their next update.

## Requirements

- A Craft.io account (any plan that supports MCP/API access).
- Claude Code, or Cowork with plugin support enabled.

## Installing

```
/plugin marketplace add craft-io-app/craft-io-plugins
/plugin install craft-guru@craft-io
```

## Connecting to Craft.io

After installing, run `/mcp` and follow the OAuth prompt to connect your own
Craft.io account. No org-level admin step is required in Claude Code.

Through claude.ai in a Team or Enterprise organization, an Owner or Admin must
first enable the Craft.io connector in Admin Settings before individual members
can connect their accounts.

## Using the skills

Describe what you want in plain language and Claude picks the right skill:

- "Generate a PRD for this feature"
- "Break this PRD into stories"
- "Analyze our feedback and tell me what to prioritize"
- "Find items related to CRK-1234"
- "Check our dependencies for blockers"
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
