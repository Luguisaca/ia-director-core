"""Bounded local process execution for experimental capability adapters."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    output_truncated: bool


def run_bounded_process(
    argv: Sequence[str],
    *,
    timeout_seconds: float = 5.0,
    max_output_bytes: int = 16_384,
) -> ProcessResult:
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("argv must contain non-empty strings")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")

    try:
        completed = subprocess.run(
            list(argv),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        raw_out, raw_err = completed.stdout, completed.stderr
        combined = len(raw_out) + len(raw_err)
        remaining = max_output_bytes
        kept_out = raw_out[:remaining]
        remaining -= len(kept_out)
        kept_err = raw_err[:remaining]
        return ProcessResult(
            returncode=completed.returncode,
            stdout=kept_out.decode("utf-8", errors="replace"),
            stderr=kept_err.decode("utf-8", errors="replace"),
            timed_out=False,
            output_truncated=combined > max_output_bytes,
        )
    except subprocess.TimeoutExpired as exc:
        raw_out = exc.stdout or b""
        raw_err = exc.stderr or b""
        if isinstance(raw_out, str):
            raw_out = raw_out.encode()
        if isinstance(raw_err, str):
            raw_err = raw_err.encode()
        remaining = max_output_bytes
        kept_out = raw_out[:remaining]
        remaining -= len(kept_out)
        kept_err = raw_err[:remaining]
        return ProcessResult(
            returncode=None,
            stdout=kept_out.decode("utf-8", errors="replace"),
            stderr=kept_err.decode("utf-8", errors="replace"),
            timed_out=True,
            output_truncated=len(raw_out) + len(raw_err) > max_output_bytes,
        )
