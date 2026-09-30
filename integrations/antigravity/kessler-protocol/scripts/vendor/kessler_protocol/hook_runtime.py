from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .adapters import ADAPTERS
from .config import load_config
from .decision import pre_decision, sensitive_target
from .evidence import record_read, record_search, record_write, source_like, tool_class
from .policies import match_policy
from .planning import is_plan_target, plan_decision, read_plan
from .profiler import get_profile
from .reports import session_summary
from .state import load, update
from .verification import classify_command, command_success, relevance, requirements, assess


def _read_payload(stream=None) -> dict:
    raw=(stream or sys.stdin).read()
    if not raw.strip(): return {}
    try: return json.loads(raw)
    except Exception as exc:
        print(f"[KESSLER] invalid hook JSON: {exc}", file=sys.stderr)
        return {}


def _root(adapter, payload) -> Path:
    try: return adapter.workspace(payload)
    except Exception: return Path.cwd().resolve()


def _record_intervention(session_id, workspace, result):
    if not result.get("policy_id") and result.get("decision") == "allow" and not result.get("message"):
        return
    def fn(st):
        st["interventions"].append({
            "policy_id": result.get("policy_id") or "KESSLER",
            "decision": result.get("decision", "allow"),
            "reason": result.get("reason") or result.get("message") or "",
            "time": time.time(),
        })
        st["interventions"] = st["interventions"][-200:]
    update(session_id, str(workspace), fn)


def before_tool(payload: dict, harness: str) -> dict:
    adapter=ADAPTERS[harness]
    workspace=_root(adapter,payload)
    cfg=load_config(workspace)
    profile=get_profile(workspace)
    session=adapter.session_id(payload)
    tool,args=adapter.tool(payload)
    command=adapter.command(tool,args)
    target=adapter.target(tool,args)
    content=adapter.content(tool,args)
    state=load(session,str(workspace))
    risk_result=pre_decision(harness=harness, command=command, target=target, content=content, workspace=workspace, profile=profile, cfg=cfg, state=state)
    plan_result=plan_decision(tool=tool, command=command, target=target, workspace=workspace, state=state)
    result=risk_result if risk_result.get("decision") == "deny" else (plan_result or risk_result)
    _record_intervention(session,workspace,result)
    return adapter.pre_output(result.get("decision","allow"), result.get("reason",""), result.get("message",""))


def after_tool(payload: dict, harness: str) -> dict:
    adapter=ADAPTERS[harness]
    workspace=_root(adapter,payload)
    cfg=load_config(workspace)
    profile=get_profile(workspace)
    session=adapter.session_id(payload)
    tool,args=adapter.tool(payload)
    command=adapter.command(tool,args)
    target=adapter.target(tool,args)
    content=adapter.content(tool,args)
    error,response=adapter.error_and_response(payload)
    cls=tool_class(tool)
    sensitive=sensitive_target(target,workspace,profile,cfg)
    fake=[p["id"] for p in match_policy("content",content)] if content else []

    def fn(st):
        st["profile_fingerprint"] = profile.get("fingerprint","")
        if cls == "write" and is_plan_target(target,workspace):
            if not error:
                digest, paths, errors, _discovery_paths, interface_mode = read_plan(workspace)
                if not errors and digest:
                    st["plan"] = {"sha256":digest,"paths":sorted(paths),"time":time.time(),"interface_mode":interface_mode}
                else:
                    st.pop("plan",None)
        elif cls == "read": record_read(st,target)
        elif cls == "search": record_search(st, str(args)[:500])
        elif cls == "write" and not error and (source_like(target) or sensitive): record_write(st,target,sensitive,fake)
        if command:
            kind=classify_command(command)
            if kind:
                success=command_success(error,response)
                st["verifications"].append({
                    "command": command[:1000], "kind": kind, "success": success,
                    "relevance": relevance(command,kind,profile), "time": time.time(),
                    "error": error[:1000] if error else "",
                })
                st["verifications"] = st["verifications"][-200:]
    update(session,str(workspace),fn)
    return adapter.post_output()


def completion(payload: dict, harness: str) -> dict:
    adapter=ADAPTERS[harness]
    workspace=_root(adapter,payload)
    profile=get_profile(workspace)
    cfg=load_config(workspace)
    session=adapter.session_id(payload)
    state=load(session,str(workspace))
    summary=session_summary(state,profile,profile.get("risk",{}).get("strictness","balanced"))
    if state.get("waiver"):
        update(session,str(workspace),lambda st: st.pop("plan",None))
        return adapter.completion_output(False)
    need_retry = bool(state.get("writes")) and not summary["verification"]["passed"]
    if need_retry:
        strict=profile.get("risk",{}).get("strictness","balanced")
        max_nudges={"balanced":1,"strict":2,"paranoid":3}.get(strict,1)
        if int(state.get("nudge_count",0)) < max_nudges:
            def fn(st): st["nudge_count"] = int(st.get("nudge_count",0)) + 1
            update(session,str(workspace),fn)
            missing=summary["verification"].get("missing") or []
            suffix=(" Missing: " + ", ".join(missing) + ".") if missing else ""
            reason=("KES-VER-001: source/config changes occurred after the latest successful relevant executable verification." + suffix +
                    " Run the most relevant detected check, or use `kessler waive --workspace . --reason \"...\"` when verification is genuinely unavailable. Do not claim verified status without evidence.")
            return adapter.completion_output(True,reason)
    if state.get("plan"):
        update(session,str(workspace),lambda st: st.pop("plan",None))
    return adapter.completion_output(False)


def before_agent(payload: dict, harness: str) -> dict:
    if harness == "gemini":
        return {"hookSpecificOutput": {"additionalContext":
            "Kessler: inspect the project (read every file you cite), then present a complete implementation plan "
            "before changing files. Cover goal, purpose, justification (why, plus at least two future risks), users, "
            "usage flow, discovery (files actually read), screen and controls, navigation, exact files and placement, "
            "method, delivery, rollback, and validation. For UI plans, also cover design_standards (touch_target_pt "
            ">=44, contrast_ratio >=4.5, supports_dynamic_type: true, respects_reduced_motion: true, 2+ "
            "responsive_breakpoints), required unconditionally; KES-VER-001 also requires a real accessibility/design "
            "check (axe, pa11y, Lighthouse CI) after implementation when the project has one available. A non_ui plan "
            "whose implementation touches a UI-surface file (.tsx/.jsx/.vue/.svelte/.html/.css/.scss/...) is rejected "
            "unless interface.non_ui_override_reason genuinely explains why — do not mislabel UI work as non_ui to "
            "dodge design_standards. Register the plan at .kessler/cache/implementation-plan.json using the "
            "file-write tool; revise it before scope changes."}}
    if harness == "claude_code":
        from .templates import CLAUDE_CODE_CONTEXT
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": CLAUDE_CODE_CONTEXT}}
    return {}


def run(harness: str, event: str, payload: dict) -> dict:
    ev=event.lower()
    if ev in {"beforeagent","userpromptsubmit"}: return before_agent(payload,harness)
    if ev in {"pretooluse","beforetool"}: return before_tool(payload,harness)
    if ev in {"posttooluse","aftertool"}: return after_tool(payload,harness)
    if ev in {"stop","afteragent"}: return completion(payload,harness)
    return {}


def main(harness: str, event: str) -> int:
    payload=_read_payload()
    out=run(harness,event,payload)
    sys.stdout.write(json.dumps(out,separators=(",",":"),ensure_ascii=False)+"\n")
    return 0
