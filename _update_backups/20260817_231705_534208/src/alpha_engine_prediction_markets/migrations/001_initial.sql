-- ae.prediction_markets plugin-owned namespace only.
-- Must be executed by the Central Hub plugin migration runner; plugin code never opens the core DB directly.
CREATE TABLE IF NOT EXISTS ae_pm_market_alias (
    alias_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    provider_market_key TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    canonical_market_ref TEXT NOT NULL,
    resolution_confidence TEXT NOT NULL,
    source_ref TEXT,
    UNIQUE(provider_id, provider_market_key, valid_from)
);
CREATE INDEX IF NOT EXISTS ix_ae_pm_market_alias_canonical ON ae_pm_market_alias(canonical_market_ref);

CREATE TABLE IF NOT EXISTS ae_pm_rule_parse (
    rule_parse_id TEXT PRIMARY KEY,
    rule_artifact_hash TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    market_ref TEXT NOT NULL,
    effective_from TEXT,
    structured_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    UNIQUE(rule_artifact_hash, parser_version)
);
CREATE INDEX IF NOT EXISTS ix_ae_pm_rule_parse_market_effective ON ae_pm_rule_parse(market_ref, effective_from);

CREATE TABLE IF NOT EXISTS ae_pm_relation (
    relation_id TEXT PRIMARY KEY,
    relation_fingerprint TEXT NOT NULL,
    version INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(relation_fingerprint, version)
);
CREATE INDEX IF NOT EXISTS ix_ae_pm_relation_status ON ae_pm_relation(status);

CREATE TABLE IF NOT EXISTS ae_pm_relation_member (
    relation_id TEXT NOT NULL,
    market_ref TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY(relation_id, market_ref, role),
    FOREIGN KEY(relation_id) REFERENCES ae_pm_relation(relation_id)
);
CREATE INDEX IF NOT EXISTS ix_ae_pm_relation_member_market ON ae_pm_relation_member(market_ref);

CREATE TABLE IF NOT EXISTS ae_pm_provider_checkpoint (
    provider_id TEXT NOT NULL,
    stream_key TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    cursor_json TEXT,
    sequence_ref TEXT,
    optimistic_version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(provider_id, stream_key)
);

CREATE TABLE IF NOT EXISTS ae_pm_qualification_projection (
    provider_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    qualified_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(provider_id, capability)
);

CREATE TABLE IF NOT EXISTS ae_pm_settlement_projection (
    market_ref TEXT PRIMARY KEY,
    current_state TEXT NOT NULL,
    evidence_fingerprint TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ae_pm_feature_cache (
    opportunity_ref TEXT NOT NULL,
    feature_provider_version TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    expires_at TEXT,
    PRIMARY KEY(opportunity_ref, feature_provider_version, input_fingerprint)
);
