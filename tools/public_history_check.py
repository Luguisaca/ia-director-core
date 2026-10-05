"""Scan published Git history for private/internal material."""
from __future__ import annotations
import re, subprocess, sys

FORBIDDEN_PATH=re.compile(r"(?im)^(?:.*?/)?(?:BOOTSTRAP\.md|CURRENT-STATE\.md|CORE-READINESS\.md|PILOT\.md|REUSE-BENCHMARK\.md)$|^(?:\.specify|specs|benchmarks|docs/internal)/")
CONTENT_PATTERNS={
 "internal_marker": re.compile(r"\b(?:LAB-\d{3}|EXP-\d{3}|Agent Economy|pre-Lab)\b",re.I),
 "secret": re.compile(r"(?:-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bAKIA[0-9A-Z]{16}\b)"),
 "local_path": re.compile(r"(?:[A-Z]:\\\\Users\\\\|/home/[^/<\s]+/|/Users/[^/<\s]+/)",re.I),
}
# Scanner source intentionally contains the signatures. Remove its diff sections before content checks.
SCANNER_HEADERS=("tools/public_surface_check.py","tools/public_history_check.py")

def output(*args:str)->str:
 return subprocess.check_output(args,text=True,encoding="utf-8",errors="replace")

def strip_scanner_diffs(patch:str)->str:
 chunks=patch.split("\ndiff --git ")
 kept=[chunks[0]]
 for chunk in chunks[1:]:
  header=chunk.splitlines()[0] if chunk.splitlines() else ""
  if any(path in header for path in SCANNER_HEADERS): continue
  kept.append("\ndiff --git "+chunk)
 return "".join(kept)

def main()->int:
 findings=[]
 names=output("git","log","--all","--name-only","--pretty=format:")
 for match in FORBIDDEN_PATH.finditer(names):
  findings.append("forbidden historical path: "+match.group(0))
 patch=strip_scanner_diffs(output("git","log","--all","-p","--no-ext-diff","--full-history"))
 for kind,pattern in CONTENT_PATTERNS.items():
  if pattern.search(patch): findings.append(kind+" found in published history")
 if findings:
  print("PUBLIC-HISTORY CHECK: FAIL")
  for finding in sorted(set(findings)): print("-",finding)
  return 1
 count=output("git","rev-list","--count","--all").strip()
 print(f"PUBLIC-HISTORY CHECK: PASS ({count} revisions)")
 return 0
if __name__=="__main__": raise SystemExit(main())
