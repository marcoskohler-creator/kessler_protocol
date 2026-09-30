from __future__ import annotations

import hashlib
import json
import os
import re
import time
import tomllib
from pathlib import Path

from .config import load_config
from .risk import score_profile, effective_strictness

PROFILE_SCHEMA = 2
KEY_FILES = [
    "package.json", "pnpm-workspace.yaml", "turbo.json", "nx.json", "yarn.lock", "pnpm-lock.yaml", "package-lock.json",
    "pyproject.toml", "requirements.txt", "poetry.lock", "uv.lock", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "prisma/schema.prisma", ".github/workflows",
]
SIGNAL_DIRS = {
    "authentication": {"auth", "authentication", "login", "session", "sessions"},
    "authorization": {"rbac", "permissions", "authorization", "iam", "acl"},
    "payments": {"payment", "payments", "billing", "checkout", "stripe"},
    "database": {"db", "database", "databases", "prisma", "models"},
    "migrations": {"migration", "migrations"},
    "medical": {"patient", "patients", "medical", "health", "healthcare", "clinic", "clinical"},
    "pii": {"users", "customers", "profiles", "accounts"},
    "secrets": {"secrets", "credentials"},
    "infrastructure": {"terraform", "infra", "k8s", "kubernetes", "helm"},
}
TEXT_SIGNAL = re.compile(r"(?:auth|oauth|jwt|rbac|stripe|payment|billing|patient|medical|hipaa|prisma|postgres|mysql|mongodb|redis)", re.I)


def _safe_json(path: Path) -> dict:
    try:
        if path.stat().st_size > 2_000_000:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_toml(path: Path) -> dict:
    try:
        if path.stat().st_size > 2_000_000:
            return {}
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _iter_signal_paths(root: Path, ignores: set[str]):
    max_files = 5000
    seen = 0
    for current, dirs, files in os.walk(root):
        rel = Path(current).relative_to(root)
        if len(rel.parts) > 3:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in ignores and not d.startswith(".cache")]
        for name in dirs + files:
            seen += 1
            if seen > max_files:
                return
            yield (rel / name).as_posix().lower()


def fingerprint(root: Path, config: dict | None = None) -> str:
    root = Path(root).resolve()
    h = hashlib.sha256()
    for rel in KEY_FILES:
        p = root / rel
        if p.is_file():
            h.update(rel.encode())
            try:
                h.update(p.read_bytes()[:2_000_000])
            except OSError:
                pass
    ignores = set((config or {}).get("paths", {}).get("ignore", [])) | {".git", "node_modules", ".venv", "venv", "dist", "build", "target"}
    for rel in sorted(_iter_signal_paths(root, ignores) or []):
        if TEXT_SIGNAL.search(rel):
            h.update(rel.encode())
    return h.hexdigest()


def _node_profile(root: Path, profile: dict):
    pkg = _safe_json(root / "package.json")
    if not pkg:
        return
    profile["languages"].add("javascript/typescript")
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps.update(pkg.get(key) or {})
    dep_names = {str(k).lower() for k in deps}
    scripts = pkg.get("scripts") or {}
    frameworks = profile["frameworks"]
    for dep, label in {
        "next": "nextjs", "react": "react", "vue": "vue", "nuxt": "nuxt", "svelte": "svelte", "@sveltejs/kit": "sveltekit",
        "express": "express", "fastify": "fastify", "nestjs": "nestjs", "@nestjs/core": "nestjs",
    }.items():
        if dep in dep_names:
            frameworks.add(label)
    for dep in dep_names:
        if dep in {"prisma", "@prisma/client", "pg", "postgres", "mysql2", "mongoose", "mongodb", "sequelize", "typeorm"}:
            profile["features"]["database"] = True
        if dep in {"next-auth", "@auth/core", "passport", "jsonwebtoken", "jose", "clerk", "@clerk/nextjs"}:
            profile["features"]["authentication"] = True
        if "stripe" in dep or dep in {"paypal-rest-sdk", "@paypal/paypal-js"}:
            profile["features"]["payments"] = True
        if dep in {"axios", "got", "ky", "undici"}:
            profile["features"]["external_api"] = True
    for kind, names in {
        "test": ("test", "test:unit", "test:ci"),
        "build": ("build",),
        "lint": ("lint",),
        "typecheck": ("typecheck", "type-check", "check:types"),
        "check": ("check",),
        "design": ("test:a11y", "a11y", "lint:a11y", "accessibility"),
    }.items():
        for name in names:
            if name in scripts:
                profile["verification"].append({"kind": kind, "command": f"npm run {name}", "source": "package.json"})
                break
    # A dedicated a11y/design-QA CLI in dependencies also counts, even without
    # a named script for it — this is what KES-VER-001 can then require for UI work.
    if not any(v["kind"] == "design" for v in profile["verification"]):
        for dep, cmd in (
            ("pa11y", "npx pa11y"),
            ("@axe-core/cli", "npx axe"),
            ("axe-core", "npx axe"),
            ("@lhci/cli", "npx lhci autorun"),
        ):
            if dep in dep_names:
                profile["verification"].append({"kind": "design", "command": cmd, "source": "package.json"})
                break
    workspaces = pkg.get("workspaces")
    if workspaces or (root / "pnpm-workspace.yaml").exists() or (root / "turbo.json").exists() or (root / "nx.json").exists():
        profile["features"]["monorepo"] = True


