from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from alpha_engine.bootstrap.lifecycle import RuntimeAlreadyRunning
from alpha_engine.reference_loop.runner import run as run_reference_compat
from alpha_engine.reference_loop.runner import run_with_runtime
from alpha_engine.runtime.application import build_runtime
from alpha_engine.runtime.control import read_runtime_discovery, request_runtime, serve_runtime
from alpha_engine.verification.runner import run_verification


def _default_profile(name: str = "default") -> Path:
    if name == "default" and os.environ.get("ALPHA_PROFILE"):
        return Path(os.environ["ALPHA_PROFILE"]).expanduser()
    return Path.home() / ".alpha_engine" / name


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _add_profile(parser: argparse.ArgumentParser, name: str = "default") -> None:
    parser.add_argument("--profile", default=str(_default_profile(name)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alpha")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start", help="start the authoritative local runtime")
    _add_profile(start)
    start.add_argument("--headless", action="store_true")
    start.add_argument("--port", type=int, default=8765)

    demo = sub.add_parser("demo", help="seed and launch the deterministic demo profile")
    _add_profile(demo, "demo")
    demo.add_argument("--headless", action="store_true")
    demo.add_argument("--port", type=int, default=8766)
    demo.add_argument("--reset", action="store_true")
    demo.add_argument("--seed-only", action="store_true")

    status = sub.add_parser("status", help="show runtime/composition/readiness status")
    _add_profile(status)

    stop = sub.add_parser("stop", help="request graceful shutdown of the selected profile runtime")
    _add_profile(stop)

    verify = sub.add_parser("verify", help="run deterministic verification")
    verify_sub = verify.add_subparsers(dest="verify_tier", required=True)
    verify_sub.add_parser("quick")
    verify_sub.add_parser("full")
    feature = verify_sub.add_parser("feature")
    feature.add_argument("feature_id")

    qualify = sub.add_parser("qualify", help="run deterministic release/readiness qualification")
    qualify.add_argument("--live", action="store_true", help="reserved opt-in; no live provider is qualified yet")

    legacy = sub.add_parser("reference-loop", help="historical lower-level deterministic reference runner")
    legacy.add_argument("--db", default="alpha-reference.sqlite3")
    legacy.add_argument("--artifacts", default="alpha-reference-artifacts")
    return parser


def _start(profile: Path, *, mode: str, headless: bool, port: int) -> int:
    try:
        runtime = build_runtime(profile, mode=mode, acquire_lease=True)
    except RuntimeAlreadyRunning as exc:
        _print({"status": "BLOCKED", "reason_code": "SECOND_INSTANCE", "reason": str(exc)})
        return 2
    health = runtime.health.snapshot()
    if health["status"] != "READY":
        runtime.close()
        _print({"status": "BLOCKED", "health": health})
        return 3
    _print({"status": "STARTING", "profile": str(profile.resolve()), "mode": mode, "port": port})
    try:
        return serve_runtime(runtime, port=port, desktop=not headless)
    except BaseException:
        # serve_runtime owns normal cleanup; ensure lease is not stranded on startup exceptions.
        runtime.close()
        raise


def _demo(args: argparse.Namespace) -> int:
    profile = Path(args.profile).expanduser()
    if args.reset:
        discovery = read_runtime_discovery(profile)
        if discovery:
            _print({"status": "BLOCKED", "reason": "cannot reset an active/discovered demo profile; stop it first"})
            return 2
        shutil.rmtree(profile, ignore_errors=True)
    try:
        runtime = build_runtime(profile, mode="demo", acquire_lease=True)
    except RuntimeAlreadyRunning as exc:
        _print({"status": "BLOCKED", "reason_code": "SECOND_INSTANCE", "reason": str(exc)})
        return 2
    try:
        manifest = run_with_runtime(runtime)
        _print({"status": "DEMO_SEEDED", "profile": str(profile.resolve()), "manifest": manifest})
        if args.seed_only:
            runtime.close()
            return 0
        return serve_runtime(runtime, port=args.port, desktop=not args.headless)
    except BaseException:
        runtime.close()
        raise


def _status(profile: Path) -> int:
    discovery = read_runtime_discovery(profile)
    if discovery:
        try:
            payload = request_runtime(profile, "/internal/v1/status")
            payload["discovery"] = {k: v for k, v in discovery.items() if k != "session_token"}
            _print(payload)
            return 0 if payload.get("health", {}).get("status") == "READY" else 1
        except RuntimeError as exc:
            _print({"status": "STALE_OR_UNREACHABLE", "reason": str(exc), "discovery": {k: v for k, v in discovery.items() if k != "session_token"}})
            return 1
    runtime = build_runtime(profile, mode="offline-status", acquire_lease=False)
    try:
        payload = runtime.status()
        payload["runtime"]["online"] = False
        _print(payload)
        return 0 if payload["health"]["status"] == "READY" else 1
    finally:
        runtime.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "reference-loop":
        _print(run_reference_compat(args.db, args.artifacts))
        return
    if args.cmd == "start":
        raise SystemExit(_start(Path(args.profile).expanduser(), mode="normal", headless=args.headless, port=args.port))
    if args.cmd == "demo":
        raise SystemExit(_demo(args))
    if args.cmd == "status":
        raise SystemExit(_status(Path(args.profile).expanduser()))
    if args.cmd == "stop":
        try:
            _print(request_runtime(Path(args.profile).expanduser(), "/internal/v1/shutdown", method="POST"))
            return
        except RuntimeError as exc:
            _print({"status": "NOT_RUNNING", "reason": str(exc)})
            raise SystemExit(2) from exc
    if args.cmd == "verify":
        tier = args.verify_tier
        feature_id = getattr(args, "feature_id", None)
        result = run_verification("feature" if tier == "feature" else tier, feature_id=feature_id)
        raise SystemExit(0 if result["readiness"] == "READY" else 1)
    if args.cmd == "qualify":
        result = run_verification("qualification")
        if args.live:
            print("LIVE_PROVIDER_QUALIFICATION=BLOCKED: no provider/rights path is qualified in this pass", file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0 if result["readiness"] == "READY" else 1)


if __name__ == "__main__":
    main()
