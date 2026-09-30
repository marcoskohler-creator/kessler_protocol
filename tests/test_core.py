from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kessler_protocol.config import init_config, load_config
from kessler_protocol.hook_runtime import run
from kessler_protocol.installers import install_antigravity, install_gemini, uninstall_antigravity, uninstall_gemini
from kessler_protocol.policies import get_policy
from kessler_protocol.profiler import get_profile
from kessler_protocol.state import key, load


class TempHome(unittest.TestCase):
    def setUp(self):
        self.home_tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.home_tmp.name)
        self.patch_home=mock.patch("pathlib.Path.home",return_value=self.home)
        self.patch_home.start()
    def tearDown(self):
        self.patch_home.stop(); self.home_tmp.cleanup()


class ProfileTests(TempHome):
    def test_auto_profile_and_risk(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"package.json").write_text(json.dumps({
                "scripts":{"test":"vitest","build":"next build","typecheck":"tsc --noEmit"},
                "dependencies":{"next":"1","@prisma/client":"1","next-auth":"1","stripe":"1"}
            }))
            (root/"src/auth").mkdir(parents=True); (root/"src/auth/login.ts").write_text("export {}")
            (root/"prisma/migrations").mkdir(parents=True)
            p=get_profile(root,refresh=True)
            self.assertIn("nextjs",p["frameworks"])
            self.assertTrue(p["features"]["authentication"])
            self.assertTrue(p["features"]["payments"])
            self.assertTrue(p["features"]["database"])
            self.assertTrue(p["features"]["migrations"])
            self.assertIn(p["risk"]["level"],{"HIGH","CRITICAL"})
            self.assertEqual(p["risk"]["strictness"],"strict" if p["risk"]["level"]=="HIGH" else "paranoid")
            self.assertTrue(any(v["kind"]=="test" for v in p["verification"]))

    def test_minimal_config(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=init_config(root)
            cfg=load_config(root)
            self.assertTrue(path.exists()); self.assertEqual(cfg["strictness"],"auto"); self.assertEqual(cfg["context"],"lean")


class HookTests(TempHome):
    def test_workspace_aliases_share_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            alias=root/"nested"/".."
            self.assertEqual(key("same-session",str(root)),key("same-session",str(alias)))

    def _project(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/"package.json").write_text(json.dumps({"scripts":{"test":"vitest","build":"next build"},"dependencies":{"next":"1"}}))
        (root/"src").mkdir(); return td,root

    def test_catastrophic_deny_antigravity(self):
        td,root=self._project()
        try:
            p={"conversationId":"a","workspacePaths":[str(root)],"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf /","Cwd":str(root)}}}
            self.assertEqual(run("antigravity","PreToolUse",p)["decision"],"deny")
        finally: td.cleanup()

    def test_destructive_git_requires_plan_antigravity_and_denies_gemini(self):
        td,root=self._project()
        try:
            ag={"conversationId":"a","workspacePaths":[str(root)],"toolCall":{"name":"run_command","args":{"CommandLine":"git reset --hard HEAD~1","Cwd":str(root)}}}
            gm={"session_id":"g","cwd":str(root),"tool_name":"run_shell_command","tool_input":{"command":"git reset --hard HEAD~1"}}
            self.assertEqual(run("antigravity","PreToolUse",ag)["decision"],"deny")
            self.assertEqual(run("gemini","BeforeTool",gm)["decision"],"deny")
        finally: td.cleanup()

    def test_failed_test_does_not_satisfy_verification(self):
        td,root=self._project()
        try:
            sid="verify-fail"
            write={"conversationId":sid,"workspacePaths":[str(root)],"toolCall":{"name":"write_to_file","args":{"TargetFile":str(root/"src/app.ts"),"CodeContent":"export const x=1"}},"error":""}
            run("antigravity","PostToolUse",write)
            bad={"conversationId":sid,"workspacePaths":[str(root)],"toolCall":{"name":"run_command","args":{"CommandLine":"npm run test","Cwd":str(root)}},"error":"exit status 1"}
            run("antigravity","PostToolUse",bad)
            stop={"conversationId":sid,"workspacePaths":[str(root)],"fullyIdle":True}
            self.assertEqual(run("antigravity","Stop",stop)["decision"],"continue")
            st=load(sid,str(root)); self.assertFalse(st["verifications"][-1]["success"])
        finally: td.cleanup()

    def test_successful_relevant_test_satisfies_verification(self):
        td,root=self._project()
        try:
            sid="verify-ok"
            write={"conversationId":sid,"workspacePaths":[str(root)],"toolCall":{"name":"write_to_file","args":{"TargetFile":str(root/"src/app.ts"),"CodeContent":"export const x=1"}},"error":""}
            run("antigravity","PostToolUse",write)
            good={"conversationId":sid,"workspacePaths":[str(root)],"toolCall":{"name":"run_command","args":{"CommandLine":"npm run test","Cwd":str(root)}},"error":""}
            run("antigravity","PostToolUse",good)
            stop={"conversationId":sid,"workspacePaths":[str(root)],"fullyIdle":True}
            self.assertNotEqual(run("antigravity","Stop",stop)["decision"],"continue")
            st=load(sid,str(root)); self.assertEqual(st["verifications"][-1]["relevance"],"high")
        finally: td.cleanup()

    def test_docs_only_write_does_not_trigger_gate(self):
        td,root=self._project()
        try:
            sid="docs"
            write={"conversationId":sid,"workspacePaths":[str(root)],"toolCall":{"name":"write_to_file","args":{"TargetFile":str(root/"README.md"),"CodeContent":"docs"}},"error":""}
            run("antigravity","PostToolUse",write)
            out=run("antigravity","Stop",{"conversationId":sid,"workspacePaths":[str(root)],"fullyIdle":True})
            self.assertNotEqual(out["decision"],"continue")
        finally: td.cleanup()

    def test_policy_explain(self):
        p=get_policy("KES-VER-001"); self.assertEqual(p["id"],"KES-VER-001"); self.assertIn("verification",p["summary"].lower())


