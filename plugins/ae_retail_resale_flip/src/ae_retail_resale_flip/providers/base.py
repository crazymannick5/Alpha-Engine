from __future__ import annotations

from ..contracts import OperationContext


def require_admitted(ctx: OperationContext) -> None:
    if not ctx.admitted:
        raise PermissionError("provider execution requires central operation admission")
    if ctx.cancelled:
        raise RuntimeError("operation cancelled")
