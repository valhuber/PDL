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
from logic.system.ai_value_computation import compute_ai_value


# =============================================================================
# DETERMINISTIC RULES
# =============================================================================

# Rule 1: Constraint - Customer balance must not exceed credit_limit
Rule.constraint(
    validate=models.Customer,
    as_condition=lambda row: row.balance <= row.credit_limit,
    error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
)

# Rule 2: Customer balance is sum of unshipped Order amount_total
Rule.sum(
    derive=models.Customer.balance,
    as_sum_of=models.Order.amount_total,
    where=lambda row: row.date_shipped is None  # unshipped orders only
)

# Rule 3: Order amount_total is sum of Item amounts
Rule.sum(
    derive=models.Order.amount_total,
    as_sum_of=models.Item.amount
)

# Rule 4: Item amount is quantity * unit_price
Rule.formula(
    derive=models.Item.amount,
    as_expression=lambda row: row.quantity * row.unit_price
)

# Rule 5a: Count suppliers for each product
Rule.count(
    derive=models.Product.count_suppliers,
    as_count_of=models.ProductSupplier
)

# Rule 5b: Item unit_price - Conditional logic with early event
Rule.early_row_event(
    on_class=models.Item,
    calling=lambda row, old_row, logic_row: ItemUnitPriceFromSupplier(row, logic_row)
)

Rule.formula(
    derive=models.Item.unit_price,
    as_expression=lambda row: (
        # IF Product has suppliers, price will be set by AI handler via event
        # ELSE copy from Product.unit_price
        row.product.unit_price if row.product.count_suppliers == 0
        else row.unit_price  # Keep existing value set by AI event
    )
)


def ItemUnitPriceFromSupplier(item_row: models.Item, logic_row: LogicRow):
    """
    Create SysSupplierReq request for AI to select optimal supplier.
    The AI handler will populate chosen_supplier_id and chosen_unit_price.
    """
    # Only create request on insert and if product has suppliers
    if not logic_row.is_inserted() or item_row.product.count_suppliers == 0:
        return
    
    logic_row.log(f"Creating SysSupplierReq for AI supplier selection")
    
    # Create request object using the Request Pattern
    supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    supplier_req = supplier_req_logic_row.row
    supplier_req.item_id = item_row.id
    supplier_req.product_id = item_row.product_id
    supplier_req.request = f"Select optimal supplier for {item_row.product.name}"
    
    # Insert the request - this triggers the AI event handler
    supplier_req_logic_row.insert(reason="AI supplier selection request")
    
    # Set the item's unit_price from the AI-selected supplier
    item_row.unit_price = supplier_req.chosen_unit_price
    logic_row.log(f"Set Item.unit_price = {item_row.unit_price} from AI-selected supplier")


# =============================================================================
# PROBABILISTIC RULE - AI Event Handler
# =============================================================================

def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    AI selects optimal supplier based on cost, lead time, and world conditions.
    Uses introspection-based utility to automatically discover candidate fields.
    """
    if not logic_row.is_inserted():
        return
    
    compute_ai_value(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='fastest reliable delivery while keeping costs reasonable',
        fallback='min:unit_cost'
    )
    
    # After AI selection, update the item's unit_price
    if row.chosen_unit_price is not None and row.item is not None:
        logic_row.log(f"Setting Item.unit_price = {row.chosen_unit_price}")
        row.item.unit_price = row.chosen_unit_price


Rule.early_row_event(
    on_class=models.SysSupplierReq,
    calling=supplier_id_from_ai
)


# =============================================================================
# SUMMARY
# =============================================================================
"""
This implementation demonstrates probabilistic + deterministic rules integration:

DETERMINISTIC RULES (5):
1. Constraint: balance <= credit_limit
2. Sum: Customer.balance = sum(Order.amount_total) where unshipped
3. Sum: Order.amount_total = sum(Item.amount)
4. Formula: Item.amount = quantity × unit_price
5. Count: Product.count_suppliers = count(ProductSupplier)

PROBABILISTIC RULES (1):
- AI selects optimal supplier considering cost, lead_time_days, and world conditions
- Automatically introspects candidate fields from ProductSupplier model
- Graceful fallback to min:unit_cost if no API key

EXECUTION FLOW:
1. User adds Item with Product that has suppliers
2. Rule 5b creates SysSupplierReq request
3. AI event fires → selects supplier → sets chosen_unit_price
4. Item.unit_price updated from chosen_unit_price
5. Rule 4 calculates Item.amount
6. Rule 3 updates Order.amount_total
7. Rule 2 updates Customer.balance
8. Rule 1 validates credit_limit constraint

Complete audit trail maintained in SysSupplierReq table.
"""


def declare_logic():
    """
    Entry point for auto-discovery system.
    Rules are already declared at module level above.
    """
    pass
