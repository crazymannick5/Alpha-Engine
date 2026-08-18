from __future__ import annotations

from ..contracts import Descriptor


def cli_contributions() -> tuple[Descriptor, ...]:
    commands = (
        ("pm.providers.list", "alpha-engine pm providers list"),
        ("pm.providers.qualify", "alpha-engine pm providers qualify"),
        ("pm.markets.sync", "alpha-engine pm markets sync"),
        ("pm.market.show", "alpha-engine pm market show"),
        ("pm.rules.history", "alpha-engine pm rules history"),
        ("pm.relations.inspect", "alpha-engine pm relations inspect"),
        ("pm.detect.run", "alpha-engine pm detect run"),
        ("pm.settlement.evaluate", "alpha-engine pm settlement evaluate"),
        ("pm.fixtures.run", "alpha-engine pm fixtures run"),
        ("pm.diagnostics.export", "alpha-engine pm diagnostics export"),
        ("pm.config.validate", "alpha-engine pm config validate"),
    )
    return tuple(Descriptor(cid, "cli_command", "1", {"syntax":syntax}) for cid,syntax in commands)
