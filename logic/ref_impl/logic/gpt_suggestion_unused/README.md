
# Probabilistic + Deterministic Supplier Choice (Minimal Example)

This self-contained sketch shows how to **marry probabilistic ranking** (LLM/ML) with **deterministic rules** (declarative DSL) inside a single **order-receipt transaction**.

It assumes your existing `Customer / Order / Item / Product` models and rule engine (e.g., LogicBank-style `Rule.*` and `@on_before_flush`). We add a tiny schema bump, one ranking function, and a before-flush glue that commits a governed result with a full audit trail.

> **Flow:** Insert/Update Order (supplier fulfillment) → call `rank_suppliers` (probabilistic) → filter by rules/policy (deterministic) → set `Order.supplier_id` or mark pending → audit to `SysSupplierReq`.

## Files
- `models_min.py` – new tables: `Supplier`, `ProductSupplier`, `SysSupplierReq`.
- `rules_supplier.py` – deterministic constraints & price copy rule.
- `ranking_service.py` – stubbed probabilistic advisor (`rank_suppliers`), replace with your LLM/ML.
- `before_flush_glue.py` – transaction-time integration.
- `features/prob_supplier.feature` – Behave spec (optional).
- `features/steps/steps_prob_supplier.py` – step defs (pseudo; adapt to your engine/db fixtures).

## Quick Start
1. Drop these files into your project (or run as a standalone illustrative module).
2. Wire `models_min.py` into your metadata (SQLAlchemy) and migrate.
3. Ensure your rule engine picks up `rules_supplier.py` and `before_flush_glue.py` on startup.
4. Run the Behave test or manually insert an order with `fulfillment_mode='supplier'`.
5. Inspect `SysSupplierReq` rows and the log to see ranked candidates, rationale, and chosen supplier.

## Talking Points (for Hemant)
- **Probabilistic propose, deterministic accept**: only the ranking is probabilistic; policies/rules gate the commit.
- **Governance**: every AI suggestion is audited (`SysSupplierReq.top_n` + `reason`), explainable, and testable.
- **Safety**: timeouts fall back to `pending_sourcing`; shipping is blocked by constraint until a viable supplier exists.
- **Extensibility**: swap the stub with an MCP tool later without changing transaction semantics.

