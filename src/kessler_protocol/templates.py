from __future__ import annotations

import json
from pathlib import Path

PLUGIN_JSON = {
    "$schema": "https://antigravity.google/schemas/v1/plugin.json",
    "name": "kessler-protocol",
    "description": "Risk-proportional engineering safety rules and executable evidence gates for agentic coding."
}

HOOKS_JSON = {
    "kessler-risk-gate": {
        "PreToolUse": [{
            "matcher": "run_command|.*write.*|.*edit.*|.*replace.*|.*patch.*|view_file|grep_search|find_by_name",
            "hooks": [{"type": "command", "command": "python ./scripts/entry.py --harness antigravity --event PreToolUse", "timeout": 10}]
        }]
    },
    "kessler-evidence-engine": {
        "PostToolUse": [{
            "matcher": "run_command|.*write.*|.*edit.*|.*replace.*|.*patch.*|view_file|grep_search|find_by_name",
            "hooks": [{"type": "command", "command": "python ./scripts/entry.py --harness antigravity --event PostToolUse", "timeout": 10}]
        }],
        "Stop": [{"type": "command", "command": "python ./scripts/entry.py --harness antigravity --event Stop", "timeout": 10}]
    }
}

KESSLER_CORE_RULE = '''---
trigger: always_on
description: "Minimal Kessler invariants. Detailed policies are enforced lazily by executable hooks."
---

# Kessler Core

Kessler is active. Keep these invariants only:

- Runtime evidence outranks assumption.
- Inspect first (read every file before citing it — a discovery entry without a real read is rejected). Before changing files, present and register a concrete plan: goal, purpose, justification (why, plus at least two future risks), users, usage flow, discovery, screen/controls/navigation (if UI), exact file placement, method, delivery, rollback, and validation. Revise it before changing scope.
- Inspect dependencies before elevated-risk edits.
- Never present placeholder or incomplete behavior as completed production integration.
- Obey Kessler hook decisions and policy IDs.
- State verification limits explicitly; do not claim a change is verified without executable evidence.

Detailed policies are loaded only when an event activates them. Do not preload the policy catalog into context.
'''

KESSLER_SKILL = '''---
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
'''

GEMINI_SKILL = '''---
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
'''

CLAUDE_CODE_CONTEXT = (
    "Kessler is active. Invariants: runtime evidence outranks assumption; inspect first — read every file before "
    "citing it in discovery, a citation with no read evidence is rejected (KES-READ-001) — before changing files, "
    "present and register a concrete implementation plan (goal, purpose, justification with why plus at least two "
    "future risks, users, usage flow, discovery, screen/controls/navigation if UI, exact file placement, method, "
    "delivery, rollback, validation) at .kessler/cache/implementation-plan.json with the file-write tool, and "
    "revise it before changing scope; UI plans must also include design_standards (touch_target_pt >=44, "
    "contrast_ratio >=4.5, supports_dynamic_type: true, respects_reduced_motion: true, 2+ responsive_breakpoints) "
    "unconditionally, and KES-VER-001 will also require a real accessibility/design check (axe, pa11y, Lighthouse "
    "CI) after implementation when the project has one available; a non_ui plan whose implementation touches a "
    "UI-surface file (.tsx/.jsx/.vue/.svelte/.html/.css/.scss/...) is rejected unless interface.non_ui_override_"
    "reason genuinely explains why — do not mislabel UI work as non_ui to dodge design_standards; inspect "
    "dependencies before elevated-risk edits; "
    "never present placeholder or incomplete behavior as completed production integration; obey Kessler hook "
    "decisions and policy IDs; state verification limits explicitly — do not claim a change is verified without "
    "executable evidence. Detailed policies are enforced locally and load into context only when a hook fires."
)

