import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from checkout import checkout
from invoice import build_invoice

CART = [{"price": 10.0, "qty": 2}, {"price": 5.0, "qty": 3}]


class RefactorTests(unittest.TestCase):
    def test_checkout_total(self):
        self.assertEqual(checkout(CART), 35.0)

    def test_invoice_total(self):
        inv = build_invoice(CART)
        self.assertEqual(inv["total"], 35.0)
        self.assertEqual(inv["line_count"], 2)


if __name__ == "__main__":
    unittest.main()
