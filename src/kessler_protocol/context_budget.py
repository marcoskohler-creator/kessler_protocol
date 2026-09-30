from __future__ import annotations
import math
from .templates import KESSLER_CORE_RULE, KESSLER_SKILL

def approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text)/4))

def measure() -> dict:
    core=KESSLER_CORE_RULE; skill=KESSLER_SKILL
    desc=""
    for line in skill.splitlines():
        if line.startswith("description:"):
            desc=line.split(":",1)[1].strip().strip('"'); break
    return {
        "always_on":{"chars":len(core),"approx_tokens":approx_tokens(core),"source":"kessler-core.md template"},
        "skill_discovery":{"chars":len(desc),"approx_tokens":approx_tokens(desc),"source":"SKILL.md description"},
        "lazy_skill_full":{"chars":len(skill),"approx_tokens":approx_tokens(skill),"loaded_only_when_relevant":True},
        "policy_catalog_prompt_tokens":0,
        "policy_catalog_note":"Policies execute locally. Only the active intervention summary is emitted to the agent.",
        "budget_targets":{"always_on_approx_tokens_max":260,"normal_intervention_approx_tokens_max":160}
    }
