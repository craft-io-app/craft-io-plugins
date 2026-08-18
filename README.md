# Craft.io plugins

The official plugin marketplace for [Craft.io](https://www.craft.io), for Claude
Code, Cursor and Gemini CLI. It ships the **craft-guru** plugin: the Craft.io MCP
connector plus guided skills for everyday product-management work — writing PRDs,
breaking them into stories, analyzing customer feedback, finding related items,
writing release notes, and running sprint planning.

One set of skills and one connector definition, read by every client. Nothing is
forked per client; each one gets a thin manifest pointing at the same files.

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
   example, *"generate a PRD for this feature"* or *"analyze our feedback and
   tell me what to prioritize"*.

### In Cursor

Cursor reads the catalog at `.cursor-plugin/marketplace.json` in this repo's
root, the same way Claude Code reads `.claude-plugin/marketplace.json`:

```
/plugin marketplace add craft-io-app/craft-io-plugins
/plugin install craft-guru@craft-io-app
```

Then connect your Craft.io account when prompted.

Needs Cursor 3.13.0 or later — that is when plugin MCP support landed, and the
manifest declares it, so older builds will not offer the plugin rather than
installing it with a connector that never starts.

### In Gemini CLI

Gemini CLI installs an extension from a repository whose `gemini-extension.json`
sits at the root. This repo is a multi-plugin marketplace, so `craft-guru` lives
at `plugins/craft-guru/` — clone and link it:

```
git clone https://github.com/craft-io-app/craft-io-plugins
gemini extensions link craft-io-plugins/plugins/craft-guru
```

`gemini extensions install <url>` takes "the GitHub URL or local path of the
extension" and has no documented way to name a subdirectory, so it is not
expected to work against this repo's root. If you would rather install than
link, use the linked clone above and run `git pull` to update.

Gemini discovers `skills/*/SKILL.md` natively, so you get the same six skills
and the same connector as every other client.

### Troubleshooting

- **Don't see the plugin after adding the marketplace?** Check you typed
  `craft-io-app/craft-io-plugins` exactly, then re-run the install command.
- **Craft.io connection fails?** Make sure you're signing in with the Craft.io
  account tied to your workspace, and that your admin has enabled the connector
  if you're on a Team or Enterprise plan.
- **Not sure what a skill does?** Describe your goal in plain language (for
  example, "what should we build next?") — Claude picks the right skill.
- **Missing a skill you read about here?** Your client is probably still running
  the version you installed. See [Staying up to date](#staying-up-to-date).

## What gets installed

One MCP connector and six skills. Nothing else — no hooks, no agents, no
scripts, nothing that runs code on your machine. See [SECURITY.md](SECURITY.md)
for the full picture, including the one trust boundary worth understanding before
you point these skills at customer feedback.

## Staying up to date

New skills ship as commits here, but no client fetches them on its own by
default. One step, once:

- **Claude Code** keeps auto-update off for third-party marketplaces. Run
  `/plugin`, open **Marketplaces**, select `craft-io-app` and choose **Enable
  auto-update** — or pull the latest on demand with
  `/plugin marketplace update craft-io-app`. Admins can set `"autoUpdate": true`
  on the marketplace entry in managed settings to do this for everyone.
- **Cursor** updates when the plugin manifest's `version` changes.
- **Gemini CLI** reads a linked extension from your clone, so `git pull` there is
  the update.

## Repository layout

```
craft-io-plugins/
├── .claude-plugin/marketplace.json   # catalog — Claude Code
├── .cursor-plugin/marketplace.json   # catalog — Cursor
└── plugins/craft-guru/
    ├── .claude-plugin/plugin.json    # manifest — Claude Code
    ├── .cursor-plugin/plugin.json    # manifest — Cursor
    ├── gemini-extension.json         # manifest — Gemini CLI
    ├── .mcp.json                     # Craft.io MCP connector (Claude Code, Cursor)
    ├── GEMINI.md                     # always-on context for Gemini CLI
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
