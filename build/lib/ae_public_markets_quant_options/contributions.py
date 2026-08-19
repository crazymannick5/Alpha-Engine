from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardContribution:
    contribution_id: str
    title: str
    kind: str
    required_capabilities: tuple[str, ...]
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CliContribution:
    command: str
    description: str
    side_effect_class: str
    required_permission: str | None


def dashboard_contributions() -> tuple[DashboardContribution, ...]:
    return (
        DashboardContribution("pmqo.market_home", "Market Research", "screen", ("canonical.read.observation",), ("universe", "freshness", "signals", "opportunities", "data_quality")),
        DashboardContribution("pmqo.security_dossier", "Security Dossier", "panel", ("canonical.read.subject",), ("identity", "listing_history", "market_series", "fundamental_vintages", "features", "evidence")),
        DashboardContribution("pmqo.options_chain", "Options Chain", "panel", ("canonical.read.observation",), ("expiration", "strike", "right", "bid", "ask", "quote_age", "iv", "greeks", "deliverable", "quality_flags")),
        DashboardContribution("pmqo.research_results", "Quant Research Results", "screen", ("artifact.read",), ("spec_hash", "manifest", "out_of_sample_metrics", "costs", "diagnostics", "result_hash")),
        DashboardContribution("pmqo.data_quality", "Market Data Quality", "screen", ("diagnostics.read",), ("stale_quotes", "conflicts", "identity_ambiguity", "chain_gaps", "pit_violations")),
    )


def cli_contributions() -> tuple[CliContribution, ...]:
    return (
        CliContribution("pmqo status", "Show cylinder health", "READ_ONLY", None),
        CliContribution("pmqo provider qualify", "Qualify a configured provider through core operations", "OPERATION", "public_markets.acquire.provider"),
        CliContribution("pmqo data backfill", "Request bounded historical acquisition", "OPERATION", "public_markets.backfill.dataset"),
        CliContribution("pmqo research run", "Run a bounded point-in-time experiment", "OPERATION", "public_markets.run_experiment"),
        CliContribution("pmqo options surface", "Compute option IV/Greeks surface", "OPERATION", "public_markets.compute_surface"),
        CliContribution("pmqo integrity check", "Run cylinder integrity checks", "READ_ONLY", None),
    )
