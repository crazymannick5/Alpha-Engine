# ae.retail_resale_flip

Deterministic Personal Alpha Engine plugin for retail/resale opportunity research and Level-2 paper simulation support.

The plugin owns only retail-domain intelligence. It does **not** own scheduling, budgets, permissions, canonical persistence, ranking/Radar, audit, notifications, or paper ledgers. Live purchasing, listing, payment, anti-bot bypass, and scraping fallbacks are absent by design.

The current implementation is fully executable in fixture/manual-import mode. Central-host adapters are deliberately narrow and fail closed when a frozen host contract is unavailable.