class InstallerTests(TempHome):
    def test_antigravity_install_is_self_contained_and_restore_previous(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td); dst=self.home/".gemini/config/plugins/kessler-protocol"
            dst.mkdir(parents=True); (dst/"old.txt").write_text("old")
            m=install_antigravity("user",ws,"ide")
            self.assertTrue((dst/"scripts/entry.py").exists())
            self.assertTrue((dst/"scripts/vendor/kessler_protocol/hook_runtime.py").exists())
            hooks=json.loads((dst/"hooks.json").read_text())
            commands=[]
            for grp in hooks.values():
                for ev,cfgs in grp.items():
                    if isinstance(cfgs,list):
                        for cfg in cfgs:
                            for h in cfg.get("hooks",[]): commands.append(h.get("command",""))
            self.assertTrue(all(str(Path(os.sys.executable).resolve()) in c or os.sys.executable in c for c in commands))
            uninstall_antigravity("user",ws,"ide",True)
            self.assertEqual((dst/"old.txt").read_text(),"old")

    def test_gemini_preserves_unrelated_settings_and_restores_prior_kessler(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td); base=self.home/".gemini"; base.mkdir(parents=True)
            settings={"theme":"dark","hooks":{"BeforeTool":[
                {"matcher":"read_file","hooks":[{"name":"other-hook","type":"command","command":"echo ok"}]},
                {"matcher":"write_file","hooks":[{"name":"kessler-old","type":"command","command":"echo old"}]}
            ]}}
            (base/"settings.json").write_text(json.dumps(settings))
            install_gemini("user",ws,"cli")
            data=json.loads((base/"settings.json").read_text())
            self.assertEqual(data["theme"],"dark")
            names=[h.get("name") for groups in data["hooks"].values() for g in groups for h in g.get("hooks",[])]
            self.assertIn("other-hook",names); self.assertIn("kessler-before-tool",names); self.assertNotIn("kessler-old",names)
            uninstall_gemini("user",ws,"cli",True)
            data=json.loads((base/"settings.json").read_text())
            names=[h.get("name") for groups in data["hooks"].values() for g in groups for h in g.get("hooks",[])]
            self.assertIn("other-hook",names); self.assertIn("kessler-old",names); self.assertNotIn("kessler-before-tool",names)

if __name__=="__main__": unittest.main()
