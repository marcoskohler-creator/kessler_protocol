#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

WRITE_TOOLS_AG = {"write_to_file", "replace_file_content", "multi_replace_file_content"}
WRITE_TOOLS_GEMINI = {"write_file", "replace"}

HARD_DENY_PATTERNS = [
    re.compile(r"(^|[;&|]\s*)rm\s+-rf\s+/(?:\s|$|[*])", re.I),
    re.compile(r"\bmkfs(?:\.|\s)", re.I),
    re.compile(r"\bdd\s+[^\n]*\bof=/dev/", re.I),
    re.compile(r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;\s*:", re.I),
]
ASK_PATTERNS = [
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-[^\s]*[fdx][^\s]*", re.I),
    re.compile(r"\brm\s+-rf\b", re.I),
    re.compile(r"\b(?:drop\s+(?:table|database)|truncate\s+table)\b", re.I),
]
VERIFY_PATTERNS = [
    re.compile(p, re.I) for p in [
        r"(^|\s)(pytest|python\s+-m\s+pytest)(\s|$)",
        r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?(test|build|lint|typecheck|check)(\s|$)",
        r"(^|\s)cargo\s+(test|check|clippy)(\s|$)",
        r"(^|\s)go\s+test(\s|$)",
        r"(^|\s)(mvn|mvnw)(\s+[^;&|]+)?\s+(test|verify|package)(\s|$)",
        r"(^|\s)(gradle|gradlew)(\s+[^;&|]+)?\s+(test|check|build)(\s|$)",
        r"(^|\s)(tsc|ruff|eslint|mypy|pyright)(\s|$)",
    ]
]
SENSITIVE_PATH = re.compile(r"(^|[/\\])(?:\.env(?:\.|$)|secrets?|credentials?|auth(?:entication|orization)?|iam|migrations?)([/\\]|$)", re.I)
SOURCE_EXT = re.compile(r"\.(py|js|jsx|ts|tsx|go|rs|java|kt|kts|cs|cpp|c|h|hpp|rb|php|swift|sql|tf|yaml|yml|json)$", re.I)

def eprint(*a): print(*a, file=sys.stderr)

def read_payload():
    raw=sys.stdin.read()
    if not raw.strip(): return {}
    try: return json.loads(raw)
    except Exception as exc:
        eprint(f"[KESSLER] invalid hook JSON: {exc}")
        return {}

def session_key(payload, harness):
    sid = payload.get("conversationId") if harness=="antigravity" else payload.get("session_id")
    if not sid: sid = payload.get("transcriptPath") or payload.get("transcript_path") or "unknown"
    return hashlib.sha256(str(sid).encode()).hexdigest()[:32]

def state_path(payload,harness):
    base=Path.home()/".kessler"/"state"
    base.mkdir(parents=True,exist_ok=True)
    return base/(session_key(payload,harness)+".json")

def load_state(payload,harness):
    p=state_path(payload,harness)
    if not p.exists(): return {"dirty":False,"last_write":0,"last_verify":0,"nudge_count":0,"last_error":""}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {"dirty":False,"last_write":0,"last_verify":0,"nudge_count":0,"last_error":""}

def save_state(payload,harness,state):
    p=state_path(payload,harness)
    tmp=p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
    os.replace(tmp,p)

def ag_tool(payload):
    tc=payload.get("toolCall") or {}
    return str(tc.get("name") or ""), tc.get("args") or {}

def gem_tool(payload):
    return str(payload.get("tool_name") or ""), payload.get("tool_input") or {}

def extract_command(tool,args,harness):
    if harness=="antigravity" and tool=="run_command": return str(args.get("CommandLine") or "")
    if harness=="gemini" and tool=="run_shell_command":
        return str(args.get("command") or args.get("CommandLine") or "")
    return ""

def extract_target(tool,args,harness):
    keys=("TargetFile","path","file_path","file","target") if harness=="antigravity" else ("file_path","path","filename","target_file")
    for k in keys:
        v=args.get(k)
        if isinstance(v,str) and v: return v
    return ""

def is_write(tool,harness):
    if harness=="antigravity": return tool in WRITE_TOOLS_AG
    return tool in WRITE_TOOLS_GEMINI or bool(re.search(r"write|edit|replace",tool,re.I))

def hard_deny(command): return any(p.search(command) for p in HARD_DENY_PATTERNS)
def needs_ask(command): return any(p.search(command) for p in ASK_PATTERNS)
def is_verification(command): return any(p.search(command) for p in VERIFY_PATTERNS)

def pre_tool(payload,harness):
    tool,args = ag_tool(payload) if harness=="antigravity" else gem_tool(payload)
    command=extract_command(tool,args,harness)
    target=extract_target(tool,args,harness)
    if command and hard_deny(command):
        reason="Kessler R4 gate: command matches a narrowly-defined catastrophic filesystem/device pattern."
        return {"decision":"deny","reason":reason} if harness=="antigravity" else {"decision":"deny","reason":reason}
    elevated = bool(command and needs_ask(command)) or bool(target and SENSITIVE_PATH.search(target))
    if elevated:
        reason="Kessler R4/R3 gate: destructive or security-sensitive operation requires explicit human awareness."
        if harness=="antigravity": return {"decision":"force_ask","reason":reason}
        return {"decision":"allow","systemMessage":reason}
    return {"decision":"allow"} if harness=="antigravity" else {"decision":"allow"}

def post_tool(payload,harness):
    tool,args = ag_tool(payload) if harness=="antigravity" else gem_tool(payload)
    error = payload.get("error") if harness=="antigravity" else ((payload.get("tool_response") or {}).get("error"))
    state=load_state(payload,harness)
    now=time.time()
    if error:
        state["last_error"]=str(error)[:1000]
    else:
        if is_write(tool,harness):
            target=extract_target(tool,args,harness)
            # Track source/config writes; docs-only edits do not trigger completion verification.
            if not target or SOURCE_EXT.search(target) or SENSITIVE_PATH.search(target):
                state["dirty"]=True; state["last_write"]=now; state["nudge_count"]=0
        command=extract_command(tool,args,harness)
        if command and is_verification(command):
            state["last_verify"]=now
            if now >= float(state.get("last_write",0)): state["dirty"]=False
            state["last_error"]=""
    save_state(payload,harness,state)
    return {}

def completion(payload,harness):
    state=load_state(payload,harness)
    dirty=bool(state.get("dirty")) and float(state.get("last_verify",0)) < float(state.get("last_write",0))
    if dirty and int(state.get("nudge_count",0)) < 1:
        state["nudge_count"]=int(state.get("nudge_count",0))+1
        save_state(payload,harness,state)
        reason=("Kessler verification gate: source/config changes were recorded after the latest recognized test/build/lint/typecheck. "
                "Run the most relevant executable verification now, or explicitly explain why no executable verification is available. "
                "Do not claim the change is verified without evidence.")
        if harness=="antigravity": return {"decision":"continue","reason":reason}
        return {"decision":"deny","reason":reason}
    if harness=="antigravity": return {"decision":"allow"}
    return {"decision":"allow"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--harness",choices=["antigravity","gemini"],required=True)
    ap.add_argument("--event",required=True)
    args=ap.parse_args()
    payload=read_payload()
    event=args.event.lower()
    if event in {"pretooluse","beforetool"}: out=pre_tool(payload,args.harness)
    elif event in {"posttooluse","aftertool"}: out=post_tool(payload,args.harness)
    elif event in {"stop","afteragent"}: out=completion(payload,args.harness)
    else: out={}
    sys.stdout.write(json.dumps(out,separators=(",",":")))
    sys.stdout.write("\n")
    return 0

if __name__=="__main__": raise SystemExit(main())
