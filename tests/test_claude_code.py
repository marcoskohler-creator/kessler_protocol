from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kessler_protocol.hook_runtime import run
from kessler_protocol.installers import install_claude_code, uninstall_claude_code
from kessler_protocol.planning import PLAN_RELATIVE_PATH
from kessler_protocol.state import load


def ui_plan() -> dict:
    return {
        "goal": "Add an export action to the audit detail page",
        "purpose": "Let reviewers save a completed audit for offline use",
        "justification": {
            "why": "Reviewers currently screenshot the page to share audits, which loses formatting and data",
            "future_risks": [
                "Ad-hoc screenshot sharing could leak fields a real export would redact as the schema grows",
                "Bolting on export later without a stable endpoint would force every consumer to migrate again",
            ],
        },
        "users": ["Reviewers with access to completed audits"],
        "usage_flow": ["Open an audit from the list", "Click Export report on the detail page"],
        "discovery": [{"path": "src/audit.tsx", "finding": "The audit page already has an action bar"}],
        "delivery": "A PDF download triggered from the browser via the existing export endpoint",
        "rollback": "Revert the audit.tsx change; no server-side or data changes are involved",
        "interface": {
            "mode": "ui", "entry_point": "Audit list row opens the detail page",
            "final_screen": "Audit detail page shows Export report in the action bar",
            "accessibility": "Export button is keyboard-reachable and has an accessible label",
            "states": ["Default: Export report button visible in the action bar",
                       "Loading: button shows a spinner while the PDF generates",
                       "Error: inline message shown if the export request fails"],
            "controls": [{"label": "Export report", "location": "Beside Share in the top action bar",
                          "action": "Request a PDF for the current audit", "destination": "Browser downloads the resulting PDF",
                          "failure": "Show an error message and keep the audit page open",
                          "handler_path": "src/audit.tsx", "evidence_path": "src/audit.tsx"}],
            "navigation": [{"from": "Audit list", "via": "Completed audit row", "to": "Audit detail page",
                            "evidence": "Existing list link and detail route were inspected", "evidence_path": "src/audit.tsx"}],
            "design_standards": {"touch_target_pt": 44, "contrast_ratio": 4.5, "supports_dynamic_type": True,
                                  "respects_reduced_motion": True, "responsive_breakpoints": ["mobile", "desktop"]},
        },
        "implementation": [{"path": "src/audit.tsx", "placement": "Action bar beside Share",
                            "method": "Call the existing export endpoint and show errors",
                            "responsibility": "Expose the export action to reviewers"}],
        "validation": [{"description": "Open the audit and click Export report, then inspect the downloaded PDF",
                         "command": "npm run test -- audit.export"}],
    }


def _record_read(root: Path, sid: str, relative_path: str):
    # KES-READ-001 requires real read evidence before a plan can cite a path
    # in discovery[]; the real Claude Code tool name for a file read is the
    # bare "Read" (not "ReadFile"), which evidence.py's READ_RX now matches.
    payload = {"session_id": sid, "cwd": str(root), "tool_name": "Read", "tool_input": {"file_path": str(root / relative_path)}}
    run("claude_code", "PreToolUse", payload)
    run("claude_code", "PostToolUse", payload)


class TempHome(unittest.TestCase):
    def setUp(self):
        self.home_tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.home_tmp.name)
        self.patch_home = mock.patch("pathlib.Path.home", return_value=self.home)
        self.patch_home.start()

    def tearDown(self):
        self.patch_home.stop()
        self.home_tmp.cleanup()