def _python_profile(root: Path, profile: dict):
    pyproject = _safe_toml(root / "pyproject.toml")
    req = ""
    for p in (root / "requirements.txt",):
        if p.exists():
            try: req += p.read_text(encoding="utf-8")[:1_000_000].lower()
            except OSError: pass
    if not pyproject and not req:
        return
    profile["languages"].add("python")
    text = json.dumps(pyproject, default=str).lower() + req
    for needle, label in (("django", "django"), ("fastapi", "fastapi"), ("flask", "flask")):
        if needle in text: profile["frameworks"].add(label)
    if any(x in text for x in ("sqlalchemy", "psycopg", "django", "pymongo", "alembic")):
        profile["features"]["database"] = True
    if any(x in text for x in ("pytest", "unittest")) or (root / "tests").exists():
        profile["verification"].append({"kind": "test", "command": "python -m pytest", "source": "python"})
    if "ruff" in text:
        profile["verification"].append({"kind": "lint", "command": "ruff check .", "source": "python"})
    if "mypy" in text:
        profile["verification"].append({"kind": "typecheck", "command": "mypy .", "source": "python"})
    if "pyright" in text:
        profile["verification"].append({"kind": "typecheck", "command": "pyright", "source": "python"})


def _other_profiles(root: Path, profile: dict):
    if (root / "Cargo.toml").exists():
        profile["languages"].add("rust")
        profile["verification"].extend([
            {"kind": "test", "command": "cargo test", "source": "Cargo.toml"},
            {"kind": "check", "command": "cargo check", "source": "Cargo.toml"},
        ])
    if (root / "go.mod").exists():
        profile["languages"].add("go")
        profile["verification"].append({"kind": "test", "command": "go test ./...", "source": "go.mod"})
    if (root / "pom.xml").exists():
        profile["languages"].add("java")
        profile["verification"].append({"kind": "test", "command": "mvn test", "source": "pom.xml"})
    if (root / "gradlew").exists() or (root / "build.gradle").exists():
        profile["languages"].add("jvm")
        profile["verification"].append({"kind": "test", "command": "./gradlew test", "source": "gradle"})
    if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
        profile["features"]["infrastructure"] = True
    if (root / "prisma" / "schema.prisma").exists():
        profile["features"]["database"] = True
    if (root / "migrations").exists() or (root / "prisma" / "migrations").exists():
        profile["features"]["migrations"] = True
    if (root / ".github" / "workflows").exists():
        profile["ci"] = "github-actions"


def _path_signals(root: Path, profile: dict, cfg: dict):
    ignores = set(cfg.get("paths", {}).get("ignore", [])) | {".git", "node_modules", ".venv", "venv", "dist", "build", "target"}
    sensitive: set[str] = set()
    for rel in _iter_signal_paths(root, ignores) or []:
        parts = set(Path(rel).parts)
        for feature, terms in SIGNAL_DIRS.items():
            if parts & terms:
                profile["features"][feature] = True
                if feature in {"authentication", "authorization", "payments", "database", "migrations", "medical", "pii", "secrets"}:
                    sensitive.add(rel)
        if rel.startswith(".env") or "/.env" in rel:
            profile["features"]["secrets"] = True
            sensitive.add(rel)
    profile["sensitive_paths"].extend(sorted(sensitive)[:200])


def build_profile(root: Path, cfg: dict | None = None) -> dict:
    root = Path(root).resolve()
    cfg = cfg or load_config(root)
    profile = {
        "schema_version": PROFILE_SCHEMA,
        "generated_at": int(time.time()),
        "workspace": str(root),
        "fingerprint": "",
        "languages": set(),
        "frameworks": set(),
        "features": {k: False for k in ["database", "migrations", "authentication", "authorization", "payments", "medical", "pii", "secrets", "infrastructure", "external_api", "monorepo"]},
        "verification": [],
        "sensitive_paths": [],
        "ci": None,
    }
    _node_profile(root, profile)
    _python_profile(root, profile)
    _other_profiles(root, profile)
    _path_signals(root, profile, cfg)
    for pat in cfg.get("paths", {}).get("sensitive", []):
        profile["sensitive_paths"].append(pat)
    # De-duplicate verification while preserving order.
    seen = set(); ver=[]
    for item in profile["verification"]:
        key=(item["kind"],item["command"])
        if key not in seen:
            seen.add(key); ver.append(item)
    profile["verification"] = ver
    score, level, reasons = score_profile(profile["features"])
    profile["risk"] = {"score": score, "level": level, "reasons": reasons, "strictness": effective_strictness(cfg.get("strictness", "auto"), level)}
    profile["languages"] = sorted(profile["languages"])
    profile["frameworks"] = sorted(profile["frameworks"])
    profile["sensitive_paths"] = sorted(set(profile["sensitive_paths"]))
    profile["fingerprint"] = fingerprint(root, cfg)
    return profile


def cache_path(root: Path) -> Path:
    return Path(root).resolve() / ".kessler" / "cache" / "project-profile.json"


def get_profile(root: Path, refresh: bool = False) -> dict:
    root = Path(root).resolve()
    cfg = load_config(root)
    path = cache_path(root)
    current_fp = fingerprint(root, cfg)
    if not refresh and cfg.get("profile", {}).get("cache", True) and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema_version") == PROFILE_SCHEMA and data.get("fingerprint") == current_fp:
                return data
        except Exception:
            pass
    data = build_profile(root, cfg)
    if cfg.get("profile", {}).get("cache", True):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass
    return data
