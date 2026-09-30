from __future__ import annotations
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from kessler_protocol.templates import write_antigravity_template, write_gemini_skill, write_claude_code_skill

SRC=ROOT/"src"/"kessler_protocol"
AG=ROOT/"integrations"/"antigravity"/"kessler-protocol"
GM=ROOT/"integrations"/"gemini-cli"/"skill"/"kessler-protocol"
CC=ROOT/"integrations"/"claude-code"/"skill"/"kessler-protocol"

if AG.exists(): shutil.rmtree(AG)
write_antigravity_template(AG)
VENDOR=AG/"scripts"/"vendor"/"kessler_protocol"
shutil.copytree(SRC,VENDOR,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
if GM.exists(): shutil.rmtree(GM)
write_gemini_skill(GM)
if CC.exists(): shutil.rmtree(CC)
write_claude_code_skill(CC)
print("Integration artifacts rebuilt from canonical source/templates")
