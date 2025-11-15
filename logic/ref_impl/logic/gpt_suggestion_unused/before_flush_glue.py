
# Transaction-time marriage: probabilistic propose → deterministic accept (+ audit).
from datetime import date, timedelta
from ranking_service import rank_suppliers

# Adapt these imports to your project
from sqlalchemy.orm import Session
from models_min import Supplier, SysSupplierReq
from logic_bank.exec_row_logic.logic_row import LogicRow  # for change access
from logic_bank.util import on_before_flush                 # decorator

def _merge_line_rankings(lines, ranker):
    # Merge per-line slates into a single slate (avg score; max eta); keep first price_estimate.
    buckets = {}  # supplier_id -> agg
    for L in lines:
        for r in ranker(**L):
            agg = buckets.setdefault(r["supplier_id"], 
                    {"supplier_id": r["supplier_id"], "score_sum":0.0, "n":0, "eta_max":0,
                     "price_estimate": r["price_estimate"], "rationales": []})
            agg["score_sum"] += r["score"]; agg["n"] += 1
            agg["eta_max"] = max(agg["eta_max"], r["eta_days"])
            agg["rationales"].append(r["rationale"])
    merged = [{
        "supplier_id": b["supplier_id"],
        "score": b["score_sum"]/b["n"] if b["n"] else 0.0,
        "eta_days": b["eta_max"],
        "price_estimate": b["price_estimate"],
        "rationale": "; ".join(b["rationales"])
    } for b in buckets.values()]
    merged.sort(key=lambda r: r["score"], reverse=True)
    return merged

@on_before_flush
def auto_supplier_assignment(session: Session, changes):
    from models import Order, Item  # adapt to your project layout

    # Detect orders needing sourcing
    orders = [o for o in changes.inserts_and_updates(Order)
              if (getattr(o, "fulfillment_mode", "stock") == "supplier" and o.supplier_id is None)]

    for o in orders:
        # Summarize order lines for the ranker
        lines = [{"product_id": i.product_id, "qty": i.quantity,
                  "need_by": o.need_by, "destination": getattr(o, "ship_to_region", None)}
                 for i in o.items]

        slate = _merge_line_rankings(lines, rank_suppliers)  # probabilistic

        # Deterministic gating against policy
        def first_viable(cands):
            for r in cands:
                sup = session.get(Supplier, r["supplier_id"])
                eta_ok = (o.need_by is None) or (date.today() + timedelta(days=r["eta_days"]) <= o.need_by)
                if sup and (not sup.embargoed) and eta_ok:
                    return r
            return None

        choice = first_viable(slate)

        # Audit regardless of outcome
        session.add(SysSupplierReq(
            order_id=o.id, request=lines, top_n=slate,
            chosen_supplier_id=choice["supplier_id"] if choice else None,
            reason=choice["rationale"] if choice else "no viable supplier"
        ))

        # Finalize (deterministic). No choice → leave unassigned; constraints will prevent ship.
        if choice:
            o.supplier_id = choice["supplier_id"]
        else:
            o.status = "pending_sourcing"
