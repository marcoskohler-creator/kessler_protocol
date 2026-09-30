import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NotifierTests(unittest.TestCase):
    def test_module_imports(self):
        import notifier  # noqa: F401


if __name__ == "__main__":
    unittest.main()
