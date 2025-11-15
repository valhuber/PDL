"""
Check Credit Use Case - Probabilistic + Deterministic Rules

This module implements credit checking with:
1. Deterministic rules: sums, formulas, constraints
2. Probabilistic rules: AI-driven supplier selection

Natural Language Specification:
1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
   - ELSE copy from Product.unit_price
"""

import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from logic.logic_discovery.ai_requests.supplier_selection import get_supplier_price_from_ai


# =============================================================================
# DETERMINISTIC RULES
# =============================================================================

# Rule 1: Constraint - Customer balance must not exceed credit_limit
Rule.constraint(validate=models.Customer,
    as_condition=lambda row: row.balance <= row.credit_limit,
    error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
)

# Rule 2: Customer balance is sum of unshipped Order amount_total
Rule.sum(derive=models.Customer.balance, as_sum_of=models.Order.amount_total,
    where=lambda row: row.date_shipped is None)  # unshipped orders only

# Rule 3: Order amount_total is sum of Item amounts
Rule.sum(derive=models.Order.amount_total, as_sum_of=models.Item.amount)

# Rule 4: Item amount is quantity * unit_price
Rule.formula(derive=models.Item.amount, as_expression=lambda row: row.quantity * row.unit_price)

# Rule 5a: Count suppliers for each product
Rule.count(derive=models.Product.count_suppliers, as_count_of=models.ProductSupplier)

# Rule 5b: Item unit_price - Conditional formula with AI integration
def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
    """
    Conditional formula: determines Item.unit_price based on supplier availability.
    - IF Product has NO suppliers → copy from Product.unit_price
    - IF Product has suppliers → call AI to compute optimal price
    """
    if row.product.count_suppliers == 0:
        logic_row.log(f"Item - Product has no suppliers, using product.unit_price")
        return row.product.unit_price
    
    # Product has suppliers - use AI to get optimal supplier price
    return get_supplier_price_from_ai(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='fastest reliable delivery while keeping costs reasonable',
        fallback='min:unit_cost'
    )

Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)


""" Summary: This implementation demonstrates probabilistic + deterministic rules integration:

DETERMINISTIC RULES (6):
1. Constraint: balance <= credit_limit
2. Sum: Customer.balance = sum(Order.amount_total) where unshipped
3. Sum: Order.amount_total = sum(Item.amount)
4. Formula: Item.amount = quantity × unit_price
5a. Count: Product.count_suppliers = count(ProductSupplier)
5b. Formula (conditional): Item.unit_price = Product.unit_price OR AI-selected price

PROBABILISTIC RULE (1):
- AI computes optimal supplier price considering cost, lead_time_days, and world conditions
- Implemented as reusable function: get_supplier_price_from_ai() in logic/ai_requests/
- Automatically introspects candidate fields from ProductSupplier model
- Graceful fallback to min:unit_cost if no API key

EXECUTION FLOW:
1. User adds Item with Product that has suppliers
2. Rule 5b (formula) checks count_suppliers
3. If count > 0: formula calls get_supplier_price_from_ai()
4. AI function creates SysSupplierReq (Request Pattern), triggers AI event
5. AI event populates audit fields (chosen_supplier_id, chosen_unit_price, reason)
6. AI function returns chosen_unit_price to formula
7. Formula sets Item.unit_price with returned value
8. Rule 4 calculates Item.amount
9. Rule 3 updates Order.amount_total
10. Rule 2 updates Customer.balance
11. Rule 1 validates credit_limit constraint

KEY PATTERNS:
- Rule.formula(calling=function) - function returns computed value
- AI as value computation - returns result, audit details in request table
- Reusable AI handlers in logic/ai_requests/ - separation of concerns
Complete audit trail maintained in SysSupplierReq table.
"""


def declare_logic():
    """
    Entry point for auto-discovery system.
    Rules are already declared at module level above.
    """
    pass
