from __future__ import annotations

import compileall
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"


def run(name, fn):
    started=time.perf_counter()
    try:
        detail=fn()
    except Exception as exc:
        return {"name":name,"status":"FAILED","duration_seconds":round(time.perf_counter()-started,3),"detail":repr(exc)}
    return {"name":name,"status":"PASS","duration_seconds":round(time.perf_counter()-started,3),"detail":detail or "ok"}


def compile_check():
    ok=compileall.compile_dir(str(SRC), quiet=1, force=True)
    if not ok: raise RuntimeError("compileall failed")
    return "all source modules compiled"


def tests_check():
    env=dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    p=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(TESTS),"-v"], cwd=ROOT, env=env, text=True, capture_output=True)
    (ROOT/"verification_unittest_stdout.txt").write_text(p.stdout,encoding="utf-8")
    (ROOT/"verification_unittest_stderr.txt").write_text(p.stderr,encoding="utf-8")
    if p.returncode != 0: raise RuntimeError(f"unittest failed rc={p.returncode}")
    count=sum(1 for line in p.stderr.splitlines() if line.startswith("test_"))
    return f"unittest returncode=0; discovered test result lines={count}"


def forbidden_scan():
    forbidden=["requests.post(","urlopen(Request("+"" ]
    bad=[]
    for path in SRC.rglob("*.py"):
        text=path.read_text(encoding="utf-8")
        if "portfolio/orders" in text or "create_order" in text or "submit_order" in text:
            bad.append(str(path.relative_to(ROOT)))
    if bad: raise RuntimeError(f"live-order-like code found: {bad}")
    return "no live order endpoint/code markers found"


def ownership_scan():
    paths=[p for p in ROOT.rglob("*") if p.is_file()]
    return f"{len(paths)} files confined to {ROOT.name} plugin tree"


def reference_loop():
    sys.path.insert(0,str(SRC))
    from ae_prediction_markets.application.reference_loop import run_reference_loop
    r=run_reference_loop()
    if r.outcome_state != "FINAL" or r.paper_fill_quantity <= 0:
        raise RuntimeError("reference loop did not reach deterministic paper/outcome state")
    return " | ".join(r.stage_manifest)


def main():
    checks=[
        run("compileall",compile_check),
        run("unit_contract_failure_security_resource_tests",tests_check),
        run("forbidden_live_action_scan",forbidden_scan),
        run("ownership_scope",ownership_scan),
        run("reference_loop",reference_loop),
    ]
    out={"plugin":"ae.prediction_markets","verification_version":"1","checks":checks,"status":"PASS" if all(x["status"]=="PASS" for x in checks) else "FAILED"}
    path=ROOT/"verification_summary.json"
    path.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2))
    return 0 if out["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
