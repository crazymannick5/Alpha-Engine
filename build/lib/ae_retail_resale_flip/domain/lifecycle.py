from __future__ import annotations
from enum import Enum


class SignalState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"


_ALLOWED_SIGNAL = {
    SignalState.CREATED: {SignalState.ACTIVE, SignalState.INVALIDATED},
    SignalState.ACTIVE: {SignalState.WEAKENED, SignalState.EXPIRED, SignalState.INVALIDATED, SignalState.SUPERSEDED},
    SignalState.WEAKENED: {SignalState.ACTIVE, SignalState.EXPIRED, SignalState.INVALIDATED, SignalState.SUPERSEDED},
    SignalState.EXPIRED: set(),
    SignalState.INVALIDATED: set(),
    SignalState.SUPERSEDED: set(),
}


def transition_signal(current: SignalState, target: SignalState) -> SignalState:
    if target not in _ALLOWED_SIGNAL[current]:
        raise ValueError(f"invalid signal transition {current.value}->{target.value}")
    return target
