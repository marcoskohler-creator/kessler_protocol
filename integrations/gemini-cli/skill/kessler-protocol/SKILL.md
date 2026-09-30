---
name: kessler-protocol
description: Applies Kessler engineering safety workflows for risky changes, KES-* policy interventions, verification evidence, residual risk, and blocked operations in Gemini CLI.
---

# Kessler Protocol

The deterministic hook engine enforces most policy without spending model context. When context is injected, act on the specific policy only.

Before implementation, inspect the project (actually read every file before citing it in discovery — KES-READ-001 rejects a citation with no read evidence) and present a concrete plan: goal, purpose, justification (why, plus at least two future risks), users, ordered usage flow, final screen, exact controls and navigation (for UI), exact files and placement, method, delivery (how the result reaches the user), rollback, and validation. Write the plan with the file-write tool to `.kessler/cache/implementation-plan.json` before changing project files. It must contain `goal`, `purpose`, `justification` (`why`, `future_risks`), `users`, `usage_flow` (2+ steps), `discovery` (already-read path and finding), `delivery`, `rollback`, `interface`, `implementation` (exact path, placement, method, responsibility), and `validation` (strings or `{description, command}`). For UI, `interface` needs `mode: "ui"`, `entry_point`, `final_screen`, `accessibility`, `states` (3+), `controls` (label, location, action, destination, failure, handler_path, evidence_path), `navigation` (from, via, to, evidence, evidence_path), and `design_standards` (`touch_target_pt` ≥44, `contrast_ratio` ≥4.5, `supports_dynamic_type: true`, `respects_reduced_motion: true`, `responsive_breakpoints` — 2+ named breakpoints) — required on every UI plan, unconditionally. For non-UI, use `mode: "non_ui"`, reason, entry_point, result, data_contract, failure_behavior, and side_effects (a list, may be empty). A `non_ui` plan whose implementation touches a UI-surface file (.tsx/.jsx/.vue/.svelte/.html/.css/.scss/...) is rejected unless `interface.non_ui_override_reason` genuinely explains why — reclassify as `mode: "ui"` instead of trying to dodge design_standards this way. Revise and re-present the plan before scope changes; test the actual user path.

- Inspect relevant dependencies before elevated-risk changes.
- Use detected executable verification after source/config writes; for UI work, that includes a real accessibility/design check (axe, pa11y, Lighthouse CI) whenever the project has one available (KES-VER-001) — the design_standards checklist alone is not verification.
- Never label incomplete or placeholder integration as production-complete.
- If verification is unavailable, disclose it and use a documented waiver rather than fabricating success.
- Use `kessler explain <POLICY_ID>` for the full rule only when needed.
