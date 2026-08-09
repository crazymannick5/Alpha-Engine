from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import re
import xml.etree.ElementTree as ET

from ..contracts import (
    ActivityCandidate, ActivitySemantic, DisclosureRevisionRef, DisclosureTimes,
    EvidenceLocator, RangeMoney, ResolutionState, SourceFamily, SourceRecordKey, SubjectResolution,
)
from ..providers.base import ProviderResult
from .xmlsafe import parse_xml


SEMANTIC_BY_CODE = {
    "P": (ActivitySemantic.ACQUISITION, "POSITIVE"),
    "S": (ActivitySemantic.DISPOSITION, "NEGATIVE"),
    "A": (ActivitySemantic.ACQUISITION, "POSITIVE"),
    "D": (ActivitySemantic.DISPOSITION, "NEGATIVE"),
    "F": (ActivitySemantic.DISPOSITION, "NEGATIVE"),
    "M": (ActivitySemantic.ACQUISITION, "POSITIVE"),
    "G": (ActivitySemantic.OTHER, "NEUTRAL"),
}


def _txt(node: ET.Element, path: str) -> str | None:
    found = node.find(path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.combine(datetime.strptime(value[:10], "%Y-%m-%d").date(), time.min, tzinfo=timezone.utc)


def _accession_from_url(url: str) -> str:
    match = re.search(r"(\d{10}-\d{2}-\d{6})", url)
    return match.group(1) if match else hashlib.sha256(url.encode()).hexdigest()[:24]


class SecOwnershipNormalizer:
    parser_id = "pii.sec.ownership_xml"
    parser_version = "1.0.0"
    source_schema_version = "sec-ownership-xml"

    def normalize(self, result: ProviderResult, *, ingested_at: datetime) -> list[ActivityCandidate]:
        root = parse_xml(result.content)
        form = (_txt(root, "documentType") or "4").upper()
        accession = _accession_from_url(result.source_url)
        issuer_cik = _txt(root, "issuer/issuerCik")
        issuer_name = _txt(root, "issuer/issuerName")
        period = _date(_txt(root, "periodOfReport"))
        owner = root.find("reportingOwner")
        owner_cik = _txt(owner, "reportingOwnerId/rptOwnerCik") if owner is not None else None
        owner_name = _txt(owner, "reportingOwnerId/rptOwnerName") if owner is not None else None
        role = None
        if owner is not None:
            rel = owner.find("reportingOwnerRelationship")
            if rel is not None:
                if _txt(rel, "isDirector") == "1": role = "DIRECTOR"
                elif _txt(rel, "isOfficer") == "1": role = _txt(rel, "officerTitle") or "OFFICER"
                elif _txt(rel, "isTenPercentOwner") == "1": role = "TEN_PERCENT_OWNER"
        actor_key = f"sec:reporting-owner:{owner_cik or owner_name or 'unknown'}"
        actor = SubjectResolution(source_key=actor_key, state=ResolutionState.UNRESOLVED)
        source_record = SourceRecordKey(provider_id="sec_edgar", source_id="sec_ownership", jurisdiction_id="US", native_id=accession)
        evidence_hash = "sha256:" + hashlib.sha256(result.content).hexdigest()
        out: list[ActivityCandidate] = []
        tables = [
            ("nonDerivativeTable/nonDerivativeTransaction", False),
            ("derivativeTable/derivativeTransaction", True),
        ]
        idx = 0
        for path, derivative in tables:
            for tx in root.findall(path):
                idx += 1
                tx_date = _date(_txt(tx, "transactionDate/value")) or period
                code = _txt(tx, "transactionCoding/transactionCode")
                semantic, direction = SEMANTIC_BY_CODE.get(code or "", (ActivitySemantic.OTHER, "NEUTRAL"))
                quantity_path = "transactionAmounts/transactionShares/value" if not derivative else "transactionAmounts/transactionShares/value"
                quantity = _decimal(_txt(tx, quantity_path))
                price = _decimal(_txt(tx, "transactionAmounts/transactionPricePerShare/value"))
                title = _txt(tx, "securityTitle/value")
                quality = []
                if code not in SEMANTIC_BY_CODE:
                    quality.append("UNKNOWN_SOURCE_CODE")
                if derivative:
                    quality.append("DERIVATIVE_SECURITY")
                if tx_date is None:
                    quality.append("TRANSACTION_TIME_MISSING")
                times = DisclosureTimes(
                    transaction_at=tx_date,
                    effective_at=tx_date,
                    filing_at=ingested_at,
                    accepted_at=ingested_at,
                    published_at=ingested_at,
                    ingested_at=ingested_at,
                    source_timezone="America/New_York",
                )
                out.append(ActivityCandidate(
                    source_record=source_record,
                    source_family=SourceFamily.CORPORATE_INSIDER,
                    filing_type=form,
                    revision=DisclosureRevisionRef(source_record_key=source_record.stable_key(), revision_no=1),
                    line_key=str(idx),
                    actor=actor,
                    subject_ref=f"issuer:sec-cik:{issuer_cik}" if issuer_cik else None,
                    security_title_source=title,
                    role=role,
                    semantic=semantic,
                    source_code=code,
                    direction=direction,
                    quantity=quantity,
                    price=RangeMoney(lower=price, upper=price, currency="USD") if price is not None else None,
                    value=(RangeMoney(lower=quantity * price, upper=quantity * price, currency="USD") if quantity is not None and price is not None else None),
                    times=times,
                    evidence=EvidenceLocator(
                        artifact_hash=evidence_hash,
                        field_paths=(path,),
                        source_url=result.source_url,
                        source_label=f"SEC Form {form} {accession}",
                    ),
                    parser_id=self.parser_id,
                    parser_version=self.parser_version,
                    source_schema_version=self.source_schema_version,
                    ruleset_id=f"us.sec.form{form.lower()}@1",
                    quality_flags=tuple(quality),
                    metadata={"issuer_name": issuer_name, "owner_name": owner_name, "derivative": derivative},
                ))
        return out
