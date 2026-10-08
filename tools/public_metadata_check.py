"""Reject private development vocabulary from new public change metadata."""
from __future__ import annotations

import os
import re
import subprocess
import sys

FORBIDDEN = re.compile(
    r"(?i)(?:\bINTERNAL\b|INTERNAL\s*(?:→|->)\s*PUBLIC|\bLAB-\d{3}\b|"
    r"\bEXP-\d{3}\b|\bNotion\b|\bpre-Lab\b|\bAgent Economy\b|"
    r"(?:[A-Z]:\\\\(?:Users|Luguisaca|LevelUp)\\\\)|/home/[^/<\s]+/|/Users/[^/<\s]+/)"
)

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8", errors="replace")

def main() -> int:
    base = os.environ.get("BASE_SHA", "").strip()
    head = os.environ.get("HEAD_SHA", "HEAD").strip()
    values = {
        "pull request title": os.environ.get("PR_TITLE", ""),
        "pull request body": os.environ.get("PR_BODY", ""),
        "branch name": os.environ.get("HEAD_REF", ""),
    }
    if base:
        values["new commit metadata"] = git("log", "--format=%B", f"{base}..{head}")
    findings = [name for name, value in values.items() if FORBIDDEN.search(value)]
    if findings:
        print("REPOSITORY-METADATA CHECK: FAIL")
        for name in findings:
            print(f"- private development vocabulary found in {name}")
        return 1
    print("REPOSITORY-METADATA CHECK: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
