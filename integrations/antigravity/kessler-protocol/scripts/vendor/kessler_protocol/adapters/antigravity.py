from __future__ import annotations
from pathlib import Path

class AntigravityAdapter:
    name = "antigravity"

    def session_id(self, payload: dict) -> str:
        return str(payload.get("conversationId") or payload.get("transcriptPath") or "unknown")

    def workspace(self, payload: dict) -> Path:
        paths = payload.get("workspacePaths") or []
        if paths: return Path(paths[0]).resolve()
        tool, args = self.tool(payload)
        cwd = args.get("Cwd") if isinstance(args, dict) else None
        return Path(cwd or ".").resolve()

    def tool(self, payload: dict):
        tc = payload.get("toolCall") or {}
        return str(tc.get("name") or ""), tc.get("args") or {}

    def command(self, tool: str, args: dict) -> str:
        return str(args.get("CommandLine") or "") if tool == "run_command" else ""

    def target(self, tool: str, args: dict) -> str:
        for key in ("TargetFile", "AbsolutePath", "SearchPath", "DirectoryPath", "path", "file_path", "target"):
            v=args.get(key)
            if isinstance(v, str) and v: return v
        return ""

    def content(self, tool: str, args: dict) -> str:
        parts=[]
        for key in ("CodeContent", "ReplacementContent", "Instruction"):
            if isinstance(args.get(key), str): parts.append(args[key])
        chunks=args.get("ReplacementChunks")
        if isinstance(chunks, list):
            for ch in chunks:
                if isinstance(ch, dict):
                    for key in ("ReplacementContent", "TargetContent"):
                        if isinstance(ch.get(key), str): parts.append(ch[key])
        return "\n".join(parts)

    def error_and_response(self, payload: dict) -> tuple[str, str]:
        return str(payload.get("error") or ""), ""

    def pre_output(self, decision: str, reason: str = "", message: str = "") -> dict:
        out={"decision": decision}
        if reason: out["reason"] = reason
        return out

    def post_output(self) -> dict: return {}

    def completion_output(self, retry: bool, reason: str = "") -> dict:
        return {"decision": "continue", "reason": reason} if retry else {"decision": "allow"}
