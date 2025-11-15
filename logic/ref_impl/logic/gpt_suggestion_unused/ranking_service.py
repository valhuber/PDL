
# Probabilistic advisor stub.
# Swap contents with an LLM/ML-backed implementation or an MCP tool.
from datetime import date

def rank_suppliers(product_id: int, qty: int, need_by, destination: str):
    """Return list sorted best→worst:
    [{supplier_id, score, eta_days, price_estimate, rationale}]
    This is intentionally *probabilistic*: it blends KPIs + external signals (e.g., Suez closure).
    """
    # Demo stub — pretend supplier 2 is delayed by Suez; supplier 1 is local & stable.
    slate = [
        {"supplier_id": 1, "score": 0.92, "eta_days": 7,  "price_estimate": 19.50, "rationale": "nearby port; stable lanes"},
        {"supplier_id": 2, "score": 0.90, "eta_days": 21, "price_estimate": 17.80, "rationale": "Suez route delay; cheaper"},
    ]
    slate.sort(key=lambda r: r["score"], reverse=True)
    return slate
