from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
INSTALL_SCHEMA = 2


def _kessler_home() -> Path:
    p=Path.home()/".kessler"
    p.mkdir(parents=True,exist_ok=True)
    return p


def _key(target: str, scope: str, workspace: Path, surface: str = "") -> str:
    raw=f"{target}|{scope}|{surface}|{workspace.resolve()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _manifest_path(target: str, scope: str, workspace: Path, surface: str = "") -> Path:
    d=_kessler_home()/"installations"; d.mkdir(parents=True,exist_ok=True)
    return d/f"{_key(target,scope,workspace,surface)}.json"


def _write_json_atomic(path: Path, data: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)


def _load_json(path: Path) -> dict:
    if not path.exists(): return {}
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict): raise ValueError(f"Expected JSON object in {path}")
    return data


def _backup_path(install_id: str, name: str) -> Path:
    p=_kessler_home()/"backups"/install_id/name
    p.parent.mkdir(parents=True,exist_ok=True)
    return p


def _copy_backup(src: Path, dst: Path):
    if not src.exists(): return None
    if src.is_dir(): shutil.copytree(src,dst)
    else:
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    return str(dst)


def _restore_backup(backup: str | None, dst: Path):
    if dst.exists():
        if dst.is_dir(): shutil.rmtree(dst)
        else: dst.unlink()
    if not backup: return
    src=Path(backup)
    if not src.exists(): return
    if src.is_dir(): shutil.copytree(src,dst)
    else:
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)


def _command(parts: list[str]) -> str:
    if os.name == "nt": return subprocess.list2cmdline(parts)
    import shlex
    return shlex.join(parts)


