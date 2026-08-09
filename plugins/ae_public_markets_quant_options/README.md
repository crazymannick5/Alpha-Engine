# ae.public_markets_quant_options

Plugin-owned implementation of the Personal Alpha Engine Public Markets / Quantitative Research / Options cylinder.

This bounded implementation includes:
- temporal security-master resolution;
- provider-neutral query/result interfaces and deterministic fixture provider;
- rights gates;
- market/fundamental/corporate-action/options normalization;
- point-in-time guards;
- split adjustment logic;
- deterministic momentum, reversal, realized-volatility and illiquidity features;
- Black-Scholes pricing/IV/Greeks plus option-chain safety checks;
- bounded point-in-time momentum research runner;
- evidence-linked signal/opportunity candidate generation;
- named scoring-feature production (no private ranking engine);
- paper action translation and deterministic quote-cross simulation primitives;
- outcome evaluation;
- host bridge and namespaced persistence protocols;
- deterministic fixtures, diagnostics, and tests.

## Ownership / integration boundary

This package owns only `plugins/ae_public_markets_quant_options/**`. It does **not** modify core contracts, plugin host, registries, scheduler, budgets, permissions, canonical persistence, ranking/Radar, paper ledger, audit, notifications, or any other cylinder.

The Central Hub must provide an adapter from its frozen PDK to `CoreHostBridge` and `PluginPersistenceScope`. Until that is frozen, this plugin can be installed/tested as domain code but must not be represented as fully host-integrated.

## Offline verification

```bash
python -m pytest -q
PYTHONPATH=src python -m ae_public_markets_quant_options.cli verify-fixture
```

No command in this package performs live brokerage execution.
