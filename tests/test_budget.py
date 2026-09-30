import unittest
from kessler_protocol.context_budget import measure

class BudgetTests(unittest.TestCase):
    def test_always_on_budget_stays_small(self):
        b=measure()
        self.assertLessEqual(b["always_on"]["approx_tokens"],b["budget_targets"]["always_on_approx_tokens_max"])
        self.assertEqual(b["policy_catalog_prompt_tokens"],0)

if __name__=="__main__": unittest.main()
