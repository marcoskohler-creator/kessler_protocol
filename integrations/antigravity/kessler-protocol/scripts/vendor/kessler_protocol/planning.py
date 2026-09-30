from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

PLAN_RELATIVE_PATH = ".kessler/cache/implementation-plan.json"
_PLACEHOLDER = re.compile(r"\b(?:todo|tbd|placeholder|a definir|não sei|unknown)\b", re.IGNORECASE)
# File extensions that are, deterministically, always some form of rendered
# user interface surface (component markup or stylesheet) — used to catch a
# plan that declares mode: "non_ui" while its implementation actually touches
# files of this shape, which would otherwise let a UI task skip the
# design_standards requirement just by mislabeling itself. Kept to unambiguous
# extensions only (no .js/.ts/.py, which are also used for non-UI code) to
# avoid false positives on legitimate non-UI work.
_UI_SURFACE_EXTENSIONS = {".tsx", ".jsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss", ".sass", ".less"}


def _text(value: object, field: str, errors: list[str], minimum: int = 8) -> None:
    if not isinstance(value, str) or len(value.strip()) < minimum or _PLACEHOLDER.search(value):
        errors.append(f"{field} must be specific text ({minimum}+ characters, no placeholder)")


def _items(value: object, field: str, errors: list[str], minimum_count: int = 1) -> list:
    # minimum_count=0 still requires a real list (e.g. interface.side_effects,
    # which may legitimately be empty but must be an explicit list, not absent).
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    if len(value) < minimum_count:
        errors.append(f"{field} must have at least {minimum_count} item(s)")
    return value


def _validation_item(value: object, field: str, errors: list[str]) -> None:
    # A plain narrative string is still accepted; an object additionally lets
    # the plan name the exact command a later KES-VER-001 check can compare
    # against, without forcing every validation step to have one (a UI click
    # path, for example, has no single command).
    if isinstance(value, str):
        _text(value, field, errors)
        return
    if isinstance(value, dict):
        _text(value.get("description"), f"{field}.description", errors)
        command = value.get("command")
        if command is not None:
            _text(command, f"{field}.command", errors, minimum=3)
        return
    errors.append(f"{field} must be a string or an object with description/command")


def _design_standards(value: object, errors: list[str]) -> None:
    # Deterministic floor from platform interaction guidelines (Apple HIG /
    # Material / WCAG 2.2 AA), not a taste judgment: the model declares the
    # numbers, Kessler checks them against the real minimums. This only proves
    # the plan STATES compliant numbers; KES-VER-001 is what additionally
    # requires an executable accessibility/design-QA check (axe/pa11y/
    # lighthouse) to actually pass, when the project has one available.
    if not isinstance(value, dict):
        errors.append("interface.design_standards must be an object")
        return
    touch = value.get("touch_target_pt")
    if not isinstance(touch, (int, float)) or isinstance(touch, bool) or touch < 44:
        errors.append("interface.design_standards.touch_target_pt must be a number >= 44 (Apple HIG / Material minimum tap target)")
    contrast = value.get("contrast_ratio")
    if not isinstance(contrast, (int, float)) or isinstance(contrast, bool) or contrast < 4.5:
        errors.append("interface.design_standards.contrast_ratio must be a number >= 4.5 (WCAG 2.2 AA, normal text)")
    if value.get("supports_dynamic_type") is not True:
        errors.append("interface.design_standards.supports_dynamic_type must be true")
    if value.get("respects_reduced_motion") is not True:
        errors.append("interface.design_standards.respects_reduced_motion must be true")
    breakpoints = value.get("responsive_breakpoints")
    if not isinstance(breakpoints, list) or len(breakpoints) < 2:
        errors.append("interface.design_standards.responsive_breakpoints must list at least 2 breakpoints (e.g. mobile and desktop)")
    else:
        for index, item in enumerate(breakpoints):
            _text(item, f"interface.design_standards.responsive_breakpoints[{index}]", errors, minimum=3)


def _relative_path(value: object, workspace: Path, field: str, errors: list[str], *, must_exist: bool = False) -> str | None:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "*?[]"):
        errors.append(f"{field} must be one exact relative path")
        return None
    path = Path(value)
    if path.is_absolute():
        errors.append(f"{field} must be relative to the workspace")
        return None
    try:
        resolved = (workspace / path).resolve()
        relative = resolved.relative_to(workspace.resolve()).as_posix()
    except ValueError:
        errors.append(f"{field} must stay inside the workspace")
        return None
    if must_exist and not resolved.exists():
        errors.append(f"{field} does not exist: {value}")
    return relative


