from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

STATE_SCHEMA = 2
LOCK_TIMEOUT = 2.0
STALE_LOCK = 30.0


def _state_root() -> Path:
    p = Path.home() / ".kessler" / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def key(session_id: str, workspace: str = "") -> str:
    return hashlib.sha256((str(session_id) + "|" + str(workspace)).encode()).hexdigest()[:32]


def path_for(session_id: str, workspace: str = "") -> Path:
    return _state_root() / f"{key(session_id, workspace)}.json"


@contextmanager
def _lock(path: Path):
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.time() + LOCK_TIMEOUT
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > STALE_LOCK:
                    lock.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.time() >= deadline:
                raise TimeoutError(f"Kessler state lock timeout: {lock}")
            time.sleep(0.03)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def empty(session_id: str, workspace: str) -> dict:
    return {
        "schema_version": STATE_SCHEMA,
        "session_id": str(session_id),
        "workspace": str(workspace),
        "updated_at": time.time(),
        "reads": [],
        "searches": [],
        "writes": [],
        "verifications": [],
        "interventions": [],
        "warnings": [],
        "nudge_count": 0,
        "profile_fingerprint": "",
    }


def load(session_id: str, workspace: str = "") -> dict:
    p = path_for(session_id, workspace)
    if not p.exists():
        return empty(session_id, workspace)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if data.get("schema_version") == STATE_SCHEMA else empty(session_id, workspace)
    except Exception:
        return empty(session_id, workspace)


def save(state: dict) -> None:
    p = path_for(state.get("session_id", "unknown"), state.get("workspace", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.time()
    with _lock(p):
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)


def update(session_id: str, workspace: str, fn):
    p = path_for(session_id, workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock(p):
        if p.exists():
            try: state = json.loads(p.read_text(encoding="utf-8"))
            except Exception: state = empty(session_id, workspace)
        else:
            state = empty(session_id, workspace)
        fn(state)
        state["updated_at"] = time.time()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return state


def latest(workspace: str | None = None) -> dict | None:
    root = _state_root()
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files:
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
            if workspace is None or str(Path(data.get("workspace", "")).resolve()) == str(Path(workspace).resolve()):
                return data
        except Exception:
            continue
    return None


def prune(max_age_days: int = 7):
    cutoff=time.time() - max_age_days*86400
    for p in _state_root().glob("*.json"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass
