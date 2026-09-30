from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .hook_runtime import run
from .installers import get_manifest
from .policies import load_policies
from .profiler import build_profile
from .templates import PLUGIN_JSON, HOOKS_JSON, KESSLER_CORE_RULE, KESSLER_SKILL, GEMINI_SKILL, CLAUDE_CODE_SKILL

PACKAGE_DIR=Path(__file__).resolve().parent
REPO_ROOT=PACKAGE_DIR.parents[1] if (PACKAGE_DIR.parents[1]/"pyproject.toml").exists() else None


def _check_json(path: Path):
    try: json.loads(path.read_text(encoding="utf-8")); return True,"valid JSON"
    except Exception as exc: return False,f"invalid JSON: {exc}"


def package_checks(deep: bool=False):
    rows=[
        (PLUGIN_JSON.get("name")=="kessler-protocol","template.plugin","valid plugin template"),
        (bool(HOOKS_JSON.get("kessler-risk-gate")),"template.hooks","hook template present"),
        ("trigger: always_on" in KESSLER_CORE_RULE,"template.rule","valid minimal always-on rule"),
        ("description:" in KESSLER_SKILL,"template.skill","Antigravity skill template present"),
        ("description:" in GEMINI_SKILL,"template.gemini-skill","Gemini skill template present"),
        ("description:" in CLAUDE_CODE_SKILL,"template.claude-code-skill","Claude Code skill template present"),
        (len(load_policies()) >= 6,"policy.catalog","policy catalog loaded"),
    ]
    if REPO_ROOT:
        required=[
            REPO_ROOT/"integrations/antigravity/kessler-protocol/plugin.json",
            REPO_ROOT/"integrations/antigravity/kessler-protocol/hooks.json",
            REPO_ROOT/"integrations/antigravity/kessler-protocol/rules/kessler-core.md",
            REPO_ROOT/"integrations/antigravity/kessler-protocol/skills/kessler-protocol/SKILL.md",
            REPO_ROOT/"integrations/gemini-cli/skill/kessler-protocol/SKILL.md",
            REPO_ROOT/"integrations/claude-code/skill/kessler-protocol/SKILL.md",
        ]
        for p in required: rows.append((p.exists(),str(p.relative_to(REPO_ROOT)),"present" if p.exists() else "missing"))
        for rel in ["integrations/antigravity/kessler-protocol/plugin.json","integrations/antigravity/kessler-protocol/hooks.json"]:
            ok,msg=_check_json(REPO_ROOT/rel); rows.append((ok,rel,msg))
    if deep:
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"package.json").write_text(json.dumps({"scripts":{"test":"vitest","build":"next build"},"dependencies":{"next":"1","@prisma/client":"1","next-auth":"1","stripe":"1"}}))
            (root/"src/auth").mkdir(parents=True); (root/"src/auth/login.ts").write_text("export {}")
            (root/"prisma/migrations").mkdir(parents=True)
            profile=build_profile(root)
            rows.append((profile["risk"]["level"] in {"HIGH","CRITICAL"},"deep.profile","auto risk/profile detection"))
            payload={"conversationId":"doctor","workspacePaths":[str(root)],"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf /","Cwd":str(root)}}}
            out=run("antigravity","PreToolUse",payload)
            rows.append((out.get("decision")=="deny","deep.hook","catastrophic command denied"))
    return rows


def _run_entry(entry: Path, harness: str, event: str, payload: dict):
    cp=subprocess.run([sys.executable,str(entry),"--harness",harness,"--event",event],input=json.dumps(payload),text=True,capture_output=True,timeout=10)
    if cp.returncode!=0: return False,cp.stderr.strip() or f"exit {cp.returncode}"
    try: return True,json.loads(cp.stdout)
    except Exception as exc: return False,f"invalid JSON output: {exc}: {cp.stdout[:200]}"


