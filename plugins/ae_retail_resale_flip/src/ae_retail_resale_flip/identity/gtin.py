from __future__ import annotations


def normalize_gtin(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) not in (8, 12, 13, 14):
        raise ValueError("GTIN must contain 8, 12, 13, or 14 digits")
    if not validate_gtin(digits):
        raise ValueError("GTIN check digit invalid")
    return digits.zfill(14)


def validate_gtin(digits: str) -> bool:
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return False
    body, check = digits[:-1], int(digits[-1])
    total = 0
    for idx, ch in enumerate(reversed(body), start=1):
        total += int(ch) * (3 if idx % 2 == 1 else 1)
    return ((10 - (total % 10)) % 10) == check
