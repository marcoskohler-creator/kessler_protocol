from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/"vendor"))
from kessler_protocol.hook_runtime import main
if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--harness",required=True); p.add_argument("--event",required=True)
    a=p.parse_args(); raise SystemExit(main(a.harness,a.event))
