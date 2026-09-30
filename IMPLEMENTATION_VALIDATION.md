# Implementation Validation — Kessler Protocol

Validation date: 2026-09-29

## Local automated validation

- Unit/integration tests: **PASS** (30/30)
- `python -m compileall` across `src`, `tests`, `tools`, `integrations`: **PASS**
- Antigravity/Gemini/Claude Code vendored runtime and static skill regeneration (`tools/build_integrations.py`) with zero drift against `src/kessler_protocol`: **PASS**
- Package wheel build/install smoke test: **PASS**
- Installed-wheel Antigravity adapter deep doctor in isolated HOME: **PASS**
- Installed-wheel Gemini adapter deep doctor in isolated HOME: **PASS**
- Installed-wheel Claude Code adapter install + deep doctor (`kessler install/doctor --target claude_code`) in isolated HOME, plus uninstall/restore round trip: **PASS**

## Findings fixed in this validation pass

- `verification.classify_command` did not recognize `python -m unittest` (only `pytest`). Kessler's own documented test command (`python -m unittest discover -s tests -v`, per README "Development" and `CONTRIBUTING.md`) was therefore invisible to KES-VER-001 — the completion gate could never be satisfied by running the project's real test command. Fixed by extending the `test` pattern in `src/kessler_protocol/verification.py`; regression coverage added in `tests/test_verification.py`.
- `doctor.py`'s deep Gemini installation check verified `kessler-before-tool`, `kessler-after-tool`, and `kessler-after-agent` were registered in `settings.json`, but not `kessler-before-agent` (the `BeforeAgent` planning-context hook added with the Planning Gate). A broken or missing `BeforeAgent` registration could pass `kessler doctor --target gemini --deep` undetected. Fixed by adding `kessler-before-agent` to the expected hook list.

Both fixes were found by dogfooding Kessler against its own repository (`kessler init` / `kessler profile`), not by code review alone.

## Claude Code adapter (new in this pass)

A full `ClaudeCodeAdapter` was added against the official Claude Code hooks contract (stdin `session_id`/`cwd`/`tool_name`/`tool_input`/`tool_output`; stdout `hookSpecificOutput.permissionDecision` for `PreToolUse`, `decision: block` for `Stop`, `additionalContext` for `UserPromptSubmit`), registered in `ADAPTERS`, wired into `decision.py`'s `force_ask`/`ask` mapping (Claude Code gets the same soft `ask` semantics as Antigravity instead of Gemini's hard fallback), `hook_runtime.before_agent`, and `cli.py`'s `--target`/`--harness` choices. `installers.install_claude_code`/`uninstall_claude_code` mirror the Gemini installer's backup/restore/manifest pattern, writing to `.claude/` (user or workspace scope) and registering `UserPromptSubmit`/`PreToolUse`/`PostToolUse`/`Stop` hooks in `settings.json`. Because Claude Code hook entries carry no documented `"name"` field (unlike Gemini's), Kessler-owned entries are identified for removal/restore by the absolute path to their vendored `entry.py` (`installers._remove_command_hooks`), verified by `doctor.installed_checks`'s `claude_code` branch and `tests/test_claude_code.py`'s installer round-trip test. `doctor.package_checks` and `installed_checks` both gained Claude Code coverage; `tools/build_integrations.py` now also regenerates a static `integrations/claude-code/skill/kessler-protocol/SKILL.md` mirror alongside Gemini's.

## Test count at freeze

30 automated tests (23 at the previous freeze + 7 for the Claude Code adapter hook contract, Planning Gate interaction, and installer round trip — see `tests/test_claude_code.py`).

## Context budget at freeze

- Always-on core: ~214 approximate tokens
- Skill discovery: ~50 approximate tokens
- Full skill: lazy, ~670 approximate tokens
- Policy catalog persistent prompt cost: 0
- Budget target: always-on core <= 260 approximate tokens (includes the planning invariant)

Approximation uses characters/4 and is a regression metric, not tokenizer-accurate billing. Measured via `kessler budget --json`.

## Project self-initialization

`kessler init` was run against this repository for the first time; `.kessler.toml` now exists at the repository root with default auto-detected settings (`strictness = "auto"`, `context = "lean"`). `.kessler/cache/project-profile.json` is intentionally not committed — it is gitignored (`.kessler/.gitignore`) and regenerates automatically from the fingerprinted project tree on the next `kessler profile` run or hook invocation.

## Certification boundary

These results validate the local implementation and documented I/O contracts. They do **not** substitute for live smoke testing inside the installed current Antigravity IDE/CLI, Gemini CLI, and Claude Code applications, and they do not substitute for a published KesslerBench run.
