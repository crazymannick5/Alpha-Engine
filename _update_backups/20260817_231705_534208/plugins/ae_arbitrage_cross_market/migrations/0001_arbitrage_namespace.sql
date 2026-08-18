-- HOST-APPLIED ONLY. The plugin runtime must not open the core database directly.
-- All names are globally prefixed to preserve cylinder ownership if the host uses SQLite.
CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_relationships (
    relationship_id TEXT PRIMARY KEY,
    relationship_type TEXT NOT NULL,
    current_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_relationship_versions (
    relationship_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    spec_json_hash TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    supersedes_version INTEGER,
    evidence_manifest_ref TEXT NOT NULL,
    PRIMARY KEY (relationship_id, version)
);

CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_relationship_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    relationship_version INTEGER NOT NULL,
    input_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_json TEXT NOT NULL,
    basis_bound TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_detector_checkpoints (
    operation_id TEXT NOT NULL,
    partition_key TEXT NOT NULL,
    cursor TEXT,
    input_watermark TEXT,
    output_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (operation_id, partition_key)
);


CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_relationship_legs (
    relationship_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    leg_no INTEGER NOT NULL,
    canonical_subject_ref TEXT NOT NULL,
    canonical_instrument_ref TEXT NOT NULL,
    role TEXT NOT NULL,
    weight TEXT NOT NULL,
    quantity_unit TEXT NOT NULL,
    settlement_currency TEXT NOT NULL,
    PRIMARY KEY (relationship_id, version, leg_no)
);

CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_cost_model_profiles (
    profile_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    schema_json_hash TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    PRIMARY KEY (profile_id, version)
);

CREATE TABLE IF NOT EXISTS plugin_ae_arbitrage_cross_market_opportunity_extensions (
    canonical_opportunity_ref TEXT NOT NULL,
    extension_version INTEGER NOT NULL,
    relationship_ref TEXT NOT NULL,
    feature_snapshot_hash TEXT NOT NULL,
    paper_plan_hint_hash TEXT,
    PRIMARY KEY (canonical_opportunity_ref, extension_version)
);

CREATE INDEX IF NOT EXISTS idx_plugin_ae_arb_relationship_status
ON plugin_ae_arbitrage_cross_market_relationships(status, relationship_type);

CREATE INDEX IF NOT EXISTS idx_plugin_ae_arb_eval_rel_created
ON plugin_ae_arbitrage_cross_market_relationship_evaluations(relationship_id, relationship_version, created_at);
