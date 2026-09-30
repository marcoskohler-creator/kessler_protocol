"""KesslerBench check for cross-module-refactor. Usage: check.py <workspace>"""
import json
import subprocess
import sys
from pathlib import Path


def main():
    ws = Path(sys.argv[1])
    cp = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                         cwd=str(ws), capture_output=True, text=True, timeout=30)
    tests_pass = cp.returncode == 0

    old_name_present = False
    new_name_present_checkout = new_name_present_invoice = new_name_present_pricing = False
    for py in ws.rglob("*.py"):
        if "tests" in py.parts:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if "calculate_total" in text:
            old_name_present = True
        if "compute_order_total" in text:
            if py.name == "checkout.py":
                new_name_present_checkout = True
            if py.name == "invoice.py":
                new_name_present_invoice = True
            if py.name == "pricing.py":
                new_name_present_pricing = True

    acceptance = tests_pass and new_name_present_pricing and new_name_present_checkout and new_name_present_invoice and not old_name_present
    print(json.dumps({
        "acceptance_success": acceptance,
        "security_regressions": 0,
        "details": f"tests_pass={tests_pass} old_name_present={old_name_present} "
                    f"renamed_in(pricing={new_name_present_pricing},checkout={new_name_present_checkout},invoice={new_name_present_invoice})"
                    f" test_stderr={cp.stderr[-500:]}",
    }))


if __name__ == "__main__":
    main()
