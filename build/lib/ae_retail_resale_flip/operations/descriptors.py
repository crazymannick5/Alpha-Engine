from __future__ import annotations

OPERATION_DESCRIPTORS = (
    {"command":"retail.refresh_offer","idempotency":"provider+offer+request_hash+freshness_bucket","checkpoint":"provider_cursor_or_etag","retry":"transient_network_or_rate_limit","resource_class":"io"},
    {"command":"retail.scan_universe","idempotency":"universe+provider_set+config_revision+window","checkpoint":"provider_page_cursor+last_normalized_hash","retry":"page_level_transient","resource_class":"io_bounded"},
    {"command":"retail.revalue_product","idempotency":"product+comparable_manifest+model_version","checkpoint":None,"retry":"deterministic_safe","resource_class":"cpu_small"},
    {"command":"retail.qualify_provider","idempotency":"provider+adapter_version+qualification_profile","checkpoint":"qualification_stage","retry":"bounded_probe_only","resource_class":"io"},
    {"command":"retail.import_manual","idempotency":"artifact_hash+import_schema_version","checkpoint":"row_offset+batch_id","retry":"row_batch_idempotent","resource_class":"io_cpu"},
    {"command":"retail.outcome_refresh","idempotency":"opportunity_or_paper_lot+horizon+provider_set","checkpoint":"provider_page","retry":"transient_only","resource_class":"io"}
)
