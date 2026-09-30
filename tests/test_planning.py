from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kessler_protocol.hook_runtime import run
from kessler_protocol.planning import PLAN_RELATIVE_PATH, validate_plan
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


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.home_tmp = tempfile.TemporaryDirectory()
        self.workspace_tmp = tempfile.TemporaryDirectory()
        self.home_patch = mock.patch("pathlib.Path.home", return_value=Path(self.home_tmp.name))
        self.home_patch.start()
        self.root = Path(self.workspace_tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src/audit.tsx").write_text("export default function Audit() {}", encoding="utf-8")
        self.plan_file = self.root / PLAN_RELATIVE_PATH
        self.session = "planning-test"

    def tearDown(self):
        self.home_patch.stop()
        self.workspace_tmp.cleanup()
        self.home_tmp.cleanup()

    def antigravity(self, tool: str, args: dict) -> dict:
        return {"conversationId": self.session, "workspacePaths": [str(self.root)],
                "toolCall": {"name": tool, "args": args}}

    def gemini(self, tool: str, args: dict) -> dict:
        return {"session_id": self.session, "cwd": str(self.root),
                "tool_name": tool, "tool_input": args}

    def _record_read(self, relative_path: str):
        # KES-READ-001 requires real read evidence before a plan can cite a
        # path in discovery[], so every register() call simulates the model
        # actually opening the file first.
        payload = self.antigravity("view_file", {"AbsolutePath": str(self.root / relative_path)})
        run("antigravity", "PreToolUse", payload)
        run("antigravity", "PostToolUse", payload)

    def register(self, plan: dict | None = None):
        self._record_read("src/audit.tsx")
        self.plan_file.parent.mkdir(parents=True, exist_ok=True)
        self.plan_file.write_text(json.dumps(plan or ui_plan()), encoding="utf-8")
        payload = self.antigravity("write_to_file", {"TargetFile": str(self.plan_file),
                                                       "CodeContent": self.plan_file.read_text()})
        self.assertEqual(run("antigravity", "PreToolUse", payload)["decision"], "allow")
        run("antigravity", "PostToolUse", payload)

    def test_requires_registered_plan_before_direct_write_in_both_harnesses(self):
        ag = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/audit.tsx"), "CodeContent": "new"})
        gm = self.gemini("write_file", {"file_path": str(self.root / "src/audit.tsx"), "content": "new"})
        self.assertEqual(run("antigravity", "PreToolUse", ag)["decision"], "deny")
        self.assertEqual(run("gemini", "BeforeTool", gm)["decision"], "deny")
        self.assertEqual(run("gemini", "BeforeAgent", self.gemini("", {}))["hookSpecificOutput"].keys(), {"additionalContext"})

    def test_plan_allows_only_named_files_and_must_be_re_registered_after_revision(self):
        self.register()
        planned = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/audit.tsx"), "CodeContent": "new"})
        unplanned = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/other.tsx"), "CodeContent": "new"})
        self.assertEqual(run("antigravity", "PreToolUse", planned)["decision"], "allow")
        self.assertEqual(run("antigravity", "PreToolUse", unplanned)["decision"], "deny")
        self.assertIn("KES-PLAN-002", run("antigravity", "PreToolUse", unplanned)["reason"])
        revision = ui_plan()
        revision["implementation"].append({"path": "src/other.tsx", "placement": "New helper module beside audit page",
                                           "method": "Implement the export request handler", "responsibility": "Connect the export control"})
        self.plan_file.write_text(json.dumps(revision), encoding="utf-8")
        self.assertEqual(run("antigravity", "PreToolUse", planned)["decision"], "deny")
        self.register(revision)
        self.assertEqual(run("antigravity", "PreToolUse", unplanned)["decision"], "allow")

    def test_invalid_plan_cannot_be_registered(self):
        plan = ui_plan()
        plan["interface"]["controls"] = []
        self.register(plan)
        self.assertNotIn("plan", load(self.session, str(self.root)))
        write = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/audit.tsx")})
        self.assertEqual(run("antigravity", "PreToolUse", write)["decision"], "deny")
        self.assertIn("interface.controls", run("antigravity", "PreToolUse", write)["reason"])

    def test_discovery_must_exist_and_paths_stay_inside_workspace(self):
        plan = ui_plan()
        plan["discovery"][0]["path"] = "missing.tsx"
        plan["implementation"][0]["path"] = "../escape.tsx"
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("does not exist" in error for error in errors))
        self.assertTrue(any("inside the workspace" in error for error in errors))

    def test_discovery_without_read_evidence_is_denied(self):
        # Register the plan WITHOUT the usual _record_read() step: the file
        # exists (so must_exist passes) but nothing in state["reads"] proves
        # it was actually opened.
        self.plan_file.parent.mkdir(parents=True, exist_ok=True)
        self.plan_file.write_text(json.dumps(ui_plan()), encoding="utf-8")
        payload = self.antigravity("write_to_file", {"TargetFile": str(self.plan_file), "CodeContent": self.plan_file.read_text()})
        run("antigravity", "PreToolUse", payload)
        run("antigravity", "PostToolUse", payload)
        write = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/audit.tsx"), "CodeContent": "new"})
        blocked = run("antigravity", "PreToolUse", write)
        self.assertEqual(blocked["decision"], "deny")
        self.assertIn("KES-READ-001", blocked["reason"])
        self._record_read("src/audit.tsx")
        self.assertEqual(run("antigravity", "PreToolUse", write)["decision"], "allow")

    def test_all_shell_commands_require_plan_but_file_reads_are_allowed(self):
        read = self.antigravity("view_file", {"AbsolutePath": str(self.root / "src/audit.tsx")})
        status = self.antigravity("run_command", {"CommandLine": "git status --short", "Cwd": str(self.root)})
        write = self.antigravity("run_command", {"CommandLine": "sed -i s/old/new/ src/audit.tsx", "Cwd": str(self.root)})
        opaque = self.antigravity("run_command", {"CommandLine": "python3 -c 'open(\"src/audit.tsx\",\"w\").write(\"x\")'", "Cwd": str(self.root)})
        chained = self.antigravity("run_command", {"CommandLine": "git status; touch src/other.tsx", "Cwd": str(self.root)})
        self.assertEqual(run("antigravity", "PreToolUse", read)["decision"], "allow")
        self.assertEqual(run("antigravity", "PreToolUse", status)["decision"], "deny")
        self.assertEqual(run("antigravity", "PreToolUse", write)["decision"], "deny")
        self.assertEqual(run("antigravity", "PreToolUse", opaque)["decision"], "deny")
        self.assertEqual(run("antigravity", "PreToolUse", chained)["decision"], "deny")
        self.register()
        self.assertEqual(run("antigravity", "PreToolUse", write)["decision"], "allow")

    def test_risk_confirmation_still_applies_after_plan_registration(self):
        self.register()
        destructive = self.antigravity("run_command", {"CommandLine": "git reset --hard HEAD~1", "Cwd": str(self.root)})
        self.assertEqual(run("antigravity", "PreToolUse", destructive)["decision"], "force_ask")

    def test_plan_registration_expires_after_completed_turn(self):
        self.register()
        stop = {"conversationId": self.session, "workspacePaths": [str(self.root)], "fullyIdle": True}
        self.assertEqual(run("antigravity", "Stop", stop)["decision"], "allow")
        self.assertNotIn("plan", load(self.session, str(self.root)))
        planned = self.antigravity("write_to_file", {"TargetFile": str(self.root / "src/audit.tsx")})
        self.assertEqual(run("antigravity", "PreToolUse", planned)["decision"], "deny")

    def test_design_standards_is_required_on_every_ui_plan(self):
        plan = ui_plan()
        del plan["interface"]["design_standards"]
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("design_standards must be an object" in error for error in errors))

    def test_design_standards_rejects_below_minimum_values(self):
        plan = ui_plan()
        plan["interface"]["design_standards"] = {
            "touch_target_pt": 40,  # below the 44pt Apple HIG / Material minimum
            "contrast_ratio": 3.0,  # below WCAG 2.2 AA's 4.5 for normal text
            "supports_dynamic_type": False,
            "respects_reduced_motion": False,
            "responsive_breakpoints": ["mobile"],  # only one, needs 2+
        }
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("touch_target_pt must be a number >= 44" in error for error in errors))
        self.assertTrue(any("contrast_ratio must be a number >= 4.5" in error for error in errors))
        self.assertTrue(any("supports_dynamic_type must be true" in error for error in errors))
        self.assertTrue(any("respects_reduced_motion must be true" in error for error in errors))
        self.assertTrue(any("responsive_breakpoints must list at least 2" in error for error in errors))

    def test_design_standards_rejects_placeholder_breakpoints(self):
        plan = ui_plan()
        plan["interface"]["design_standards"]["responsive_breakpoints"] = ["a", "b"]  # each under the 3-char floor
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("responsive_breakpoints[0]" in error for error in errors))
        self.assertTrue(any("responsive_breakpoints[1]" in error for error in errors))

    def test_valid_design_standards_plan_registers_and_captures_ui_interface_mode(self):
        self.register()
        state = load(self.session, str(self.root))
        self.assertEqual(state["plan"]["interface_mode"], "ui")

    def test_non_ui_plan_has_no_design_standards_requirement(self):
        plan = ui_plan()
        # Swap the implementation target to a non-UI-surface file so this test
        # stays focused on design_standards alone — a .tsx path here would
        # also trip the separate anti-gaming check below.
        plan["implementation"] = [{"path": "scripts/generate_report.py", "placement": "New batch script",
                                    "method": "Query audit rows and write report.json",
                                    "responsibility": "Produce the batch report"}]
        plan["interface"] = {
            "mode": "non_ui", "entry_point": "CLI command invocation",
            "reason": "Batch job with no user-facing screen",
            "result": "Writes a summary report to disk",
            "data_contract": "Reads audit rows, writes report.json with the same shape as the API response",
            "failure_behavior": "Exits non-zero and leaves any partial report file untouched",
            "side_effects": [],
        }
        errors, _, _ = validate_plan(plan, self.root)
        self.assertFalse(any("design_standards" in error for error in errors))

    def test_non_ui_plan_rejects_ui_surface_files_without_override(self):
        # implementation still points at src/audit.tsx (from the base ui_plan()
        # fixture) — a UI-surface file — while mode is declared non_ui.
        plan = ui_plan()
        plan["interface"] = {
            "mode": "non_ui", "entry_point": "CLI command invocation",
            "reason": "Batch job with no user-facing screen",
            "result": "Writes a summary report to disk",
            "data_contract": "Reads audit rows, writes report.json with the same shape as the API response",
            "failure_behavior": "Exits non-zero and leaves any partial report file untouched",
            "side_effects": [],
        }
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("UI-surface file" in error for error in errors))

    def test_non_ui_plan_accepts_ui_surface_files_with_valid_override_reason(self):
        plan = ui_plan()
        plan["implementation"] = [{"path": "src/audit.css", "placement": "New stylesheet",
                                    "method": "Regenerate the compiled stylesheet from design tokens",
                                    "responsibility": "Produce the static, server-bundled CSS file"}]
        plan["interface"] = {
            "mode": "non_ui", "entry_point": "Build step invocation",
            "reason": "Regenerates a static CSS bundle with no runtime interaction",
            "result": "Writes a compiled stylesheet to disk",
            "data_contract": "Reads design tokens, writes a static .css file",
            "failure_behavior": "Exits non-zero and leaves the previous stylesheet untouched",
            "side_effects": [],
            "non_ui_override_reason": "Generated stylesheet has no interactive controls or screens of its own",
        }
        errors, _, _ = validate_plan(plan, self.root)
        self.assertFalse(any("UI-surface file" in error for error in errors))

    def test_non_ui_plan_rejects_placeholder_override_reason(self):
        plan = ui_plan()
        plan["interface"] = {
            "mode": "non_ui", "entry_point": "CLI command invocation",
            "reason": "Batch job with no user-facing screen",
            "result": "Writes a summary report to disk",
            "data_contract": "Reads audit rows, writes report.json with the same shape as the API response",
            "failure_behavior": "Exits non-zero and leaves any partial report file untouched",
            "side_effects": [],
            "non_ui_override_reason": "tbd",
        }
        errors, _, _ = validate_plan(plan, self.root)
        self.assertTrue(any("UI-surface file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
