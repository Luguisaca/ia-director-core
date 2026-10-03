from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import Authorization, run_intent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the IA Director Core experimental local slice.")
    parser.add_argument("intent", help="Human intent to record and process")
    parser.add_argument("--records-dir", type=Path, default=Path("records"))
    parser.add_argument("--authorize", action="store_true", help="Explicitly authorize the demonstration")
    parser.add_argument("--authorized-by", help="Human identity granting authorization")
    parser.add_argument("--scope", help="Exact capability scope authorized by the named human")
    parser.add_argument("--risk-tier", help="Exact risk tier authorized by the named human (demo: low)")
    args = parser.parse_args(argv)
    record, path = run_intent(
        args.intent,
        Authorization(args.authorize, args.authorized_by, args.scope, args.risk_tier),
        args.records_dir,
    )
    print(json.dumps({"record": str(path), "status": record["status"], "human_gate": record["human_gate"]}, indent=2))
    return 0 if record["status"] == "HUMAN_TEST_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