class ClaudeCodeHookContractTests(TempHome):
    def _project(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "package.json").write_text(json.dumps({"scripts": {"test": "vitest", "build": "next build"}, "dependencies": {"next": "1"}}))
        (root / "src").mkdir()
        return td, root

    def test_catastrophic_command_is_denied_via_permission_decision(self):
        td, root = self._project()
        try:
            payload = {"session_id": "cc-1", "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
            out = run("claude_code", "PreToolUse", payload)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        finally:
            td.cleanup()

    def test_destructive_git_maps_to_ask_once_a_plan_is_registered(self):
        # Planning Gate takes priority over risk confirmation until a plan is
        # registered (mirrors test_planning.PlanningTests.
        # test_risk_confirmation_still_applies_after_plan_registration), so the
        # plan must be registered first to isolate the risk-engine mapping.
        td, root = self._project()
        try:
            (root / "src/audit.tsx").write_text("export default function Audit() {}", encoding="utf-8")
            sid = "cc-risk"
            _record_read(root, sid, "src/audit.tsx")
            plan_file = root / PLAN_RELATIVE_PATH
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(ui_plan()), encoding="utf-8")
            register = {"session_id": sid, "cwd": str(root), "tool_name": "Write",
                        "tool_input": {"file_path": str(plan_file), "content": plan_file.read_text()}}
            run("claude_code", "PreToolUse", register)
            run("claude_code", "PostToolUse", register)
            destructive = {"session_id": sid, "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~1"}}
            out = run("claude_code", "PreToolUse", destructive)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        finally:
            td.cleanup()

    def test_before_agent_injects_additional_context(self):
        out = run("claude_code", "UserPromptSubmit", {"session_id": "cc-3", "cwd": "."})
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("Kessler is active", out["hookSpecificOutput"]["additionalContext"])

    def test_verification_gate_blocks_stop_until_relevant_test_passes(self):
        td, root = self._project()
        try:
            sid = "cc-verify"
            write = {"session_id": sid, "cwd": str(root), "tool_name": "Write",
                     "tool_input": {"file_path": str(root / "src/app.ts"), "content": "export const x=1"}}
            run("claude_code", "PostToolUse", write)
            failing = {"session_id": sid, "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": "npm run test"},
                       "tool_output": {"is_error": True, "error": "exit status 1"}}
            run("claude_code", "PostToolUse", failing)
            stop = run("claude_code", "Stop", {"session_id": sid, "cwd": str(root)})
            self.assertEqual(stop["hookSpecificOutput"]["decision"], "block")
            st = load(sid, str(root))
            self.assertFalse(st["verifications"][-1]["success"])

            passing = {"session_id": sid, "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": "npm run test"},
                       "tool_output": {"is_error": False}}
            run("claude_code", "PostToolUse", passing)
            stop2 = run("claude_code", "Stop", {"session_id": sid, "cwd": str(root)})
            self.assertNotIn("decision", stop2.get("hookSpecificOutput", {}))
        finally:
            td.cleanup()

    def test_planning_gate_denies_direct_write_without_registered_plan(self):
        td, root = self._project()
        try:
            payload = {"session_id": "cc-plan", "cwd": str(root), "tool_name": "Write",
                       "tool_input": {"file_path": str(root / "src/app.ts"), "content": "new"}}
            out = run("claude_code", "PreToolUse", payload)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("KES-PLAN-001", out["hookSpecificOutput"]["permissionDecisionReason"])
        finally:
            td.cleanup()

    def test_planning_gate_allows_write_once_plan_is_registered(self):
        td, root = self._project()
        try:
            (root / "src/audit.tsx").write_text("export default function Audit() {}", encoding="utf-8")
            sid = "cc-plan-ok"
            _record_read(root, sid, "src/audit.tsx")
            plan_file = root / PLAN_RELATIVE_PATH
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(ui_plan()), encoding="utf-8")
            register = {"session_id": sid, "cwd": str(root), "tool_name": "Write",
                        "tool_input": {"file_path": str(plan_file), "content": plan_file.read_text()}}
            self.assertEqual(run("claude_code", "PreToolUse", register)["hookSpecificOutput"]["permissionDecision"], "allow")
            run("claude_code", "PostToolUse", register)
            planned = {"session_id": sid, "cwd": str(root), "tool_name": "Write",
                       "tool_input": {"file_path": str(root / "src/audit.tsx"), "content": "new"}}
            self.assertEqual(run("claude_code", "PreToolUse", planned)["hookSpecificOutput"]["permissionDecision"], "allow")
        finally:
            td.cleanup()


class ClaudeCodeInstallerTests(TempHome):
    def test_install_preserves_unrelated_settings_and_uninstall_restores_prior_kessler(self):
        # Claude Code hook entries carry no documented "name" field (unlike
        # Gemini's), so Kessler identifies its own entries by the absolute
        # path to its vendored entry.py, which is deterministic per
        # scope/workspace. A pre-existing hook whose command contains that
        # same future path (tagged --legacy-marker here so it's
        # distinguishable from the freshly-installed one) simulates a prior
        # Kessler installation that install_claude_code must replace and be
        # able to restore on uninstall.
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            base = self.home / ".claude"
            base.mkdir(parents=True)
            future_entry = base / "kessler" / "runtime" / "entry.py"
            settings = {"theme": "dark", "hooks": {"PreToolUse": [
                {"matcher": "*", "hooks": [{"type": "command", "command": "echo other-hook"}]},
                {"matcher": "*", "hooks": [{"type": "command", "command": f"python {future_entry} --harness claude_code --event PreToolUse --legacy-marker"}]},
            ]}}
            (base / "settings.json").write_text(json.dumps(settings))

            install_claude_code("user", ws, "cli")
            self.assertTrue((base / "skills/kessler-protocol/SKILL.md").exists())
            self.assertTrue(future_entry.exists())
            data = json.loads((base / "settings.json").read_text())
            self.assertEqual(data["theme"], "dark")
            commands = [h.get("command", "") for groups in data["hooks"].values() for g in groups for h in g.get("hooks", [])]
            self.assertTrue(any("echo other-hook" in c for c in commands))
            self.assertTrue(any(str(future_entry) in c and "--legacy-marker" not in c for c in commands))
            self.assertFalse(any("--legacy-marker" in c for c in commands))
            for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"):
                self.assertIn(event, data["hooks"])

            uninstall_claude_code("user", ws, "cli", True)
            self.assertFalse((base / "skills/kessler-protocol").exists())
            self.assertFalse((base / "kessler/runtime").exists())
            data = json.loads((base / "settings.json").read_text())
            self.assertEqual(data["theme"], "dark")
            commands = [h.get("command", "") for groups in data["hooks"].values() for g in groups for h in g.get("hooks", [])]
            self.assertTrue(any("echo other-hook" in c for c in commands))
            self.assertTrue(any("--legacy-marker" in c for c in commands))
            self.assertFalse(any(str(future_entry) in c and "--legacy-marker" not in c for c in commands))


if __name__ == "__main__":
    unittest.main()
