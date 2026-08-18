# Prediction Markets implementation notes

## Implemented end-to-end substrate

This overlay implements a deterministic, venue-neutral Prediction Markets cylinder substrate with:

- typed market/rule/book/trade/relation/settlement domain models;
- strict Decimal and timezone-aware serialization;
- provider adapter protocol and deterministic fixture provider;
- a real read-only Kalshi Trade API v2 adapter with network-admission enforcement, endpoint allowlisting, public market/trade routes, host-injected auth for order books, rate/auth/schema error classification, and no order submission code;
- Kalshi market, rule, order-book, trade, and settlement normalization;
- binary-complement ask derivation from YES/NO bids;
- threshold-rule parsing with explicit quality flags;
- relation math for exclusive/exhaustive/nested-threshold constraints;
- stale-book, liquidity-stress, relation-inconsistency, rule-change, and resolution-risk signal logic;
- opportunity conversion and deterministic scoring features;
- single-leg paper action translation and pure fill-policy simulation for central paper-engine integration;
- settlement state evaluation including disputed/final/void/corrected-capable DTOs;
- configuration and action-universe gating;
- persistence/checkpoint ports without direct core DB access;
- core-invoked operation handlers that submit candidates through a sink protocol;
- dashboard and CLI contribution descriptors;
- a guarded central registration adapter;
- a deterministic full reference loop proving `Data → Evidence → Analysis → Signal → Opportunity → Ranking/Review → Decision/Simulation → Outcome`.

## Deliberately not implemented as plugin-local infrastructure

The overlay does **not** create a scheduler, canonical database, signal/opportunity store, ranking engine, Radar, review system, permissions, budgets, paper ledger, audit log, notification sender, secrets store, or backup system. Those remain Central Hub authorities.

## Provider research basis checked 2026-08-07

The Kalshi implementation was aligned to current official API documentation showing:

- recommended production REST base `https://external-api.kalshi.com/trade-api/v2`;
- public `GET /markets` and `GET /markets/trades` routes;
- `GET /markets/{ticker}/orderbook` returning YES and NO bid arrays in `orderbook_fp`, with asks derived through binary complement semantics;
- separate production/demo environments.

Production promotion still requires central source-terms and credential qualification.