def validate_plan(data: object, workspace: Path) -> tuple[list[str], set[str], set[str]]:
    """Returns (errors, implementation_paths, discovery_paths). discovery_paths
    is used by plan_decision() to enforce KES-READ-001 (a discovery entry may
    only cite a path the session has real read evidence for)."""
    errors: list[str] = []
    paths: set[str] = set()
    discovery_paths: set[str] = set()
    if not isinstance(data, dict):
        return ["plan must be a JSON object"], paths, discovery_paths

    for field in ("goal", "purpose", "delivery", "rollback"):
        _text(data.get(field), field, errors)

    # justification answers "why, including problems this could cause later" —
    # separate from goal/purpose, which only cover the immediate ask.
    justification = data.get("justification")
    if not isinstance(justification, dict):
        errors.append("justification must be an object with why and future_risks")
    else:
        _text(justification.get("why"), "justification.why", errors)
        for index, value in enumerate(_items(justification.get("future_risks"), "justification.future_risks", errors, minimum_count=2)):
            _text(value, f"justification.future_risks[{index}]", errors)

    for index, value in enumerate(_items(data.get("users"), "users", errors)):
        _text(value, f"users[{index}]", errors)
    # usage_flow needs at least a before/after step, not a single vague line.
    for index, value in enumerate(_items(data.get("usage_flow"), "usage_flow", errors, minimum_count=2)):
        _text(value, f"usage_flow[{index}]", errors)

    for index, value in enumerate(_items(data.get("validation"), "validation", errors)):
        _validation_item(value, f"validation[{index}]", errors)

    for index, item in enumerate(_items(data.get("discovery"), "discovery", errors)):
        if not isinstance(item, dict):
            errors.append(f"discovery[{index}] must be an object")
            continue
        path = _relative_path(item.get("path"), workspace, f"discovery[{index}].path", errors, must_exist=True)
        if path:
            discovery_paths.add(path)
        _text(item.get("finding"), f"discovery[{index}].finding", errors)

    for index, item in enumerate(_items(data.get("implementation"), "implementation", errors)):
        if not isinstance(item, dict):
            errors.append(f"implementation[{index}] must be an object")
            continue
        path = _relative_path(item.get("path"), workspace, f"implementation[{index}].path", errors)
        if path:
            if path in paths:
                errors.append(f"implementation[{index}].path is duplicated")
            paths.add(path)
        # placement is often just the exact filename/location (e.g. "calc.py" —
        # 7 chars), so it gets a lower floor than narrative fields; the
        # placeholder-word regex in _text still catches lazy junk values.
        _text(item.get("placement"), f"implementation[{index}].placement", errors, minimum=3)
        for field in ("method", "responsibility"):
            _text(item.get(field), f"implementation[{index}].{field}", errors)

    interface = data.get("interface")
    if not isinstance(interface, dict):
        errors.append("interface must describe ui or non_ui")
    elif interface.get("mode") == "ui":
        _text(interface.get("entry_point"), "interface.entry_point", errors, minimum=3)
        _text(interface.get("final_screen"), "interface.final_screen", errors)
        _text(interface.get("accessibility"), "interface.accessibility", errors)
        _design_standards(interface.get("design_standards"), errors)
        # At least loading/empty/error-shaped states, not just the happy path.
        for index, value in enumerate(_items(interface.get("states"), "interface.states", errors, minimum_count=3)):
            _text(value, f"interface.states[{index}]", errors)
        for field, required, linked_paths in (
            ("controls", ("label", "location", "action", "destination", "failure"), ("handler_path", "evidence_path")),
            ("navigation", ("from", "via", "to", "evidence"), ("evidence_path",)),
        ):
            for index, item in enumerate(_items(interface.get(field), f"interface.{field}", errors)):
                if not isinstance(item, dict):
                    errors.append(f"interface.{field}[{index}] must be an object")
                    continue
                for key in required:
                    _text(item.get(key), f"interface.{field}[{index}].{key}", errors)
                for linked_path in linked_paths:
                    linked = _relative_path(item.get(linked_path), workspace,
                                            f"interface.{field}[{index}].{linked_path}", errors)
                    if linked and linked not in paths and not (workspace / linked).exists():
                        errors.append(f"interface.{field}[{index}].{linked_path} must exist or be planned")
    elif interface.get("mode") == "non_ui":
        _text(interface.get("entry_point"), "interface.entry_point", errors, minimum=3)
        for field in ("reason", "result", "data_contract", "failure_behavior"):
            _text(interface.get(field), f"interface.{field}", errors)
        # side_effects may legitimately be empty (a pure, isolated change) but
        # must be an explicit list — minimum_count=0 still requires the key.
        for index, value in enumerate(_items(interface.get("side_effects"), "interface.side_effects", errors, minimum_count=0)):
            _text(value, f"interface.side_effects[{index}]", errors)
        # Anti-gaming check: a plan cannot escape design_standards just by
        # declaring mode: "non_ui" while its implementation actually touches
        # UI-surface files. An honest exception (e.g. a server-rendered email
        # template with no client interaction) still goes through — but only
        # with an explicit, non-placeholder reason, mirroring how `kessler
        # waive --reason "..."` requires a documented reason rather than
        # silently skipping verification.
        ui_like = sorted(p for p in paths if Path(p).suffix.lower() in _UI_SURFACE_EXTENSIONS)
        if ui_like:
            override = interface.get("non_ui_override_reason")
            if not (isinstance(override, str) and len(override.strip()) >= 8 and not _PLACEHOLDER.search(override)):
                errors.append(
                    "interface.mode is \"non_ui\" but implementation touches UI-surface file(s): "
                    + ", ".join(ui_like[:5]) +
                    ". Reclassify as mode: \"ui\" (with design_standards), or if these are genuinely not "
                    "interactive UI (e.g. a server-rendered template with no client interaction), explain why "
                    "in interface.non_ui_override_reason (8+ characters, no placeholder)."
                )
    else:
        errors.append("interface.mode must be ui or non_ui")
    return errors, paths, discovery_paths


