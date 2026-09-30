import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import new_connection, seed


class MigrationTests(unittest.TestCase):
    def test_existing_data_preserved(self):
        conn = new_connection()
        seed(conn)
        row = conn.execute("SELECT id, email, name FROM users WHERE id=1").fetchone()
        self.assertEqual(row, (1, "a@example.com", "Alice"))


if __name__ == "__main__":
    unittest.main()
