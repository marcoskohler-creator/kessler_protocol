# Changelog

## Unreleased

- Implemented risk-proportional `justification.future_risks` validation (Abordagem 2): changes touching sensitive boundaries (`auth/`, `.env*`, `migrations/`, `billing/`, `secrets/`) or running in HIGH/CRITICAL risk profiles require at least two concrete risks; low/moderate non-sensitive tasks require `future_risks` as a mandatory list but permit it to be empty (`[]`). Any declared risk item must remain substantive (>= 8 chars, no placeholders), eliminating forced hallucination of risks on trivial edits while preserving strict gates on elevated changes.
- Expanded the implementation-plan schema to a full justification/delivery/rollback model: `justification` (`why` plus risk-proportional `future_risks`), `delivery`, `rollback`, a tightened `usage_flow` (at least two steps), and a domain-specific `interface` block (`mode: "ui"` with `entry_point`/`final_screen`/`accessibility`/`states`/`controls`/`navigation`, or `mode: "non_ui"` with `reason`/`result`/`data_contract`/`failure_behavior`/`side_effects`). `validation` now accepts either a plain string or `{description, command}`.
- Implemented `KES-READ-001` for real: a `discovery[]` entry citing a file is now rejected unless the session has recorded read evidence for that exact path. Fixed a companion bug in `evidence.py` where the read-evidence regex never matched Claude Code's real `"Read"` tool name, so read evidence was silently never recorded in real Claude Code sessions.
- Made `KES-TRUTH-001` (fake-success content pattern) always-active instead of gated behind `strict`/`paranoid` strictness; it remains purely advisory and never blocks.
- Recalibrated `risk.py` so that migrations/authentication/authorization/payments/secrets signals reach HIGH risk (and auto-escalate to `strict` strictness) on their own, instead of requiring several risk signals at once.
- Added the Claude Code adapter: `ClaudeCodeAdapter` implements the documented Claude Code hooks contract (`hookSpecificOutput.permissionDecision` for `PreToolUse`, `decision: block` for `Stop`, `additionalContext` for `UserPromptSubmit`). Added `installers.install_claude_code`/`uninstall_claude_code` (mirroring the Gemini installer's backup/restore/manifest pattern against `.claude/settings.json`, identifying Kessler-owned hook entries by their vendored `entry.py` path since Claude Code hook entries carry no `"name"` field), `decision.py`/`hook_runtime.py` wiring, `cli.py --target/--harness claude_code`, `doctor.py` package and installed-target coverage, a static `integrations/claude-code/skill/kessler-protocol/SKILL.md` mirror, and `tests/test_claude_code.py`.
- Added the Planning Gate: `KES-PLAN-001`/`KES-PLAN-002` require a registered, evidence-based implementation plan (`.kessler/cache/implementation-plan.json`) before project-changing tools run; direct edits outside the planned file scope are blocked. Added `planning.py`, a `BeforeAgent` Gemini hook carrying planning context, and `docs/PLANNING.md`.
- Raised the always-on context budget target to 260 approximate tokens to account for the planning invariant.
- Fixed `verification.classify_command` to recognize `python -m unittest`, not only `pytest` — Kessler's own documented test command was previously invisible to the KES-VER-001 completion gate.
- Fixed `doctor --target gemini --deep` to also check that the `kessler-before-agent` hook is registered, closing a coverage gap introduced by the Planning Gate's new `BeforeAgent` hook.
- Self-initialized this repository with `kessler init` (`.kessler.toml` committed; `.kessler/cache/` gitignored and regenerated on demand).

## Implementation baseline

- Replaced prompt-heavy rule architecture with local Policy/Risk/Evidence/Verification/State/Decision engines.
- Added automatic project profiling and cached fingerprints.
- Added risk-derived `auto` strictness.
- Added minimal `.kessler.toml` with manual overrides.
- Added Lazy Policy Loading and Zero-Token Enforcement architecture.
- Added executable verification success and relevance tracking; failed checks no longer satisfy completion.
- Added session reports and documented waivers cleared by subsequent writes.
- Added transactional installation manifests, selective Gemini hook mutation, previous-version restoration and rollback.
- Added Antigravity IDE/2.0 and CLI surface-aware installation paths.
- Added self-contained vendored Antigravity runtime generated from canonical source.
- Added `doctor --deep`, `profile`, `explain`, `report`, `waive`, and `budget` commands.
- Added context-budget CI guard.
- Expanded CI to Linux/macOS/Windows on Python 3.11/3.13.
