from __future__ import annotations

import re
from pathlib import Path

GENERIC = [
    # Real accessibility/design-QA tooling, not a taste judgment on the plan's
    # declared design_standards — this is what KES-VER-001 requires to actually
    # pass for UI work, when the project has one of these installed. Listed
    # before the generic npm-script patterns below: an "npm run test:a11y" or
    # "npm run lint:a11y" script name is an accessibility check first, and
    # classify_command() returns on the first matching entry — the generic
    # "test:[\\w:-]+" pattern would otherwise shadow "test:a11y" and misclassify
    # it as a plain test run (caught by tests/test_verification.py).
    ("design", re.compile(r"(^|\s)(?:npx\s+)?(?:@axe-core/cli|axe)\b", re.I)),
    ("design", re.compile(r"(^|\s)(npx\s+)?pa11y\b", re.I)),
    ("design", re.compile(r"(^|\s)(npx\s+)?lhci\b", re.I)),
    ("design", re.compile(r"(^|\s)(npx\s+)?lighthouse\b", re.I)),
    ("design", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?(?:test:a11y|a11y|lint:a11y|accessibility)(\s|$)", re.I)),
    ("test", re.compile(r"(^|\s)(pytest|python3?\s+-m\s+pytest|python3?\s+-m\s+unittest|go\s+test|cargo\s+test|mvn(?:w)?\b.*\btest|gradle(?:w)?\b.*\btest)(\s|$)", re.I)),
    ("test", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?(?:test|test:[\w:-]+)(\s|$)", re.I)),
    ("build", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?build(\s|$)", re.I)),
    ("build", re.compile(r"(^|\s)(cargo\s+build|mvn(?:w)?\b.*\bpackage|gradle(?:w)?\b.*\bbuild)(\s|$)", re.I)),
    ("lint", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?lint(\s|$)", re.I)),
    ("lint", re.compile(r"(^|\s)(ruff\s+check|eslint\b|cargo\s+clippy)(\s|$)", re.I)),
    ("typecheck", re.compile(r"(^|\s)(tsc\b|mypy\b|pyright\b)(\s|$)", re.I)),
    ("typecheck", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?(?:typecheck|type-check|check:types)(\s|$)", re.I)),
    ("check", re.compile(r"(^|\s)(cargo\s+check|go\s+vet)(\s|$)", re.I)),
    ("check", re.compile(r"(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?check(\s|$)", re.I)),
]
FAIL_PATTERNS = [
    re.compile(r"\bexit(?:ed)?(?: with)? (?:code|status)\s*[:=]?\s*([1-9]\d*)\b", re.I),
    re.compile(r"\bprocess (?:failed|exited).*?\b([1-9]\d*)\b", re.I),
    re.compile(r"\bcommand failed\b", re.I),
    re.compile(r"\btests? failed\b", re.I),
]


def classify_command(command: str) -> str | None:
    for kind, rx in GENERIC:
        if rx.search(command or ""):
            return kind
    return None


def command_success(error: str | None, response_text: str = "") -> bool:
    if error and str(error).strip():
        return False
    text = response_text or ""
    return not any(rx.search(text) for rx in FAIL_PATTERNS)


def relevance(command: str, kind: str | None, profile: dict) -> str:
    if not kind:
        return "none"
    normalized = " ".join((command or "").strip().split()).lower()
    for item in profile.get("verification", []):
        expected = " ".join(str(item.get("command", "")).split()).lower()
        if expected and (normalized == expected or expected in normalized or normalized in expected):
            return "high"
    detected_kinds = {x.get("kind") for x in profile.get("verification", [])}
    if kind in detected_kinds:
        return "medium"
    if kind in {"test", "build", "typecheck", "lint", "check", "design"}:
        return "low"
    return "none"


def requirements(profile: dict, changed_paths: list[str], strictness: str, sensitive: bool, ui: bool = False) -> list[str]:
    available = [x.get("kind") for x in profile.get("verification", []) if x.get("kind")]
    req: list[str] = []
    if not changed_paths:
        return req
    # One relevant executable check is the floor if the project exposes one.
    if available:
        preferred = next((x for x in ["test", "typecheck", "build", "check", "lint"] if x in available), None)
        if preferred:
            req.append(preferred)
    if sensitive or strictness in {"strict", "paranoid"}:
        if "test" in available and "test" not in req:
            req.append("test")
        secondary = next((x for x in ["typecheck", "build", "check", "lint"] if x in available and x not in req), None)
        if secondary and strictness == "paranoid":
            req.append(secondary)
    # UI work gets its own floor: a design/accessibility check, when the
    # project has one, regardless of strictness — interface quality is not
    # supposed to depend on how "risky" the project's backend happens to be.
    if ui and "design" in available and "design" not in req:
        req.append("design")
    return req


def assess(verifications: list[dict], last_write: float, required_kinds: list[str]) -> dict:
    after = [v for v in verifications if float(v.get("time", 0)) >= last_write and v.get("success")]
    relevant = [v for v in after if v.get("relevance") in {"high", "medium"}]
    kinds = {v.get("kind") for v in relevant}
    missing = [k for k in required_kinds if k not in kinds]
    # If project has no explicit commands, any generic successful relevant command is acceptable.
    passed = bool(relevant) if not required_kinds else not missing
    max_rel = "none"
    for level in ("high", "medium", "low"):
        if any(v.get("relevance") == level for v in after):
            max_rel = level; break
    return {"passed": passed, "missing": missing, "successful_after_write": len(after), "relevant_after_write": len(relevant), "max_relevance": max_rel}
