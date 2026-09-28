from __future__ import annotations
import json
from pathlib import Path

class GeminiAdapter:
    name = "gemini"

    def session_id(self, payload: dict) -> str:
        return str(payload.get("session_id") or payload.get("transcript_path") or "unknown")

    def workspace(self, payload: dict) -> Path:
        return Path(payload.get("cwd") or ".").resolve()

    def tool(self, payload: dict):
        return str(payload.get("tool_name") or ""), payload.get("tool_input") or {}

    def command(self, tool: str, args: dict) -> str:
        return str(args.get("command") or args.get("CommandLine") or "") if tool == "run_shell_command" else ""

    def target(self, tool: str, args: dict) -> str:
        for key in ("file_path", "path", "filename", "target_file", "directory_path"):
            v=args.get(key)
            if isinstance(v, str) and v: return v
        return ""

    def content(self, tool: str, args: dict) -> str:
        parts=[]
        for key in ("content", "new_string", "replacement", "instruction"):
            if isinstance(args.get(key), str): parts.append(args[key])
        return "\n".join(parts)

    def error_and_response(self, payload: dict) -> tuple[str, str]:
        tr = payload.get("tool_response") or {}
        error = str(tr.get("error") or "") if isinstance(tr, dict) else ""
        try: text=json.dumps(tr, ensure_ascii=False, default=str)
        except Exception: text=str(tr)
        return error, text[:20000]

    def pre_output(self, decision: str, reason: str = "", message: str = "") -> dict:
        # Gemini hooks support allow/deny but not force_ask. Caller maps confirmation semantics.
        out={"decision": decision}
        if reason: out["reason"] = reason
        if message: out["systemMessage"] = message
        return out

    def post_output(self) -> dict: return {}

    def completion_output(self, retry: bool, reason: str = "") -> dict:
        # AfterAgent deny is the available hard validation signal.
        return {"decision": "deny", "reason": reason} if retry else {"decision": "allow"}
