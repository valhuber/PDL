
# Deterministic rules — replace 'Rule' with your engine's DSL entry points.
# Assumes existing mapped classes: Order, Item, ProductSupplier, Supplier

from logic_bank.rule_base import Rule  # adapt import to your project

# Require a supplier for supplier-fulfilled orders before shipping
Rule.constraint(
    validate="Order",
    as_condition=lambda o: (getattr(o, "fulfillment_mode", "stock") != "supplier")
                           or (o.supplier_id is not None)
                           or (o.date_shipped is None),
    error_msg="Supplier required for supplier-fulfilled orders."
)

# Never allow embargoed suppliers
Rule.constraint(
    validate="Order",
    as_condition=lambda o: (o.supplier is None) or (o.supplier.embargoed is False),
    error_msg="Chosen supplier is embargoed by policy."
)

# If a supplier is set, price Items from the supplier's latest quote
Rule.copy(
    derive="Item.unit_price",
    from_="ProductSupplier.last_quote",
    where=lambda i, ps: (i.order.supplier_id == ps.supplier_id) and (i.product_id == ps.product_id)
)
