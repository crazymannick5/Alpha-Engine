from alpha_engine.verification.runner import run_verification


if __name__ == "__main__":
    result = run_verification("full")
    raise SystemExit(0 if result["readiness"] == "READY" else 1)
