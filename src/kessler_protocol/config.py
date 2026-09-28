from __future__ import annotations

import copy
import fnmatch
import tomllib
from pathlib import Path

CONFIG_NAME = ".kessler.toml"

DEFAULT_CONFIG = {
    "version": 1,
    "strictness": "auto",
    "context": "lean",
    "profile": {"auto": True, "cache": True},
    "verification": {"auto_detect": True, "required": []},
    "policy": {"lazy_loading": True},
    "paths": {
        "sensitive": [],
        "ignore": [".git", ".kessler/cache", "node_modules", ".next", "dist", "build", ".venv", "venv", "vendor", "target"],
    },
    "commands": {"allow": [], "deny": []},
}

TEMPLATE = '''# Kessler Protocol project configuration
# Most settings are intentionally automatic. Manual values override detection.
version = 1
strictness = "auto" # auto | balanced | strict | paranoid
context = "lean"    # lean | standard | deep

[profile]
auto = true
cache = true

[verification]
auto_detect = true
required = []

[policy]
lazy_loading = true

[paths]
sensitive = []
ignore = [".git", ".kessler/cache", "node_modules", ".next", "dist", "build", ".venv", "venv", "vendor", "target"]

[commands]
allow = []
deny = []
'''


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(workspace: Path) -> dict:
    workspace = Path(workspace).resolve()
    path = workspace / CONFIG_NAME
    if not path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a TOML table")
    cfg = _merge(DEFAULT_CONFIG, data)
    if cfg["strictness"] not in {"auto", "balanced", "strict", "paranoid"}:
        raise ValueError("strictness must be auto, balanced, strict, or paranoid")
    if cfg["context"] not in {"lean", "standard", "deep"}:
        raise ValueError("context must be lean, standard, or deep")
    return cfg


def init_config(workspace: Path, force: bool = False) -> Path:
    workspace = Path(workspace).resolve()
    path = workspace / CONFIG_NAME
    if path.exists() and not force:
        return path
    path.write_text(TEMPLATE, encoding="utf-8")
    return path


def path_matches(path: str, patterns: list[str]) -> bool:
    norm = path.replace("\\", "/").lstrip("./")
    return any(fnmatch.fnmatch(norm, pat.replace("\\", "/")) or fnmatch.fnmatch("/" + norm, pat) for pat in patterns)
