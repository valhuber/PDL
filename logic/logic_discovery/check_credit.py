"""
Deterministic + Probabilistic Rules for PDL Demo

This module demonstrates conditional logic that uses AI when appropriate.
"""

import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from logic.logic_discovery.ai_requests.supplier_selection import get_supplier_price_from_ai


def declare_logic():
    """
    Declare business rules combining deterministic and probabilistic logic.
    """
    
    # ========================================
    # DETERMINISTIC RULES
    # ========================================
    
    # Rule 1: Customer balance constraint
    Rule.constraint(
        validate=models.Customer,
        as_condition=lambda row: row.balance <= row.credit_limit,
        error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
    )
    
    # Rule 2: Customer balance is sum of unshipped orders
    Rule.sum(
        derive=models.Customer.balance,
        as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None
    )
    
    # Rule 3: Order amount_total is sum of item amounts
    Rule.sum(
        derive=models.Order.amount_total,
        as_sum_of=models.Item.amount
    )
    
    # Rule 4: Item amount formula
    Rule.formula(
        derive=models.Item.amount,
        as_expression=lambda row: row.quantity * row.unit_price
    )
    
    # Rule 5a: Count suppliers for each product
    Rule.count(
        derive=models.Product.count_suppliers,
        as_count_of=models.ProductSupplier
    )
    
    # ========================================
    # CONDITIONAL FORMULA WITH AI
    # ========================================
    
    # Rule 5b: Item unit_price - Conditional formula with AI integration
    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """
        Determine Item.unit_price based on supplier availability:
        - IF Product has NO suppliers → use product.unit_price (deterministic)
        - IF Product has suppliers → call AI to select optimal supplier (probabilistic)
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
