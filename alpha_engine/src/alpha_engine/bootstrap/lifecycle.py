from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RuntimeAlreadyRunning(RuntimeError):
    """Raised when an active runtime already owns a profile."""


class RuntimeLeaseError(RuntimeError):
    """Raised when the runtime lease cannot be safely acquired or released."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return False
                return code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


@dataclass(slots=True)
class RuntimeLease:
    runtime_dir: Path
    profile_root: Path
    acquired: bool = False
    stale_recovered: bool = False

    @property
    def lock_path(self) -> Path:
        return self.runtime_dir / "instance.lock"

    @property
    def discovery_path(self) -> Path:
        return self.runtime_dir / "runtime.json"

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def read_discovery(self) -> dict[str, Any] | None:
        return self._read_json(self.discovery_path)

    def acquire(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        existing = self._read_json(self.lock_path)
        if existing:
            pid = int(existing.get("pid") or 0)
            if process_is_running(pid):
                raise RuntimeAlreadyRunning(
                    f"profile already owned by process {pid}: {self.profile_root}"
                )
            self.stale_recovered = True
            self.lock_path.unlink(missing_ok=True)
            self.discovery_path.unlink(missing_ok=True)
        elif self.lock_path.exists():
            # An unreadable lock is ambiguous. Do not destroy it automatically.
            raise RuntimeLeaseError(f"unreadable runtime lock: {self.lock_path}")

        payload = {
            "schema_version": 1,
            "pid": os.getpid(),
            "profile": str(self.profile_root.resolve()),
            "acquired_at": _utc_now(),
        }
        try:
            with self.lock_path.open("x", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True)
        except FileExistsError as exc:
            raise RuntimeAlreadyRunning(f"runtime lock raced for {self.profile_root}") from exc
        self.acquired = True

    def publish(self, *, port: int, session_token: str, mode: str, status: str) -> None:
        if not self.acquired:
            raise RuntimeLeaseError("runtime discovery cannot be published before lease acquisition")
        payload = {
            "schema_version": 1,
            "pid": os.getpid(),
            "profile": str(self.profile_root.resolve()),
            "host": "127.0.0.1",
            "port": int(port),
            "session_token": session_token,
            "mode": mode,
            "status": status,
            "published_at": _utc_now(),
            "stale_lock_recovered": self.stale_recovered,
        }
        tmp = self.discovery_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.discovery_path)

    def release(self) -> None:
        if not self.acquired:
            return
        lock = self._read_json(self.lock_path)
        if lock and int(lock.get("pid") or 0) not in (0, os.getpid()):
            raise RuntimeLeaseError("refusing to release a runtime lease owned by another process")
        self.discovery_path.unlink(missing_ok=True)
        self.lock_path.unlink(missing_ok=True)
        self.acquired = False