def installed_checks(target: str, scope: str, workspace: Path, surface: str, deep: bool=False):
    rows=[]; m=get_manifest(target,scope,workspace,surface)
    rows.append((bool(m),"installation manifest","present" if m else "missing"))
    if target=="antigravity":
        if m: base=Path(m.get("installed_path",""))
        elif scope=="workspace": base=workspace.resolve()/".agents/plugins/kessler-protocol"
        elif surface=="cli": base=Path.home()/".gemini/antigravity-cli/plugins/kessler-protocol"
        else: base=Path.home()/".gemini/config/plugins/kessler-protocol"
        for name in ["plugin.json","hooks.json","rules/kessler-core.md","skills/kessler-protocol/SKILL.md","scripts/entry.py","scripts/vendor/kessler_protocol/hook_runtime.py"]:
            p=base/name; rows.append((p.exists(),str(p),"present" if p.exists() else "missing"))
        if deep and (base/"scripts/entry.py").exists():
            with tempfile.TemporaryDirectory() as td:
                payload={"conversationId":"doctor-installed","workspacePaths":[td],"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf /","Cwd":td}}}
                ok,out=_run_entry(base/"scripts/entry.py","antigravity","PreToolUse",payload)
                rows.append((ok and isinstance(out,dict) and out.get("decision")=="deny","deep.installed-hook",str(out)))
    elif target=="claude_code":
        base=(Path.home()/".claude") if scope=="user" else workspace.resolve()/".claude"
        skill=Path(m.get("skill_path",base/"skills/kessler-protocol")) if m else base/"skills/kessler-protocol"
        runtime=Path(m.get("runtime_path",base/"kessler/runtime")) if m else base/"kessler/runtime"
        settings=Path(m.get("settings_path",base/"settings.json")) if m else base/"settings.json"
        for p,label in [(skill/"SKILL.md","skill"),(runtime/"entry.py","runtime"),(settings,"settings")]: rows.append((p.exists(),str(p),label))
        if settings.exists():
            try:
                data=json.loads(settings.read_text(encoding="utf-8")); marker=str(runtime/"entry.py")
                events_seen=set()
                for event,groups in data.get("hooks",{}).items():
                    if not isinstance(groups,list): continue
                    for g in groups:
                        for h in (g.get("hooks",[]) if isinstance(g,dict) else []):
                            if isinstance(h,dict) and marker in str(h.get("command","")): events_seen.add(event)
                for expected in ["UserPromptSubmit","PreToolUse","PostToolUse","Stop"]:
                    rows.append((expected in events_seen,f"claude-code-hook.{expected}","registered" if expected in events_seen else "missing"))
            except Exception as exc: rows.append((False,str(settings),f"cannot parse: {exc}"))
        if deep and (runtime/"entry.py").exists():
            with tempfile.TemporaryDirectory() as td:
                payload={"session_id":"doctor-installed","cwd":td,"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}
                ok,out=_run_entry(runtime/"entry.py","claude_code","PreToolUse",payload)
                denied=ok and isinstance(out,dict) and out.get("hookSpecificOutput",{}).get("permissionDecision") in {"deny","ask"}
                rows.append((denied,"deep.installed-hook",str(out)))
    else:
        base=(Path.home()/".gemini") if scope=="user" else workspace.resolve()/".gemini"
        skill=Path(m.get("skill_path",base/"skills/kessler-protocol")) if m else base/"skills/kessler-protocol"
        runtime=Path(m.get("runtime_path",base/"kessler/runtime")) if m else base/"kessler/runtime"
        settings=Path(m.get("settings_path",base/"settings.json")) if m else base/"settings.json"
        for p,label in [(skill/"SKILL.md","skill"),(runtime/"entry.py","runtime"),(settings,"settings")]: rows.append((p.exists(),str(p),label))
        if settings.exists():
            try:
                data=json.loads(settings.read_text(encoding="utf-8")); names=[]
                for groups in data.get("hooks",{}).values():
                    if isinstance(groups,list):
                        for g in groups:
                            for h in g.get("hooks",[]) if isinstance(g,dict) else []:
                                if isinstance(h,dict): names.append(h.get("name"))
                for expected in ["kessler-before-agent","kessler-before-tool","kessler-after-tool","kessler-after-agent"]: rows.append((expected in names,expected,"registered" if expected in names else "missing"))
            except Exception as exc: rows.append((False,str(settings),f"cannot parse: {exc}"))
        if deep and (runtime/"entry.py").exists():
            with tempfile.TemporaryDirectory() as td:
                payload={"session_id":"doctor-installed","cwd":td,"tool_name":"run_shell_command","tool_input":{"command":"dd if=/dev/zero of=/dev/sda"}}
                ok,out=_run_entry(runtime/"entry.py","gemini","BeforeTool",payload)
                rows.append((ok and isinstance(out,dict) and out.get("decision")=="deny","deep.installed-hook",str(out)))
    return rows
