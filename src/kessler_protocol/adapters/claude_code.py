from __future__ import annotations
import json
from pathlib import Path

# Payload/response shapes follow the official Claude Code hooks reference
# (docs.claude.com/en/docs/claude-code/hooks): PreToolUse/PostToolUse/Stop/
# UserPromptSubmit stdin fields (session_id, cwd, tool_name, tool_input,
# tool_output, ...) and the hookSpecificOutput stdout contract
# (permissionDecision: allow|deny|ask; decision: block|none; additionalContext).


class ClaudeCodeAdapter:
    name = "claude_code"

    def session_id(self, payload: dict) -> str:
        return str(payload.get("session_id") or payload.get("transcript_path") or "unknown")

    def workspace(self, payload: dict) -> Path:
        return Path(payload.get("cwd") or ".").resolve()

    def tool(self, payload: dict):
        return str(payload.get("tool_name") or ""), payload.get("tool_input") or {}

    def command(self, tool: str, args: dict) -> str:
        return str(args.get("command") or "") if tool == "Bash" else ""

    def target(self, tool: str, args: dict) -> str:
        for key in ("file_path", "path", "notebook_path"):
            v = args.get(key)
            if isinstance(v, str) and v:
                return v
        return ""

    def content(self, tool: str, args: dict) -> str:
        parts = []
        for key in ("content", "new_string", "new_source"):
            if isinstance(args.get(key), str):
                parts.append(args[key])
        edits = args.get("edits")
        if isinstance(edits, list):
            for e in edits:
                if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                    parts.append(e["new_string"])
        return "\n".join(parts)

    def error_and_response(self, payload: dict) -> tuple[str, str]:
        out = payload.get("tool_output")
        if isinstance(out, dict):
            error = str(out.get("error") or "") if (out.get("is_error") or out.get("error")) else ""
            try:
                text = json.dumps(out, ensure_ascii=False, default=str)
            except Exception:
                text = str(out)
            return error, text[:20000]
        return "", str(out or "")[:20000]

    def pre_output(self, decision: str, reason: str = "", message: str = "") -> dict:
        mapped = {"deny": "deny", "force_ask": "ask", "allow": "allow"}.get(decision, "allow")
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": mapped}}
        if reason:
            out["hookSpecificOutput"]["permissionDecisionReason"] = reason
        if message:
            out["systemMessage"] = message
        return out

    def post_output(self) -> dict:
        return {}

    def completion_output(self, retry: bool, reason: str = "") -> dict:
        if retry:
            return {"hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": reason}}
        return {}
