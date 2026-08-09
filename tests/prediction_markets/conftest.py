from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DummyContext:
    operation_id: str = "op-test"
    correlation_id: str = "corr-test"
    cancelled: bool = False

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise RuntimeError("cancelled")
