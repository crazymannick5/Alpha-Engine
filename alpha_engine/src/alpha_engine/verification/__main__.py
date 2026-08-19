from __future__ import annotations

import argparse

from .runner import run_verification


def main() -> None:
    parser = argparse.ArgumentParser(prog="alpha verify")
    parser.add_argument("tier", choices=["quick", "full", "qualification", "feature"])
    parser.add_argument("feature_id", nargs="?")
    args = parser.parse_args()
    result = run_verification(args.tier, feature_id=args.feature_id)
    raise SystemExit(0 if result["readiness"] == "READY" else 1)


if __name__ == "__main__":
    main()
