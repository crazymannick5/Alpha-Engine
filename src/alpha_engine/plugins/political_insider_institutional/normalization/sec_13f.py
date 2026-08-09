from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import xml.etree.ElementTree as ET

from ..contracts import EvidenceLocator, HoldingSnapshot, SourceRecordKey
from ..providers.base import ProviderResult
from .xmlsafe import parse_xml


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ET.Element, name: str) -> str | None:
    for child in node.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _dec(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


class Sec13FNormalizer:
    parser_version = "1.0.0"

    def normalize(
        self,
        result: ProviderResult,
        *,
        manager_source_key: str,
        period_end: date,
        filing_at: datetime,
        accession: str,
    ) -> list[HoldingSnapshot]:
        root = parse_xml(result.content)
        artifact_hash = "sha256:" + hashlib.sha256(result.content).hexdigest()
        source_record = SourceRecordKey(provider_id="sec_edgar", source_id="sec_13f", jurisdiction_id="US", native_id=accession)
        out: list[HoldingSnapshot] = []
        for info in root.iter():
            if _local(info.tag) != "infoTable":
                continue
            cusip = _child_text(info, "cusip")
            name = _child_text(info, "nameOfIssuer")
            shares = _dec(_child_text(info, "sshPrnamt"))
            value_thousands = _dec(_child_text(info, "value"))
            if not cusip or shares is None:
                continue
            out.append(HoldingSnapshot(
                manager_source_key=manager_source_key,
                security_key=f"cusip:{cusip}",
                period_end=period_end,
                filing_at=filing_at,
                shares=shares,
                value_usd=(value_thousands * Decimal(1000) if value_thousands is not None else None),
                evidence=EvidenceLocator(
                    artifact_hash=artifact_hash,
                    field_paths=("infoTable",),
                    source_url=result.source_url,
                    source_label=f"SEC 13F {accession} {name or cusip}",
                ),
                source_record=source_record,
                parser_version=self.parser_version,
            ))
        return out
