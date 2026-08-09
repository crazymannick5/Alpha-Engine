# Arbitrage Cylinder File Ownership

Workstream: `PLUGIN`  
Plugin ID: `ae.arbitrage_cross_market`

This workstream owns **only** files below:

`plugins/ae_arbitrage_cross_market/`

No root project file, `src/alpha_engine/**` file, another `plugins/**` directory, central migration, central contract, dashboard shell file, CLI shell file, or provider shared-registry file is modified by this overlay.

The apply overlay is intentionally additive. If an existing repository already contains a file at any exact path in this ownership root, treat that as a collision requiring Primary Development reconciliation before applying; do not overwrite it blindly.
