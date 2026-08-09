from __future__ import annotations

import xml.etree.ElementTree as ET


class UnsafeXmlError(ValueError):
    pass


def parse_xml(payload: bytes, *, max_bytes: int = 10_000_000) -> ET.Element:
    if len(payload) > max_bytes:
        raise UnsafeXmlError("PII_XML_OVERSIZE")
    head = payload[:100_000].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise UnsafeXmlError("PII_XML_DTD_ENTITY_BLOCKED")
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise UnsafeXmlError(f"PII_PARSE_STRUCTURAL:{exc}") from exc
