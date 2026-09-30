# Compatibility

## Antigravity

Kessler uses the documented plugin structure (`plugin.json`, `hooks.json`, `rules/`, `skills/`) and `PreToolUse`, `PostToolUse`, and `Stop` hook contracts. The preferred installer rewrites hook commands to the exact Python interpreter and vendors the runtime into the installed plugin.

- user IDE / Antigravity 2.0: `~/.gemini/config/plugins/kessler-protocol`
- user Antigravity CLI: `~/.gemini/antigravity-cli/plugins/kessler-protocol`
- workspace: `.agents/plugins/kessler-protocol`

## Gemini CLI

Kessler registers named hooks in `settings.json` for `BeforeTool`, `AfterTool`, and `AfterAgent`. It removes/restores only Kessler-owned hook groups during uninstall.

## Claude Code

Kessler implements the documented Claude Code hooks contract (`hookSpecificOutput.permissionDecision` for `PreToolUse`, `decision: block` for `Stop`, `additionalContext` for `UserPromptSubmit`) and registers command hooks in `settings.json` for `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.

- user scope: `~/.claude/{skills,kessler/runtime,settings.json}`
- workspace scope: `<workspace>/.claude/{skills,kessler/runtime,settings.json}`

Claude Code hook entries have no documented `"name"` field, so Kessler identifies and removes/restores only its own entries by the absolute path to its vendored `entry.py`, never by matching unrelated hooks. Local validation (install/uninstall round trip, hook contract unit tests, isolated-HOME wheel install + `kessler doctor --target claude_code --deep`) is complete — see `IMPLEMENTATION_VALIDATION.md`. Live smoke testing inside the installed Claude Code application itself has not yet been run.

## Not yet certified

Codex and Cursor adapters are intentionally not represented as working integrations until each has its own installer, uninstall path, hook contract tests and live smoke tests.
