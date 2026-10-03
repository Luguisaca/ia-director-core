"""Fail-closed checks for accidental internal/private material in a distributable tree."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".whl", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip"}

FORBIDDEN_PATH_PARTS = {
    "bootstrap.md",
    "core-readiness.md",
    "reuse-benchmark.md",
    "pilot.md",
}

INTERNAL_MARKERS = re.compile(
    r"\b(?:LAB-\d{3}|EXP-\d{3}|Agent Economy|pre-Lab|Notion)\b",
    re.IGNORECASE,
)

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]

LOCAL_PATH_PATTERNS = [
    re.compile(r"(?i)(?:[A-Z]:\\Users\\|/home/[^/<\s]+/|/Users/[^/<\s]+/)"),
]

ALLOWLIST = {
    ("tools/public_surface_check.py", "internal_marker"),
    ("tools/public_surface_check.py", "secret_pattern"),
    ("tools/public_surface_check.py", "local_path"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [ROOT / p.decode() for p in result.stdout.split(b"\0") if p]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in path.parts) or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part.lower() in FORBIDDEN_PATH_PARTS for part in path.parts):
            findings.append(f"forbidden internal path: {rel}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        checks = [
            ("internal_marker", INTERNAL_MARKERS),
            ("secret_pattern", SECRET_PATTERNS),
            ("local_path", LOCAL_PATH_PATTERNS),
        ]
        for kind, patterns in checks:
            patterns = patterns if isinstance(patterns, list) else [patterns]
            for pattern in patterns:
                for match in pattern.finditer(text):
                    if (rel, kind) in ALLOWLIST:
                        continue
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append(f"{kind}: {rel}:{line}")

    if findings:
        print("PUBLIC-SURFACE CHECK: FAIL")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("PUBLIC-SURFACE CHECK: PASS")
    print(f"tracked files checked: {len(tracked_files())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
