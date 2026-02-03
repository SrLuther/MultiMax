#!/usr/bin/env python3
import re
from pathlib import Path

content = Path("multimax/__init__.py").read_text(encoding="utf-8")
pattern = r"return ['\"](\d+\.\d+\.\d+)['\"]"
matches = list(re.finditer(pattern, content))

if matches:
    for m in matches:
        line_num = content[: m.start()].count("\n") + 1
        print(f"Line {line_num}: {m.group(0)}")
else:
    print("Not found")
