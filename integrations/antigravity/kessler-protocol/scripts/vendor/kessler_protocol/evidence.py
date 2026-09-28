from __future__ import annotations

import re
import time

READ_RX = re.compile(r"(?:read|view|cat|open).*file|view_file|read_file", re.I)
SEARCH_RX = re.compile(r"grep|search|find", re.I)
WRITE_RX = re.compile(r"write|edit|replace|patch", re.I)
SOURCE_RX = re.compile(r"\.(?:py|js|jsx|ts|tsx|go|rs|java|kt|kts|cs|cpp|c|h|hpp|rb|php|swift|sql|tf|yaml|yml|json|toml)$", re.I)


def tool_class(tool: str) -> str | None:
    if SEARCH_RX.search(tool or ""):
        return "search"
    if READ_RX.search(tool or ""):
        return "read"
    if WRITE_RX.search(tool or ""):
        return "write"
    return None


def source_like(path: str) -> bool:
    if not path:
        return True
    return bool(SOURCE_RX.search(path))


def record_read(state: dict, target: str):
    state["reads"].append({"path": target, "time": time.time()})
    state["reads"] = state["reads"][-200:]


def record_search(state: dict, query: str):
    state["searches"].append({"query": query[:500], "time": time.time()})
    state["searches"] = state["searches"][-200:]


def record_write(state: dict, target: str, sensitive: bool, fake_success_signals: list[str] | None = None):
    state["writes"].append({"path": target, "sensitive": sensitive, "time": time.time(), "signals": fake_success_signals or []})
    state["writes"] = state["writes"][-200:]
    state["nudge_count"] = 0
    state.pop("waiver", None)


def has_discovery_before(state: dict, at: float) -> bool:
    return any(float(x.get("time", 0)) <= at for x in state.get("reads", [])) or any(float(x.get("time", 0)) <= at for x in state.get("searches", []))
