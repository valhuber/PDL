"""
Check Credit Logic - Deterministic + Probabilistic Rules

Natural Language Requirements:
1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
   - ELSE copy from Product.unit_price
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models
import logging

app_logger = logging.getLogger(__name__)


def declare_logic():
    """Declares Check Credit business logic using LogicBank declarative rules."""
    
    # 1. Constraint: Customer balance must not exceed credit_limit
    Rule.constraint(
        validate=models.Customer,
        as_condition=lambda row: row.balance <= row.credit_limit,
        error_msg="Customer balance {row.balance} exceeds credit limit {row.credit_limit}"
    )
    
    # 2. Customer balance is sum of unshipped Order amount_total
    Rule.sum(
        derive=models.Customer.balance,
        as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None  # Only unshipped orders
    )
    
    # 3. Order amount_total is sum of Item amounts
    Rule.sum(
        derive=models.Order.amount_total,
        as_sum_of=models.Item.amount
    )
    
    # 4. Item amount is quantity * unit_price
    Rule.formula(
        derive=models.Item.amount,
        as_expression=lambda row: row.quantity * row.unit_price
    )
    
    # 5a. Count suppliers for each product (used by conditional logic)
    Rule.count(
        derive=models.Product.count_suppliers,
        as_count_of=models.ProductSupplier
    )
    
    # 5b. Item unit_price - Conditional: AI if suppliers exist, else copy from Product
    
    # Register early event handler (fires BEFORE formula)
    Rule.early_row_event(
        on_class=models.Item,
        calling=lambda row, old_row, logic_row: ItemUnitPriceFromSupplier(row, logic_row)
    )
    
    # Formula that preserves AI-set value or uses default
    Rule.formula(
        derive=models.Item.unit_price,
        as_expression=lambda row: (
            row.product.unit_price if row.product.count_suppliers == 0
            else row.unit_price  # Preserve value set by event handler
        )
    )


def ItemUnitPriceFromSupplier(item_row: models.Item, logic_row: LogicRow):
    """
    Event handler that decides when to invoke AI for supplier selection.
    
    IF product has suppliers (count_suppliers > 0):
        - Create SysSupplierReq request (Request Pattern)
        - AI selects optimal supplier (fires on insert)
        - Copy AI-chosen unit_price back to Item
    ELSE:
        - Do nothing (formula will copy from Product.unit_price)
    """
    # Only process on insert
    if not logic_row.is_inserted():
        return
    
    # Check if product has suppliers
    if item_row.product.count_suppliers == 0:
        logic_row.log(f"Item {item_row.id} - Product has no suppliers, using default unit_price")
        return
    
    # Product has suppliers - invoke AI via Request Pattern
    logic_row.log(f"Item - Product has {item_row.product.count_suppliers} suppliers, invoking AI")
    
    # Create request using new_logic_row (pass CLASS not instance)
    supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    supplier_req = supplier_req_logic_row.row  # Get the instance AFTER creation
    
    # Set request context
    supplier_req.item_id = item_row.id
    supplier_req.product_id = item_row.product_id
    
    # Insert triggers AI handler (in ai_requests/supplier_selection.py)
    supplier_req_logic_row.insert(reason="AI supplier selection request")
    
    # CRITICAL: Copy AI result to target row
    item_row.unit_price = supplier_req.chosen_unit_price
    logic_row.log(f"Item - AI selected supplier, unit_price set to {item_row.unit_price}")
