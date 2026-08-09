# Craft.io plugins for Claude Code 

The official Claude Code plugin marketplace for [Craft.io](https://www.craft.io).
It ships the **craft-guru** plugin: the Craft.io MCP connector plus guided skills
for everyday product-management work — writing PRDs, breaking them into stories,
analyzing customer feedback, finding related items, identifying blockers, writing
release notes, and running sprint planning.

## Install

```
/plugin marketplace add craft-io-app/craft-io-plugins
/plugin install craft-guru@craft-io-app
```

Then run `/mcp` and sign in to connect your Craft.io account.

See [`plugins/craft-guru/README.md`](plugins/craft-guru/README.md) for what each
skill does.

## How to add the plugin (step-by-step)

No coding or technical setup required — this takes about a minute.

### In Claude Code

1. Open Claude Code.
2. Type this and press enter:
   ```
   /plugin marketplace add craft-io-app/craft-io-plugins
   ```
3. Then install the plugin:
   ```
   /plugin install craft-guru@craft-io-app
   ```
4. Type `/mcp` and follow the prompt to sign in with your Craft.io account. This
   connects Claude to your own workspace — no admin setup needed.
5. That's it. Try asking Claude something like *"break this PRD into stories"* or
   *"analyze our feedback and tell me what to prioritize."*

### In Cowork / claude.ai (Team or Enterprise workspace)

1. Ask your workspace Owner or Admin to enable the **Craft.io** connector once,
   in **Admin Settings**. This is a one-time step for the whole organization.
2. Once enabled, open the plugin marketplace inside Cowork and search for
   **craft-guru**, or use the same `/plugin marketplace add` and
   `/plugin install` commands shown above.
3. Connect your own Craft.io account when prompted.
4. Start using the skills by describing what you want in plain English — for
   example, *"generate a PRD for this feature"* or *"check our dependencies for
   blockers"*.

### In Cursor

Cursor plugin support reads `plugins/craft-guru/.cursor-plugin/plugin.json` and
`marketplace.json`. Installing directly from this repo's subdirectory (rather
than a dedicated single-plugin repo) hasn't been hands-on verified against a
real Cursor build yet — treat the install path below as provisional until
that's confirmed:

```
/plugin marketplace add craft-io-app/craft-io-plugins
/plugin install craft-guru@craft-io-app
```

If subdirectory installs aren't supported, the fallback is to point Cursor's
"add marketplace" flow at `plugins/craft-guru` specifically once that's
confirmed. This section will be updated once verified — coming soon.

### In Gemini CLI

The `craft-guru` extension manifest (`gemini-extension.json`) lives at
`plugins/craft-guru/`, not at the repo root. Gemini CLI's documented install
flow (`gemini extensions install <source>`) expects the manifest at the
extension's root directory, and subdirectory-of-a-monorepo installs haven't
been hands-on verified yet. Until that's confirmed, the safer path is a local
clone plus a link:

```
git clone https://github.com/craft-io-app/craft-io-plugins
gemini extensions link craft-io-plugins/plugins/craft-guru
```

A direct `gemini extensions install https://github.com/craft-io-app/craft-io-plugins`
may or may not work depending on whether Gemini CLI resolves a subdirectory —
this section will be updated once verified. Coming soon.

### Troubleshooting

- **Don't see the plugin after adding the marketplace?** Check you typed
  `craft-io-app/craft-io-plugins` exactly, then re-run the install command.
- **Craft.io connection fails?** Make sure you're signing in with the Craft.io
  account tied to your workspace, and that your admin has enabled the connector
  if you're on a Team or Enterprise plan.
- **Not sure what a skill does?** Describe your goal in plain language (for
  example, "what should we build next?") — Claude picks the right skill.

## What gets installed

One MCP connector and six skills. Nothing else — no hooks, no agents, no
scripts, nothing that runs code on your machine. See [SECURITY.md](SECURITY.md)
for the full picture, including the one trust boundary worth understanding before
you point these skills at customer feedback.

## Repository layout

```
craft-io-plugins/
├── .claude-plugin/marketplace.json   # marketplace catalog
└── plugins/craft-guru/
    ├── .claude-plugin/plugin.json
    ├── .cursor-plugin/
    │   ├── plugin.json
    │   └── marketplace.json
    ├── .mcp.json                     # Craft.io MCP connector (Claude Code, Cursor)
    ├── gemini-extension.json         # Craft.io MCP connector (Gemini CLI)
    ├── GEMINI.md
    ├── README.md
    └── skills/
        ├── prd-generator/SKILL.md
        ├── break-to-stories/SKILL.md
        ├── feedback-analyzer/SKILL.md
        ├── find-related-items/SKILL.md
        ├── release-notes/SKILL.md
        └── sprint-planning/SKILL.md
```

Adding a skill means adding one `skills/<name>/SKILL.md` folder. No manifest
change. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE).