def _vendor_runtime(runtime_dir: Path):
    src=PACKAGE_DIR
    dst=runtime_dir/"vendor"/"kessler_protocol"
    if dst.exists(): shutil.rmtree(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    entry=runtime_dir/"entry.py"
    from .templates import ENTRY_PY
    entry.write_text(ENTRY_PY,encoding="utf-8")
    return entry


def _rewrite_antigravity_hooks(plugin_dir: Path):
    entry=_vendor_runtime(plugin_dir/"scripts")
    hooks_path=plugin_dir/"hooks.json"
    data=_load_json(hooks_path)
    for group in data.values():
        if not isinstance(group,dict): continue
        for event, configs in group.items():
            if event == "enabled" or not isinstance(configs,list): continue
            for cfg in configs:
                handlers = cfg.get("hooks",[]) if isinstance(cfg,dict) else []
                for h in handlers:
                    if isinstance(h,dict) and (h.get("command","").startswith("__KESSLER_HOOK__") or "./scripts/entry.py" in h.get("command","")):
                        h["command"]=_command([sys.executable,str(entry),"--harness","antigravity","--event",event])
    _write_json_atomic(hooks_path,data)


def _antigravity_dst(scope: str, workspace: Path, surface: str) -> Path:
    if scope == "workspace": return workspace.resolve()/".agents"/"plugins"/"kessler-protocol"
    if surface == "cli": return Path.home()/".gemini"/"antigravity-cli"/"plugins"/"kessler-protocol"
    return Path.home()/".gemini"/"config"/"plugins"/"kessler-protocol"


def install_antigravity(scope: str, workspace: Path, surface: str = "ide") -> dict:
    dst=_antigravity_dst(scope,workspace,surface)
    install_id=f"ag-{int(time.time())}-{_key('antigravity',scope,workspace,surface)}"
    backup=None
    try:
        if dst.exists(): backup=_copy_backup(dst,_backup_path(install_id,"previous-plugin"))
        if dst.exists(): shutil.rmtree(dst)
        dst.parent.mkdir(parents=True,exist_ok=True)
        from .templates import write_antigravity_template
        write_antigravity_template(dst)
        _rewrite_antigravity_hooks(dst)
        manifest={"schema":INSTALL_SCHEMA,"id":install_id,"target":"antigravity","scope":scope,"surface":surface,"workspace":str(workspace.resolve()),"installed_path":str(dst),"previous_backup":backup,"created_at":time.time()}
        _write_json_atomic(_manifest_path("antigravity",scope,workspace,surface),manifest)
        return manifest
    except Exception:
        _restore_backup(backup,dst)
        raise


def _remove_named_hooks(settings: dict) -> dict:
    removed={}
    hooks=settings.get("hooks")
    if not isinstance(hooks,dict): return removed
    for event,groups in list(hooks.items()):
        if not isinstance(groups,list): continue
        keep=[]; rem=[]
        for group in groups:
            if not isinstance(group,dict): keep.append(group); continue
            handlers=group.get("hooks")
            if not isinstance(handlers,list): keep.append(group); continue
            filtered=[h for h in handlers if not (isinstance(h,dict) and str(h.get("name","")).startswith("kessler-"))]
            if len(filtered) != len(handlers):
                rem.append(group)
                if filtered:
                    clone=dict(group); clone["hooks"]=filtered; keep.append(clone)
            else: keep.append(group)
        hooks[event]=keep
        if rem: removed[event]=rem
    return removed


def _restore_removed_hooks(settings: dict, removed: dict):
    hooks=settings.setdefault("hooks",{})
    for event,groups in (removed or {}).items():
        hooks.setdefault(event,[]).extend(groups)


def _remove_command_hooks(settings: dict, marker: str) -> dict:
    # Claude Code hook entries have no documented "name" field, so Kessler-owned
    # entries are identified by the absolute path to its own vendored entry.py.
    removed={}
    hooks=settings.get("hooks")
    if not isinstance(hooks,dict): return removed
    for event,groups in list(hooks.items()):
        if not isinstance(groups,list): continue
        keep=[]; rem=[]
        for group in groups:
            if not isinstance(group,dict): keep.append(group); continue
            handlers=group.get("hooks")
            if not isinstance(handlers,list): keep.append(group); continue
            filtered=[h for h in handlers if not (isinstance(h,dict) and marker in str(h.get("command","")))]
            if len(filtered) != len(handlers):
                rem.append(group)
                if filtered:
                    clone=dict(group); clone["hooks"]=filtered; keep.append(clone)
            else: keep.append(group)
        hooks[event]=keep
        if rem: removed[event]=rem
    return removed


def install_gemini(scope: str, workspace: Path, surface: str = "cli") -> dict:
    base=(Path.home()/".gemini") if scope=="user" else (workspace.resolve()/".gemini")
    skill_dst=base/"skills"/"kessler-protocol"
    runtime_dir=base/"kessler"/"runtime"
    settings_path=base/"settings.json"
    install_id=f"gem-{int(time.time())}-{_key('gemini',scope,workspace,surface)}"
    skill_backup=runtime_backup=None
    original_settings_bytes=settings_path.read_bytes() if settings_path.exists() else None
    try:
        if skill_dst.exists(): skill_backup=_copy_backup(skill_dst,_backup_path(install_id,"previous-skill"))
        if runtime_dir.exists(): runtime_backup=_copy_backup(runtime_dir,_backup_path(install_id,"previous-runtime"))
        if skill_dst.exists(): shutil.rmtree(skill_dst)
        if runtime_dir.exists(): shutil.rmtree(runtime_dir)
        skill_dst.parent.mkdir(parents=True,exist_ok=True)
        from .templates import write_gemini_skill
        write_gemini_skill(skill_dst)
        entry=_vendor_runtime(runtime_dir)
        settings=_load_json(settings_path)
        previous_hooks=_remove_named_hooks(settings)
        hooks=settings.setdefault("hooks",{})
        cmd_base=[sys.executable,str(entry),"--harness","gemini"]
        definitions={
            "BeforeAgent":{"matcher":"*","sequential":True,"hooks":[{"name":"kessler-before-agent","type":"command","command":_command(cmd_base+["--event","BeforeAgent"]),"timeout":5000,"description":"Kessler planning context"}]},
            "BeforeTool":{"matcher":"write_file|replace|run_shell_command|read_file|.*search.*|.*write.*|.*edit.*|.*patch.*","sequential":True,"hooks":[{"name":"kessler-before-tool","type":"command","command":_command(cmd_base+["--event","BeforeTool"]),"timeout":5000,"description":"Kessler deterministic risk gate"}]},
            "AfterTool":{"matcher":"write_file|replace|run_shell_command|read_file|.*search.*|.*write.*|.*edit.*|.*patch.*","sequential":True,"hooks":[{"name":"kessler-after-tool","type":"command","command":_command(cmd_base+["--event","AfterTool"]),"timeout":5000,"description":"Kessler evidence and verification tracker"}]},
            "AfterAgent":{"matcher":"*","sequential":True,"hooks":[{"name":"kessler-after-agent","type":"command","command":_command(cmd_base+["--event","AfterAgent"]),"timeout":5000,"description":"Kessler completion evidence gate"}]},
        }
        for event,group in definitions.items(): hooks.setdefault(event,[]).append(group)
        _write_json_atomic(settings_path,settings)
        manifest={"schema":INSTALL_SCHEMA,"id":install_id,"target":"gemini","scope":scope,"surface":surface,"workspace":str(workspace.resolve()),"skill_path":str(skill_dst),"runtime_path":str(runtime_dir),"settings_path":str(settings_path),"previous_skill_backup":skill_backup,"previous_runtime_backup":runtime_backup,"previous_kessler_hooks":previous_hooks,"created_at":time.time()}
        _write_json_atomic(_manifest_path("gemini",scope,workspace,surface),manifest)
        return manifest
    except Exception:
        _restore_backup(skill_backup,skill_dst); _restore_backup(runtime_backup,runtime_dir)
        if original_settings_bytes is None: settings_path.unlink(missing_ok=True)
        else:
            settings_path.parent.mkdir(parents=True,exist_ok=True); settings_path.write_bytes(original_settings_bytes)
        raise


def install_claude_code(scope: str, workspace: Path, surface: str = "cli") -> dict:
    base=(Path.home()/".claude") if scope=="user" else (workspace.resolve()/".claude")
    skill_dst=base/"skills"/"kessler-protocol"
    runtime_dir=base/"kessler"/"runtime"
    settings_path=base/"settings.json"
    install_id=f"cc-{int(time.time())}-{_key('claude_code',scope,workspace,surface)}"
    skill_backup=runtime_backup=None
    original_settings_bytes=settings_path.read_bytes() if settings_path.exists() else None
    try:
        if skill_dst.exists(): skill_backup=_copy_backup(skill_dst,_backup_path(install_id,"previous-skill"))
        if runtime_dir.exists(): runtime_backup=_copy_backup(runtime_dir,_backup_path(install_id,"previous-runtime"))
        if skill_dst.exists(): shutil.rmtree(skill_dst)
        if runtime_dir.exists(): shutil.rmtree(runtime_dir)
        skill_dst.parent.mkdir(parents=True,exist_ok=True)
        from .templates import write_claude_code_skill
        write_claude_code_skill(skill_dst)
        entry=_vendor_runtime(runtime_dir)
        settings=_load_json(settings_path)
        marker=str(entry)
        previous_hooks=_remove_command_hooks(settings, marker)
        hooks=settings.setdefault("hooks",{})
        cmd_base=[sys.executable,str(entry),"--harness","claude_code"]
        definitions={
            "UserPromptSubmit":{"matcher":"*","hooks":[{"type":"command","command":_command(cmd_base+["--event","UserPromptSubmit"]),"timeout":10}]},
            "PreToolUse":{"matcher":"*","hooks":[{"type":"command","command":_command(cmd_base+["--event","PreToolUse"]),"timeout":10}]},
            "PostToolUse":{"matcher":"*","hooks":[{"type":"command","command":_command(cmd_base+["--event","PostToolUse"]),"timeout":10}]},
            "Stop":{"matcher":"*","hooks":[{"type":"command","command":_command(cmd_base+["--event","Stop"]),"timeout":10}]},
        }
        for event,group in definitions.items(): hooks.setdefault(event,[]).append(group)
        _write_json_atomic(settings_path,settings)
        manifest={"schema":INSTALL_SCHEMA,"id":install_id,"target":"claude_code","scope":scope,"surface":surface,"workspace":str(workspace.resolve()),"skill_path":str(skill_dst),"runtime_path":str(runtime_dir),"settings_path":str(settings_path),"previous_skill_backup":skill_backup,"previous_runtime_backup":runtime_backup,"previous_kessler_hooks":previous_hooks,"created_at":time.time()}
        _write_json_atomic(_manifest_path("claude_code",scope,workspace,surface),manifest)
        return manifest
    except Exception:
        _restore_backup(skill_backup,skill_dst); _restore_backup(runtime_backup,runtime_dir)
        if original_settings_bytes is None: settings_path.unlink(missing_ok=True)
        else:
            settings_path.parent.mkdir(parents=True,exist_ok=True); settings_path.write_bytes(original_settings_bytes)
        raise


def uninstall_antigravity(scope: str, workspace: Path, surface: str = "ide", restore_previous: bool = True) -> dict:
    mp=_manifest_path("antigravity",scope,workspace,surface)
    m=_load_json(mp)
    dst=Path(m.get("installed_path") or _antigravity_dst(scope,workspace,surface))
    if dst.exists(): shutil.rmtree(dst)
    restored=False
    if restore_previous and m.get("previous_backup"):
        _restore_backup(m["previous_backup"],dst); restored=dst.exists()
    mp.unlink(missing_ok=True)
    return {"target":"antigravity","removed":str(dst),"restored_previous":restored}


def uninstall_gemini(scope: str, workspace: Path, surface: str = "cli", restore_previous: bool = True) -> dict:
    mp=_manifest_path("gemini",scope,workspace,surface)
    m=_load_json(mp)
    base=(Path.home()/".gemini") if scope=="user" else (workspace.resolve()/".gemini")
    skill=Path(m.get("skill_path") or base/"skills/kessler-protocol")
    runtime=Path(m.get("runtime_path") or base/"kessler/runtime")
    settings_path=Path(m.get("settings_path") or base/"settings.json")
    if skill.exists(): shutil.rmtree(skill)
    if runtime.exists(): shutil.rmtree(runtime)
    if restore_previous:
        _restore_backup(m.get("previous_skill_backup"),skill)
        _restore_backup(m.get("previous_runtime_backup"),runtime)
    if settings_path.exists():
        settings=_load_json(settings_path); _remove_named_hooks(settings)
        if restore_previous: _restore_removed_hooks(settings,m.get("previous_kessler_hooks",{}))
        _write_json_atomic(settings_path,settings)
    mp.unlink(missing_ok=True)
    return {"target":"gemini","removed_skill":str(skill),"removed_runtime":str(runtime),"settings":str(settings_path),"restored_previous":restore_previous}


def uninstall_claude_code(scope: str, workspace: Path, surface: str = "cli", restore_previous: bool = True) -> dict:
    mp=_manifest_path("claude_code",scope,workspace,surface)
    m=_load_json(mp)
    base=(Path.home()/".claude") if scope=="user" else (workspace.resolve()/".claude")
    skill=Path(m.get("skill_path") or base/"skills/kessler-protocol")
    runtime=Path(m.get("runtime_path") or base/"kessler/runtime")
    settings_path=Path(m.get("settings_path") or base/"settings.json")
    marker=str(runtime/"entry.py")
    if skill.exists(): shutil.rmtree(skill)
    if runtime.exists(): shutil.rmtree(runtime)
    if restore_previous:
        _restore_backup(m.get("previous_skill_backup"),skill)
        _restore_backup(m.get("previous_runtime_backup"),runtime)
    if settings_path.exists():
        settings=_load_json(settings_path); _remove_command_hooks(settings,marker)
        if restore_previous: _restore_removed_hooks(settings,m.get("previous_kessler_hooks",{}))
        _write_json_atomic(settings_path,settings)
    mp.unlink(missing_ok=True)
    return {"target":"claude_code","removed_skill":str(skill),"removed_runtime":str(runtime),"settings":str(settings_path),"restored_previous":restore_previous}


def rollback(target: str, scope: str, workspace: Path, surface: str) -> dict:
    if target=="antigravity": return uninstall_antigravity(scope,workspace,surface,True)
    if target=="claude_code": return uninstall_claude_code(scope,workspace,surface,True)
    return uninstall_gemini(scope,workspace,surface,True)


def get_manifest(target: str, scope: str, workspace: Path, surface: str) -> dict:
    return _load_json(_manifest_path(target,scope,workspace,surface))
