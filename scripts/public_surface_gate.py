from pathlib import Path
import subprocess, sys
files=subprocess.check_output(['git','ls-files'],text=True).splitlines()
blocked=('AGENTS.md','CURRENT-STATE.md')
findings=[p for p in files if p in blocked or p.startswith('docs/internal/') or p.startswith('.specify/')]
if findings:
 print('PUBLIC SURFACE FAIL'); print('\n'.join(findings)); sys.exit(1)
subprocess.check_call([sys.executable,'tools/public_surface_check.py'])
subprocess.check_call([sys.executable,'tools/public_history_check.py'])
print('PUBLIC SURFACE PASS')
