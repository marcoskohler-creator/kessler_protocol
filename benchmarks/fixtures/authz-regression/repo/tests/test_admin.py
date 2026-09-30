import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from admin import list_pending_audits, AuthorizationError

ADMIN = SimpleNamespace(is_admin=True)
REGULAR = SimpleNamespace(is_admin=False)


class AuthzTests(unittest.TestCase):
    def test_admin_can_list(self):
        result = list_pending_audits(ADMIN)
        self.assertTrue(len(result) > 0)

    def test_non_admin_is_rejected(self):
        with self.assertRaises(AuthorizationError):
            list_pending_audits(REGULAR)


if __name__ == "__main__":
    unittest.main()
