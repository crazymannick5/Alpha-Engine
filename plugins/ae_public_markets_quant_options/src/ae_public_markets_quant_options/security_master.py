from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .errors import IdentityAmbiguous, IdentityNotFound
from .models import ExternalIdentifier, Instrument, Listing


@dataclass(slots=True)
class SecurityMaster:
    instruments: dict[str, Instrument] = field(default_factory=dict)
    listings: list[Listing] = field(default_factory=list)
    identifiers: list[ExternalIdentifier] = field(default_factory=list)

    def add_instrument(self, instrument: Instrument) -> None:
        self.instruments[instrument.subject_id] = instrument

    def add_listing(self, listing: Listing) -> None:
        if listing.subject_id not in self.instruments:
            raise IdentityNotFound(listing.subject_id)
        self.listings.append(listing)

    def add_identifier(self, identifier: ExternalIdentifier) -> None:
        if identifier.subject_id not in self.instruments:
            raise IdentityNotFound(identifier.subject_id)
        self.identifiers.append(identifier)

    def resolve_identifier(self, namespace: str, value: str, as_of: date) -> Instrument:
        matches = {
            i.subject_id
            for i in self.identifiers
            if i.namespace.upper() == namespace.upper()
            and i.value == value
            and i.active_on(as_of)
        }
        return self._one(matches, f"{namespace}:{value}@{as_of}")

    def resolve_symbol(self, symbol: str, as_of: date, venue: str | None = None, currency: str | None = None) -> Instrument:
        matches = {
            l.subject_id
            for l in self.listings
            if l.symbol.upper() == symbol.upper()
            and l.active_on(as_of)
            and (venue is None or l.venue.upper() == venue.upper())
            and (currency is None or l.currency.upper() == currency.upper())
        }
        return self._one(matches, f"symbol={symbol} venue={venue} currency={currency} as_of={as_of}")

    def listing_history(self, subject_id: str) -> tuple[Listing, ...]:
        return tuple(sorted((x for x in self.listings if x.subject_id == subject_id), key=lambda x: x.valid_from))

    def _one(self, subject_ids: set[str], description: str) -> Instrument:
        if not subject_ids:
            raise IdentityNotFound(description)
        if len(subject_ids) != 1:
            raise IdentityAmbiguous(f"{description}: {sorted(subject_ids)}")
        subject_id = next(iter(subject_ids))
        inst = self.instruments[subject_id]
        return inst
