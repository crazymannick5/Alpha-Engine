from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PmqoConfig:
    max_subjects_per_run: int = 500
    max_history_rows: int = 250_000
    max_option_contracts: int = 2_000
    max_quote_age_seconds: int = 900
    momentum_threshold: Decimal = Decimal("0.05")
    iv_rv_threshold: Decimal = Decimal("0.05")
    allow_nonstandard_option_paper: bool = False

    def validate(self) -> None:
        if self.max_subjects_per_run <= 0 or self.max_subjects_per_run > 10_000:
            raise ValueError("max_subjects_per_run out of bounded range")
        if self.max_history_rows <= 0:
            raise ValueError("max_history_rows must be positive")
        if self.max_option_contracts <= 0:
            raise ValueError("max_option_contracts must be positive")
        if self.max_quote_age_seconds < 0:
            raise ValueError("max_quote_age_seconds cannot be negative")
