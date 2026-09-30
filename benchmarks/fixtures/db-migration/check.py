"""KesslerBench check for db-migration. Usage: check.py <workspace>"""
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


def main():
    ws = Path(sys.argv[1])
    cp = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                         cwd=str(ws), capture_output=True, text=True, timeout=30)
    base_tests_pass = cp.returncode == 0

    init_untouched = True
    original_init = "CREATE TABLE users (\n    id INTEGER PRIMARY KEY,\n    email TEXT NOT NULL,\n    name TEXT NOT NULL\n);\n"
    init_path = ws / "migrations" / "001_init.sql"
    if init_path.exists():
        init_untouched = init_path.read_text(encoding="utf-8") == original_init

    new_migration_files = sorted(p for p in (ws / "migrations").glob("*.sql") if p.name != "001_init.sql")
    has_new_migration = len(new_migration_files) > 0
    correct_numbering = all(re.match(r"^\d{3}_", p.name) for p in new_migration_files) if new_migration_files else False

    column_added = False
    nullable_and_backward_compatible = False
    detail = f"base_tests_pass={base_tests_pass} init_untouched={init_untouched} has_new_migration={has_new_migration} correct_numbering={correct_numbering} new_files={[p.name for p in new_migration_files]}"
    try:
        sys.path.insert(0, str(ws))
        import importlib
        db = importlib.import_module("db")
        importlib.reload(db)
        conn = db.new_connection()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        column_added = "phone_number" in cols
        db.seed(conn)
        row = conn.execute("SELECT id, email, name FROM users WHERE id=1").fetchone()
        nullable_and_backward_compatible = row == (1, "a@example.com", "Alice")
        detail += f" columns={cols} existing_row_ok={nullable_and_backward_compatible}"
    except Exception as exc:
        detail += f" exception:{exc!r}"

    acceptance = base_tests_pass and init_untouched and has_new_migration and correct_numbering and column_added and nullable_and_backward_compatible
    print(json.dumps({"acceptance_success": acceptance, "security_regressions": 0, "details": detail}))


if __name__ == "__main__":
    main()
