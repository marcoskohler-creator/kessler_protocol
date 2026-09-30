from __future__ import annotations

from .verification import assess, requirements


def session_summary(state: dict, profile: dict, strictness: str) -> dict:
    writes = state.get("writes", [])
    changed = [x.get("path", "") for x in writes]
    sensitive = any(x.get("sensitive") for x in writes)
    last_write = max([float(x.get("time", 0)) for x in writes] or [0.0])
    ui = state.get("plan", {}).get("interface_mode") == "ui"
    req = requirements(profile, changed, strictness, sensitive, ui=ui)
    ver = assess(state.get("verifications", []), last_write, req) if writes else {"passed": True, "missing": [], "successful_after_write": 0, "relevant_after_write": 0, "max_relevance": "none"}
    discovery = bool(state.get("reads") or state.get("searches"))
    residual = "LOW"
    if writes and not ver["passed"]: residual = "HIGH" if sensitive else "MODERATE"
    elif sensitive: residual = "MODERATE"
    confidence = 100
    if writes and not ver["passed"]: confidence -= 35
    if sensitive and not discovery: confidence -= 20
    confidence -= min(20, len([x for x in state.get("verifications", []) if not x.get("success")]) * 5)
    confidence = max(0, confidence)
    return {
        "risk_level": profile.get("risk", {}).get("level", "UNKNOWN"),
        "strictness": strictness,
        "files_modified": len(writes),
        "sensitive_writes": sum(1 for x in writes if x.get("sensitive")),
        "reads": len(state.get("reads", [])),
        "searches": len(state.get("searches", [])),
        "interventions": state.get("interventions", []),
        "verification": ver,
        "required_verification": req,
        "residual_risk": residual,
        "completion_confidence": confidence,
    }


def to_markdown(summary: dict) -> str:
    lines=[
        "# Kessler Session Report", "",
        f"- Project risk: **{summary['risk_level']}**",
        f"- Effective strictness: **{summary['strictness']}**",
        f"- Files modified: **{summary['files_modified']}**",
        f"- Sensitive writes: **{summary['sensitive_writes']}**",
        f"- Read/search evidence: **{summary['reads']} reads / {summary['searches']} searches**",
        f"- Verification: **{'PASS' if summary['verification']['passed'] else 'INCOMPLETE'}**",
        f"- Residual risk: **{summary['residual_risk']}**",
        f"- Completion confidence: **{summary['completion_confidence']}%**", "",
        "## Required verification", "",
    ]
    lines += [f"- {x}" for x in summary.get("required_verification", [])] or ["- No project-specific executable verification was detected."]
    lines += ["", "## Interventions", ""]
    lines += [f"- `{x.get('policy_id','?')}` — {x.get('decision','')} — {x.get('reason','')}" for x in summary.get("interventions", [])] or ["- None."]
    return "\n".join(lines) + "\n"
