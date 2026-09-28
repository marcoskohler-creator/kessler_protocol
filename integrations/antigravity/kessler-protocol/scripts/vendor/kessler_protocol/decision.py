from __future__ import annotations

import fnmatch
import re
import time
from pathlib import Path

from .config import path_matches
from .evidence import has_discovery_before
from .policies import match_policy


def _compact(policy: dict, context_mode: str) -> str:
    if context_mode == "lean":
        return f"{policy['id']}: {policy['summary']}"
    if context_mode == "standard":
        return f"{policy['id']} — {policy['title']}: {policy['summary']} Required: {policy['remediation']}"
    return f"{policy['id']} — {policy['title']} [{policy['severity']}]. {policy['summary']} Remediation: {policy['remediation']}"


def _custom_command(command: str, cfg: dict) -> tuple[str | None, str]:
    for pat in cfg.get("commands", {}).get("deny", []):
        try:
            if re.search(pat, command, re.I): return "deny", f"Project policy denied command pattern: {pat}"
        except re.error:
            if pat.lower() in command.lower(): return "deny", f"Project policy denied command: {pat}"
    for pat in cfg.get("commands", {}).get("allow", []):
        try:
            if re.search(pat, command, re.I): return "allow", ""
        except re.error:
            if pat.lower() in command.lower(): return "allow", ""
    return None, ""


def sensitive_target(target: str, workspace: Path, profile: dict, cfg: dict) -> bool:
    if not target: return False
    try:
        p=Path(target)
        rel = p.resolve().relative_to(workspace.resolve()).as_posix() if p.is_absolute() else p.as_posix()
    except Exception:
        rel = str(target).replace("\\", "/")
    if path_matches(rel, cfg.get("paths", {}).get("sensitive", [])):
        return True
    # Profile may contain concrete paths or user globs.
    for pat in profile.get("sensitive_paths", []):
        pn=str(pat).replace("\\", "/")
        if rel == pn or rel.startswith(pn.rstrip("/") + "/") or fnmatch.fnmatch(rel, pn):
            return True
    return bool(match_policy("path", rel))


def pre_decision(*, harness: str, command: str, target: str, content: str, workspace: Path, profile: dict, cfg: dict, state: dict) -> dict:
    mode = cfg.get("context", "lean")
    strict = profile.get("risk", {}).get("strictness", "balanced")
    if command:
        custom, reason = _custom_command(command, cfg)
        if custom == "deny": return {"decision": "deny", "policy_id": "PROJECT-DENY", "reason": reason}
        if custom != "allow":
            matches = match_policy("command", command)
            if matches:
                p = sorted(matches, key=lambda x: x.get("severity", "R0"), reverse=True)[0]
                if p["action"] == "deny": return {"decision": "deny", "policy_id": p["id"], "reason": _compact(p, mode)}
                if p["action"] == "confirm":
                    if harness == "antigravity": return {"decision": "force_ask", "policy_id": p["id"], "reason": _compact(p, mode)}
                    return {"decision": "deny", "policy_id": p["id"], "reason": _compact(p, mode) + " Explicit user authorization is required before retrying through the agent."}
    sensitive = sensitive_target(target, workspace, profile, cfg)
    if sensitive and strict in {"strict", "paranoid"}:
        has_discovery = bool(state.get("reads") or state.get("searches"))
        p = next((x for x in match_policy("path", target) if x["id"] == "KES-SEC-001"), None)
        reason = _compact(p, mode) if p else "KES-SEC-001: sensitive boundary modification detected."
        if not has_discovery:
            reason += " No prior read/search evidence is recorded for this session."
        if harness == "antigravity":
            return {"decision": "force_ask", "policy_id": "KES-SEC-001", "reason": reason}
        if strict == "paranoid":
            return {"decision": "deny", "policy_id": "KES-SEC-001", "reason": reason}
        return {"decision": "allow", "policy_id": "KES-SEC-001", "message": reason}
    # Fake-success patterns are advisory, never deterministic proof.
    if content and strict in {"strict", "paranoid"}:
        matches=match_policy("content", content)
        if matches:
            p=matches[0]
            return {"decision": "allow", "policy_id": p["id"], "message": _compact(p, mode)}
    return {"decision": "allow", "policy_id": None, "reason": "", "message": ""}
