"""
Credit Check Logic with AI Supplier Selection
Generated from training/template_probabilistic_rules.py
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from database import models
from logic.logic_discovery.ai_requests.supplier_selection import get_supplier_price_from_ai
from logic_bank.logic_bank import Rule


def ItemUnitPriceFromSupplier(row: models.Item, old_row, logic_row: LogicRow):
    """
    Formula to compute Item.unit_price based on supplier selection via AI.
    
    Uses LogicBank's triggered insert pattern:
    - Creates SysSupplierReq audit record using logic_row.new_logic_row()
    - Triggers supplier_id_from_ai event handler which populates chosen fields
    - Returns the chosen_unit_price from the audit record
    
    This pattern avoids "Session is already flushing" errors.
    """
    if row.product.count_suppliers == 0:
        # No suppliers available - use product price
        logic_row.log(f"Item - Product {row.product_id} has no suppliers, using product price")
        return row.product.unit_price
    
    # Product has suppliers - call AI via triggered insert pattern
    return get_supplier_price_from_ai(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='lowest cost',
        fallback='product.unit_price'
    )


# Register the formula rule
Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)

# Sum rule for Item.amount (unit_price * quantity)
Rule.formula(derive=models.Item.amount, as_expression=lambda row: row.unit_price * row.quantity)

# Aggregate rules for Order
Rule.sum(derive=models.Order.amount_total, as_sum_of=models.Item.amount)

# Constraint rule for Customer credit check
Rule.constraint(validate=models.Customer,
                as_condition=lambda row: row.balance <= row.credit_limit,
                error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})")
