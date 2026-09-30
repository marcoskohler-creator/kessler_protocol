from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import init_config, load_config
from .context_budget import measure as context_budget
from .doctor import package_checks, installed_checks
from .hook_runtime import main as hook_main
from .installers import install_antigravity, install_gemini, install_claude_code, uninstall_antigravity, uninstall_gemini, uninstall_claude_code, rollback
from .policies import get_policy
from .profiler import get_profile
from .reports import session_summary, to_markdown
from .state import latest, update


def emit(obj, as_json=False):
    if as_json: print(json.dumps(obj,indent=2,ensure_ascii=False,default=str)); return
    if isinstance(obj,dict):
        for k,v in obj.items(): print(f"{k}: {v}")
    else: print(obj)


def _surface(target,args):
    return args.surface if getattr(args,"surface",None) else ("ide" if target=="antigravity" else "cli")


def main(argv=None):
    p=argparse.ArgumentParser(prog="kessler",description="Kessler Protocol — deterministic safety and evidence layer for agentic coding")
    sub=p.add_subparsers(dest="cmd",required=True)

    sp=sub.add_parser("init",help="Create minimal project config and auto-profile the workspace")
    sp.add_argument("--workspace",default="."); sp.add_argument("--force",action="store_true"); sp.add_argument("--json",action="store_true")
    sp=sub.add_parser("profile",help="Show auto-detected project profile")
    sp.add_argument("--workspace",default="."); sp.add_argument("--refresh",action="store_true"); sp.add_argument("--json",action="store_true")
    sp=sub.add_parser("budget",help="Measure Kessler prompt/context budget")
    sp.add_argument("--json",action="store_true")
    sp=sub.add_parser("explain",help="Explain a policy ID")
    sp.add_argument("policy_id"); sp.add_argument("--json",action="store_true")

    for name in ("install","uninstall","rollback"):
        sp=sub.add_parser(name)
        sp.add_argument("--target",choices=["antigravity","gemini","claude_code"],required=True)
        sp.add_argument("--scope",choices=["user","workspace"],default="user")
        sp.add_argument("--surface",choices=["ide","cli"],default=None)
        sp.add_argument("--workspace",default="."); sp.add_argument("--json",action="store_true")
        if name=="uninstall": sp.add_argument("--no-restore",action="store_true")

    sp=sub.add_parser("doctor")
    sp.add_argument("--target",choices=["package","antigravity","gemini","claude_code"],default="package")
    sp.add_argument("--scope",choices=["user","workspace"],default="user"); sp.add_argument("--surface",choices=["ide","cli"],default=None)
    sp.add_argument("--workspace",default="."); sp.add_argument("--deep",action="store_true"); sp.add_argument("--json",action="store_true")

    sp=sub.add_parser("report")
    sp.add_argument("--workspace",default="."); sp.add_argument("--json",action="store_true")
    sp=sub.add_parser("waive")
    sp.add_argument("--workspace",default="."); sp.add_argument("--reason",required=True); sp.add_argument("--json",action="store_true")

    # Internal stable entry point used by installed hook adapters.
    sp=sub.add_parser("hook")
    sp.add_argument("--harness",choices=["antigravity","gemini","claude_code"],required=True); sp.add_argument("--event",required=True)

    args=p.parse_args(argv); ws=Path(getattr(args,"workspace",".")).resolve()
    if args.cmd=="hook": return hook_main(args.harness,args.event)
    if args.cmd=="init":
        path=init_config(ws,args.force); (ws/".kessler").mkdir(exist_ok=True); (ws/".kessler"/".gitignore").write_text("cache/\n",encoding="utf-8")
        result={"config":str(path),"profile":get_profile(ws,refresh=True)}; emit(result,args.json); return 0
    if args.cmd=="profile": emit(get_profile(ws,args.refresh),args.json); return 0
    if args.cmd=="budget": emit(context_budget(),args.json); return 0
    if args.cmd=="explain":
        pol=get_policy(args.policy_id)
        if not pol: print(f"Unknown policy: {args.policy_id}"); return 2
        emit(pol,args.json); return 0
    if args.cmd in {"install","uninstall","rollback"}:
        surface=_surface(args.target,args)
        if args.cmd=="install":
            if args.target=="antigravity": result=install_antigravity(args.scope,ws,surface)
            elif args.target=="claude_code": result=install_claude_code(args.scope,ws,surface)
            else: result=install_gemini(args.scope,ws,surface)
        elif args.cmd=="uninstall":
            if args.target=="antigravity": result=uninstall_antigravity(args.scope,ws,surface,not args.no_restore)
            elif args.target=="claude_code": result=uninstall_claude_code(args.scope,ws,surface,not args.no_restore)
            else: result=uninstall_gemini(args.scope,ws,surface,not args.no_restore)
        else: result=rollback(args.target,args.scope,ws,surface)
        emit(result,args.json); return 0
    if args.cmd=="doctor":
        surface=_surface(args.target,args) if args.target!="package" else ""
        rows=package_checks(args.deep) if args.target=="package" else installed_checks(args.target,args.scope,ws,surface,args.deep)
        ok=all(r[0] for r in rows)
        if args.json: print(json.dumps({"ok":ok,"checks":[{"ok":r[0],"item":r[1],"detail":r[2]} for r in rows]},indent=2,ensure_ascii=False))
        else:
            for good,item,detail in rows: print(("PASS" if good else "FAIL")+f"  {item} — {detail}")
            print("\nOVERALL:","PASS" if ok else "FAIL")
        return 0 if ok else 1
    if args.cmd in {"report","waive"}:
        st=latest(str(ws))
        if not st: print("No Kessler session state found for this workspace."); return 1
        if args.cmd=="waive":
            sid=st.get("session_id","unknown")
            def fn(s): s["waiver"]={"reason":args.reason,"time":__import__('time').time()}
            update(sid,str(ws),fn); emit({"waived":True,"reason":args.reason},args.json); return 0
        profile=get_profile(ws); cfg=load_config(ws); summary=session_summary(st,profile,profile.get("risk",{}).get("strictness",cfg.get("strictness","balanced")))
        if args.json: emit(summary,True)
        else: print(to_markdown(summary),end="")
        return 0
    return 2

if __name__=="__main__": raise SystemExit(main())
