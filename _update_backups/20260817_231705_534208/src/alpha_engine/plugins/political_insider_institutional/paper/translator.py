from __future__ import annotations

from decimal import Decimal

from ..contracts import OpportunityCandidate, PaperActionProposal


class PaperTranslator:
    """Produces proposals only. It never mutates a ledger or executes live money."""

    def translate(
        self,
        opportunity: OpportunityCandidate,
        *,
        canonical_instrument_ref: str,
        max_notional: Decimal = Decimal("1000"),
        horizon_days: int = 30,
    ) -> PaperActionProposal:
        if opportunity.actionability != "PAPER_ELIGIBLE":
            raise PermissionError("PII_OPPORTUNITY_NOT_PAPER_ELIGIBLE")
        if opportunity.direction not in {"LONG", "SHORT", "YES", "NO"}:
            raise ValueError("PII_PAPER_DIRECTION_UNSUPPORTED")
        if not canonical_instrument_ref:
            raise ValueError("PII_CANONICAL_INSTRUMENT_REQUIRED")
        return PaperActionProposal(
            instrument_ref=canonical_instrument_ref,
            side=opportunity.direction,
            max_notional=max_notional,
            horizon_days=horizon_days,
            source_opportunity_hash=opportunity.deterministic_hash(),
            earliest_action_at=opportunity.earliest_availability_at,
            assumptions=(
                "information available only from earliest public availability onward",
                "fills, fees, slippage, calendars, and ledger state are owned by the central paper engine",
                "proposal is hypothetical and paper-only",
            ),
        )
