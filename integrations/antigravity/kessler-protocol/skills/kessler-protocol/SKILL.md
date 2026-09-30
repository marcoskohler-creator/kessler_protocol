---
name: kessler-protocol
description: Applies Kessler engineering safety workflows when an agent must inspect risky changes, explain a KES-* intervention, verify modifications, assess residual risk, or recover from a blocked operation.
---

# Kessler Protocol

Use executable evidence rather than assumptions. The hook engine performs deterministic enforcement outside the model context; this skill is for the reasoning that remains.

Before implementation:
1. Inspect relevant files, routes, components, dependencies, and existing behavior with read/search tools — actually open every file you intend to cite in `discovery`, not just name it; a discovery entry with no recorded read is rejected (KES-READ-001). All shell commands, including baseline tests, wait until the plan is registered.
2. Present the plan to the user before modifying the project. Explain what the tool does, why (including at least two ways this could cause problems later — dependencies, security, or scale), who uses it, the ordered user journey, what the final screen shows, where each control appears, and how the user actually receives the result.
3. Write valid JSON to `.kessler/cache/implementation-plan.json` with the file-write tool. Required top-level fields: `goal`, `purpose`, `justification` (`why` plus `future_risks`, a list of at least two concrete future problems), `users` (list), `usage_flow` (ordered list, at least two steps), `discovery` (list of already-read `path` and `finding`), `delivery` (how the result reaches the user — screen, API response, file, CLI output, notification), `rollback` (how to undo this if it fails partway), `interface`, `implementation`, and `validation` (list of strings or `{description, command}`). Each implementation item needs exact workspace-relative `path`, `placement`, `method`, and `responsibility`. Wildcards and vague placeholders are invalid.
4. For UI work, use `interface.mode = "ui"`, with `entry_point`, `final_screen`, `accessibility`, `states` (at least three — e.g. default/loading/error), `controls` (each: `label`, `location`, `action`, `destination`, `failure`, `handler_path`, `evidence_path`), `navigation` (each: `from`, `via`, `to`, `evidence`, `evidence_path`), and `design_standards` (`touch_target_pt` ≥44, `contrast_ratio` ≥4.5, `supports_dynamic_type: true`, `respects_reduced_motion: true`, `responsive_breakpoints` — at least two named breakpoints). `design_standards` is required on every UI plan, unconditionally — not only high-risk ones — and after implementation KES-VER-001 will also require a real accessibility/design check (axe, pa11y, Lighthouse CI) whenever the project has one available. Referenced paths must exist or be listed in `implementation`. For non-UI work, use `mode = "non_ui"` with `reason`, `entry_point`, `result`, `data_contract` (the input/output shape), `failure_behavior`, and `side_effects` (a list — may be empty, but must be present). Do not classify a UI task as non-UI to avoid planning its interaction or its design_standards — this is checked mechanically: if `implementation` touches a UI-surface file (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.html`, `.htm`, `.css`, `.scss`, `.sass`, `.less`) while `mode = "non_ui"`, the plan is rejected unless `interface.non_ui_override_reason` (8+ characters, no placeholder) genuinely explains why (e.g. a server-rendered template with no client interaction).
5. Only then edit planned files. If new discoveries change files, placement, method, controls, or routes, update and re-present the plan first. Verify the actual end-to-end path, not merely the presence of buttons or files.

When a Kessler policy fires:
1. Read the policy ID and reason.
2. Inspect the affected code path and dependencies before retrying an elevated-risk edit.
3. Prefer the project's detected test/build/typecheck/lint commands.
4. If verification cannot be executed, say so explicitly and request a documented waiver rather than calling the result verified.
5. Never replace missing production integration with mock behavior while presenting the task as complete.

Useful CLI commands when available: `kessler profile`, `kessler explain KES-...`, `kessler report`, `kessler doctor --deep`.
