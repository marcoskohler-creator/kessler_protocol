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
            "matcher": "run_command|write_to_file|replace_file_content|multi_replace_file_content|view_file|grep_search|find_by_name",
            "hooks": [{"type": "command", "command": "python ./scripts/entry.py --harness antigravity --event PreToolUse", "timeout": 10}]
        }]
    },
    "kessler-evidence-engine": {
        "PostToolUse": [{
            "matcher": "run_command|write_to_file|replace_file_content|multi_replace_file_content|view_file|grep_search|find_by_name",
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

Use executable evidence rather than assumptions. The hook engine performs deterministic enforcement outside the model context; this skill is only for the reasoning that remains.

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

- Inspect relevant dependencies before elevated-risk changes.
- Use detected executable verification after source/config writes.
- Never label incomplete or placeholder integration as production-complete.
- If verification is unavailable, disclose it and use a documented waiver rather than fabricating success.
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
