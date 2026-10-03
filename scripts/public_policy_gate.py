from pathlib import Path
import sys
required=['README.md','LICENSE','pyproject.toml','docs/ASSURANCE.md']
missing=[p for p in required if not Path(p).is_file()]
if missing:
 print('POLICY FAIL: '+', '.join(missing)); sys.exit(1)
print('POLICY PASS')
