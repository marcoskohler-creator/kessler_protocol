from __future__ import annotations

import unittest

from kessler_protocol.verification import classify_command, requirements


class VerificationClassifyTests(unittest.TestCase):
    def test_pytest_invocations_classify_as_test(self):
        self.assertEqual(classify_command("pytest"), "test")
        self.assertEqual(classify_command("python -m pytest"), "test")
        self.assertEqual(classify_command("python3 -m pytest -x"), "test")

    def test_unittest_invocations_classify_as_test(self):
        # Kessler's own repository documents this exact command
        # (README.md "Development" section, CONTRIBUTING.md) as its test runner.
        # A project using unittest instead of pytest must still satisfy KES-VER-001.
        self.assertEqual(classify_command("python -m unittest discover -s tests -v"), "test")
        self.assertEqual(classify_command("python3 -m unittest"), "test")

    def test_unrelated_command_is_not_classified(self):
        self.assertIsNone(classify_command("git status --short"))

    def test_accessibility_tooling_commands_classify_as_design(self):
        self.assertEqual(classify_command("npx axe https://localhost:3000"), "design")
        self.assertEqual(classify_command("npx @axe-core/cli https://localhost:3000"), "design")
        self.assertEqual(classify_command("npx pa11y http://localhost:3000"), "design")
        self.assertEqual(classify_command("npx lhci autorun"), "design")
        self.assertEqual(classify_command("npx lighthouse https://localhost:3000"), "design")
        self.assertEqual(classify_command("npm run test:a11y"), "design")
        self.assertEqual(classify_command("npm run a11y"), "design")
        self.assertEqual(classify_command("npm run lint:a11y"), "design")
        self.assertEqual(classify_command("yarn accessibility"), "design")


class VerificationRequirementsUiDesignTests(unittest.TestCase):
    def test_design_required_when_ui_and_project_has_design_tooling(self):
        profile = {"verification": [{"kind": "design", "command": "npm run test:a11y"}]}
        req = requirements(profile, changed_paths=["src/audit.tsx"], strictness="balanced", sensitive=False, ui=True)
        self.assertIn("design", req)

    def test_design_not_required_when_project_has_no_design_tooling(self):
        # The design floor is dependent on the project actually having a11y
        # tooling installed — same floor-dependent pattern as test/build/lint.
        profile = {"verification": [{"kind": "test", "command": "pytest"}]}
        req = requirements(profile, changed_paths=["src/audit.tsx"], strictness="balanced", sensitive=False, ui=True)
        self.assertNotIn("design", req)

    def test_design_not_required_when_not_ui_even_if_tooling_available(self):
        profile = {"verification": [{"kind": "design", "command": "npm run test:a11y"}]}
        req = requirements(profile, changed_paths=["src/audit.tsx"], strictness="balanced", sensitive=False, ui=False)
        self.assertNotIn("design", req)

    def test_design_required_for_ui_regardless_of_strictness(self):
        # Marcos's explicit choice: the design floor applies to every UI plan,
        # unconditionally — not risk-gated like the secondary test/build checks.
        profile = {"verification": [{"kind": "design", "command": "npm run test:a11y"}]}
        for strictness in ("balanced", "strict", "paranoid"):
            req = requirements(profile, changed_paths=["src/audit.tsx"], strictness=strictness, sensitive=False, ui=True)
            self.assertIn("design", req, f"expected design in requirements at strictness={strictness}")


if __name__ == "__main__":
    unittest.main()