CLAUDE_CODE_SKILL = '''---
name: kessler-protocol
description: Applies Kessler engineering safety workflows for risky changes, KES-* policy interventions, verification evidence, residual risk, and blocked operations in Claude Code.
---

# Kessler Protocol

The deterministic hook engine enforces most policy without spending model context. When context is injected, act on the specific policy only.

Before implementation, inspect the project (actually read every file before citing it in discovery — KES-READ-001 rejects a citation with no read evidence) and present a concrete plan: goal, purpose, justification (why, plus at least two future risks), users, ordered usage flow, final screen, exact controls and navigation (for UI), exact files and placement, method, delivery (how the result reaches the user), rollback, and validation. Write the plan with a file-write tool to `.kessler/cache/implementation-plan.json` before changing project files. It must contain `goal`, `purpose`, `justification` (`why`, `future_risks`), `users`, `usage_flow` (2+ steps), `discovery` (already-read path and finding), `delivery`, `rollback`, `interface`, `implementation` (exact path, placement, method, responsibility), and `validation` (strings or `{description, command}`). For UI, `interface` needs `mode: "ui"`, `entry_point`, `final_screen`, `accessibility`, `states` (3+), `controls` (label, location, action, destination, failure, handler_path, evidence_path), `navigation` (from, via, to, evidence, evidence_path), and `design_standards` (`touch_target_pt` ≥44, `contrast_ratio` ≥4.5, `supports_dynamic_type: true`, `respects_reduced_motion: true`, `responsive_breakpoints` — 2+ named breakpoints) — required on every UI plan, unconditionally. Referenced paths must exist or be planned. For non-UI, use `mode: "non_ui"`, reason, entry_point, result, data_contract, failure_behavior, and side_effects (a list, may be empty). A `non_ui` plan whose implementation touches a UI-surface file (.tsx/.jsx/.vue/.svelte/.html/.css/.scss/...) is rejected unless `interface.non_ui_override_reason` genuinely explains why — reclassify as `mode: "ui"` instead of trying to dodge design_standards this way. Revise and re-present the plan before scope changes; test the actual user path.

- Inspect relevant dependencies before elevated-risk changes.
- Use detected executable verification (the project's real test/build/lint/typecheck command) after source/config writes; for UI work, that includes a real accessibility/design check (axe, pa11y, Lighthouse CI) whenever the project has one available (KES-VER-001) — the design_standards checklist alone is not verification.
- Never label incomplete or placeholder integration as production-complete.
- If verification is unavailable, disclose it and use a documented waiver (`kessler waive --reason "..."`) rather than fabricating success.
- Use `kessler explain <POLICY_ID>` for the full rule only when needed.
'''

ENTRY_PY = '''from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/"vendor"))
from kessler_protocol.hook_runtime import main
if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--harness",required=True); p.add_argument("--event",required=True)
    a=p.parse_args(); raise SystemExit(main(a.harness,a.event))
'''


def write_antigravity_template(dst: Path) -> None:
    dst=Path(dst)
    (dst/"rules").mkdir(parents=True,exist_ok=True)
    (dst/"skills/kessler-protocol").mkdir(parents=True,exist_ok=True)
    (dst/"scripts").mkdir(parents=True,exist_ok=True)
    (dst/"plugin.json").write_text(json.dumps(PLUGIN_JSON,indent=2)+"\n",encoding="utf-8")
    (dst/"hooks.json").write_text(json.dumps(HOOKS_JSON,indent=2)+"\n",encoding="utf-8")
    (dst/"rules/kessler-core.md").write_text(KESSLER_CORE_RULE,encoding="utf-8")
    (dst/"skills/kessler-protocol/SKILL.md").write_text(KESSLER_SKILL,encoding="utf-8")
    (dst/"scripts/entry.py").write_text(ENTRY_PY,encoding="utf-8")


def write_gemini_skill(dst: Path) -> None:
    dst=Path(dst); dst.mkdir(parents=True,exist_ok=True)
    (dst/"SKILL.md").write_text(GEMINI_SKILL,encoding="utf-8")


def write_claude_code_skill(dst: Path) -> None:
    dst=Path(dst); dst.mkdir(parents=True,exist_ok=True)
    (dst/"SKILL.md").write_text(CLAUDE_CODE_SKILL,encoding="utf-8")
