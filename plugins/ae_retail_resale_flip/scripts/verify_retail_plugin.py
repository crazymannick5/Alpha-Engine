from __future__ import annotations
import compileall
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "ae_retail_resale_flip"

FORBIDDEN = (
    "alpha_engine.persistence", "alpha_engine.db", "alpha_engine.storage",
    "sqlalchemy", "smtplib", "requests.", "httpx.",
)

def main() -> int:
    failures: list[str] = []
    if not compileall.compile_dir(str(SRC), quiet=1):
        failures.append("compileall")
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"forbidden-import:{path.relative_to(ROOT)}:{token}")
        for marker in ("TODO", "FIXME", "NotImplementedError"):
            if marker in text:
                failures.append(f"unfinished-marker:{path.relative_to(ROOT)}:{marker}")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True)
    if proc.returncode:
        failures.append(f"pytest:{proc.returncode}")
    if failures:
        print("VERIFY_FAIL")
        for item in failures: print(item)
        return 1
    print("VERIFY_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