def plan_path(workspace: Path) -> Path:
    return workspace.resolve() / PLAN_RELATIVE_PATH


def is_plan_target(target: str, workspace: Path) -> bool:
    if not target:
        return False
    try:
        path = Path(target)
        return (path if path.is_absolute() else workspace / path).resolve() == plan_path(workspace)
    except (OSError, ValueError):
        return False


def read_plan(workspace: Path) -> tuple[str | None, set[str], list[str], set[str], str | None]:
    path = plan_path(workspace)
    try:
        raw = path.read_bytes()
        data = json.loads(raw)
    except (OSError, ValueError) as exc:
        return None, set(), [f"cannot read {PLAN_RELATIVE_PATH}: {exc}"], set(), None
    errors, paths, discovery_paths = validate_plan(data, workspace)
    interface_mode = None
    if isinstance(data, dict) and isinstance(data.get("interface"), dict) and data["interface"].get("mode") in ("ui", "non_ui"):
        interface_mode = data["interface"]["mode"]
    return hashlib.sha256(raw).hexdigest(), paths, errors, discovery_paths, interface_mode


def _normalized_target(target: str, workspace: Path) -> str | None:
    try:
        path = Path(target)
        return (path if path.is_absolute() else workspace / path).resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return None


def _read_evidence_paths(state: dict, workspace: Path) -> set[str]:
    # Mirrors the same normalization plan paths go through, so a read of
    # "src/audit.tsx" and a discovery entry for the same file match even if
    # the tool call used an absolute path.
    out: set[str] = set()
    for entry in state.get("reads", []):
        normalized = _normalized_target(str(entry.get("path", "")), workspace)
        if normalized:
            out.add(normalized)
    return out


def plan_decision(*, tool: str, command: str, target: str, workspace: Path, state: dict) -> dict | None:
    if is_plan_target(target, workspace):
        return None  # Writing or revising the plan itself is the bootstrap step.
    direct_write = bool(re.search(r"write|edit|replace|patch", tool, re.IGNORECASE))
    shell_execution = bool(command)
    if not direct_write and not shell_execution:
        return None
    digest, planned_paths, errors, discovery_paths, _interface_mode = read_plan(workspace)
    registered = state.get("plan", {})
    if errors or not digest or registered.get("sha256") != digest:
        detail = (" Invalid plan: " + "; ".join(errors[:3]) + ".") if errors else ""
        return {
            "decision": "deny", "policy_id": "KES-PLAN-001",
            "reason": "KES-PLAN-001: write a complete, evidence-based plan to "
                      f"{PLAN_RELATIVE_PATH} with the file-write tool before implementation."
                      " Include goal, purpose, justification (why, plus at least two future risks), users,"
                      " usage flow, discovery, interface, exact files and placement, method, delivery,"
                      " rollback, and validation."
                      + detail,
        }
    # KES-READ-001: a discovery claim about a file is only as good as the
    # evidence behind it. The plan already proved the path exists (must_exist
    # above); this proves the session actually opened it, not just named it.
    unread = sorted(p for p in discovery_paths if p not in _read_evidence_paths(state, workspace))
    if unread:
        return {
            "decision": "deny", "policy_id": "KES-READ-001",
            "reason": "KES-READ-001: discovery cites file(s) with no recorded read evidence in this session: "
                      + ", ".join(unread[:5]) +
                      ". Read each file with the read/view tool before citing its contents in the plan.",
        }
    if direct_write:
        normalized = _normalized_target(target, workspace)
        if normalized not in planned_paths:
            return {
                "decision": "deny", "policy_id": "KES-PLAN-002",
                "reason": f"KES-PLAN-002: {target or 'unknown target'} is absent from the registered implementation plan."
                          " Revise the plan before changing scope.",
            }
    return None
