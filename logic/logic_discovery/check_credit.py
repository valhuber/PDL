"""
Check Credit Logic - Declarative Rules with Probabilistic AI Supplier Selection

Natural Language Requirements:
1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
   - ELSE copy from Product.unit_price

Generated: Auto-generated from natural language by GitHub Copilot
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models


def declare_logic():
    """
    Declarative rules for Check Credit use case.
    
    Combines deterministic rules (sums, formulas, constraints) with 
    probabilistic AI value computation (supplier selection).
    """
    
    # =========================================================================
    # Rule 1: Constraint - Customer balance must not exceed credit_limit
    # =========================================================================
    Rule.constraint(
        validate=models.Customer,
        as_condition=lambda row: row.balance is None or row.credit_limit is None or row.balance <= row.credit_limit,
        error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
    )
    
    # =========================================================================
    # Rule 2: Customer balance is sum of unshipped Order amount_total
    # =========================================================================
    Rule.sum(
        derive=models.Customer.balance,
        as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None  # Only unshipped orders
    )
    
    # =========================================================================
    # Rule 3: Order amount_total is sum of Item amounts
    # =========================================================================
    Rule.sum(
        derive=models.Order.amount_total,
        as_sum_of=models.Item.amount
    )
    
    # =========================================================================
    # Rule 4: Item amount is quantity * unit_price
    # =========================================================================
    Rule.formula(
        derive=models.Item.amount,
        as_expression=lambda row: row.quantity * (row.unit_price or 0)
    )
    
    # =========================================================================
    # Rule 5a: Count suppliers for Product (needed for conditional logic)
    # =========================================================================
    Rule.count(
        derive=models.Product.count_suppliers,
        as_count_of=models.ProductSupplier
    )
    
    # =========================================================================
    # Rule 5b: Item unit_price - Conditional AI vs. Default
    # =========================================================================
    
    # Early event handler - fires BEFORE formula to invoke AI if needed
    Rule.early_row_event(
        on_class=models.Item,
        calling=lambda row, old_row, logic_row: ItemUnitPriceFromSupplier(row, logic_row)
    )
    
    # Formula that preserves AI-set value or uses default from Product
    Rule.formula(
        derive=models.Item.unit_price,
        as_expression=lambda row: (
            row.product.unit_price if row.product.count_suppliers == 0
            else row.unit_price  # Preserve value set by event handler (AI or None initially)
        )
    )


def ItemUnitPriceFromSupplier(item_row: models.Item, logic_row: LogicRow):
    """
    Conditional AI logic: IF product has suppliers THEN use AI ELSE skip.
    
    When product has suppliers:
    1. Creates SysSupplierReq using Request Pattern
    2. AI handler fires on insert, sets chosen_supplier_id and chosen_unit_price
    3. Copies AI result back to item_row.unit_price
    4. Formula (above) preserves this AI-computed value
    
    When product has no suppliers:
    - Skips AI, lets formula copy from Product.unit_price
    
    Args:
        item_row: The Item being inserted/updated
        logic_row: LogicBank's wrapper with .new_logic_row(), .log() methods
    """
    # Only process on insert, skip if no suppliers
    if not logic_row.is_inserted():
        return
    
    if item_row.product.count_suppliers == 0:
        logic_row.log(f"Item - Product has no suppliers, using default unit_price")
        return
    
    logic_row.log(f"Item - Product has {item_row.product.count_suppliers} suppliers, invoking AI")
    
    # CRITICAL PATTERN: Pass CLASS to new_logic_row (not instance)
    supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    supplier_req = supplier_req_logic_row.row  # Get instance AFTER creation
    
    # Set request context (links to Item and Product)
    supplier_req.item_id = item_row.id
    supplier_req.product_id = item_row.product_id
    
    # Insert triggers AI handler (see ai_requests/supplier_selection.py)
    supplier_req_logic_row.insert(reason="AI supplier selection request")
    
    # CRITICAL: Copy AI result to target row
    # (AI populated SysSupplierReq.chosen_unit_price, now copy to Item.unit_price)
    item_row.unit_price = supplier_req.chosen_unit_price
    logic_row.log(f"Item - AI selected supplier, unit_price set to {item_row.unit_price}")
