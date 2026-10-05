"""Scan every published revision for private/internal material."""
from __future__ import annotations
import re, subprocess, sys

FORBIDDEN_PATHS=("BOOTSTRAP.md","CURRENT-STATE.md","CORE-READINESS.md","PILOT.md","REUSE-BENCHMARK.md")
FORBIDDEN_PREFIXES=(".specify/","specs/","benchmarks/","docs/internal/")
PATTERNS={
 "internal_marker": re.compile(r"\b(?:LAB-\d{3}|EXP-\d{3}|Agent Economy|pre-Lab|Notion)\b",re.I),
 "secret": re.compile(r"(?:-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bAKIA[0-9A-Z]{16}\b)"),
 "local_path": re.compile(r"(?:[A-Z]:\\\\Users\\\\|/home/[^/<\s]+/|/Users/[^/<\s]+/)",re.I),
}
ALLOW_PATTERN_FILES={"tools/public_surface_check.py","tools/public_history_check.py"}

def run(*args:str)->bytes:
 return subprocess.check_output(args)

def main()->int:
 findings=[]
 commits=run("git","rev-list","--all").decode().splitlines()
 for commit in commits:
  files=run("git","ls-tree","-r","--name-only","-z",commit).split(b"\0")
  for raw in files:
   if not raw: continue
   path=raw.decode("utf-8","replace")
   low=path.lower()
   if any(low==x.lower() for x in FORBIDDEN_PATHS) or any(low.startswith(x.lower()) for x in FORBIDDEN_PREFIXES):
    findings.append(f"forbidden historical path: {commit[:12]}:{path}")
    continue
   try: data=run("git","show",f"{commit}:{path}")
   except subprocess.CalledProcessError: continue
   if b"\0" in data[:8192]: continue
   try: text=data.decode("utf-8")
   except UnicodeDecodeError: continue
   if path in ALLOW_PATTERN_FILES: continue
   for kind,pattern in PATTERNS.items():
    if pattern.search(text): findings.append(f"{kind}: {commit[:12]}:{path}")
 if findings:
  print("PUBLIC-HISTORY CHECK: FAIL")
  for finding in sorted(set(findings)): print("-",finding)
  return 1
 print(f"PUBLIC-HISTORY CHECK: PASS ({len(commits)} revisions)")
 return 0
if __name__=="__main__": raise SystemExit(main())
