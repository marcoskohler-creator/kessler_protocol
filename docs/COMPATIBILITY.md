# Compatibility

## Antigravity

Kessler uses the documented plugin structure (`plugin.json`, `hooks.json`, `rules/`, `skills/`) and `PreToolUse`, `PostToolUse`, and `Stop` hook contracts. The preferred installer rewrites hook commands to the exact Python interpreter and vendors the runtime into the installed plugin.

- user IDE / Antigravity 2.0: `~/.gemini/config/plugins/kessler-protocol`
- user Antigravity CLI: `~/.gemini/antigravity-cli/plugins/kessler-protocol`
- workspace: `.agents/plugins/kessler-protocol`

## Gemini CLI

Kessler registers named hooks in `settings.json` for `BeforeTool`, `AfterTool`, and `AfterAgent`. It removes/restores only Kessler-owned hook groups during uninstall.

## Not yet certified

Claude Code, Codex and Cursor adapters are intentionally not represented as working integrations until each has its own installer, uninstall path, hook contract tests and live smoke tests.
