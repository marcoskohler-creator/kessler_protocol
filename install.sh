#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install .
echo "Kessler CLI installed. No agent configuration was modified automatically."
echo "Recommended next steps:"
echo "  kessler init"
echo "  kessler budget"
echo "  kessler install --target antigravity --scope user --surface ide"
echo "  kessler install --target antigravity --scope user --surface cli"
echo "  kessler install --target gemini --scope user"
echo "  kessler doctor --target package --deep"
