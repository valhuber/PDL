"""
Check Credit Logic - Declarative Rules

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
    """
    Declare Check Credit business logic using LogicBank rules.
    """
    
    # Rule 1: Constraint - Customer balance must not exceed credit_limit
    Rule.constraint(validate=models.Customer,
                   as_condition=lambda row: row.balance is None or row.credit_limit is None or row.balance <= row.credit_limit,
                   error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})")
    
    # Rule 2: Customer balance is sum of unshipped Order amount_total
    Rule.sum(derive=models.Customer.balance,
             as_sum_of=models.Order.amount_total,
             where=lambda row: row.date_shipped is None)
    
    # Rule 3: Order amount_total is sum of Item amounts
    Rule.sum(derive=models.Order.amount_total,
             as_sum_of=models.Item.amount)
    
    # Rule 4: Item amount is quantity * unit_price
    Rule.formula(derive=models.Item.amount,
                 as_expression=lambda row: (row.quantity or 0) * (row.unit_price or 0))
    
    # Rule 5a: Count suppliers for each product
    Rule.count(derive=models.Product.count_suppliers,
               as_count_of=models.ProductSupplier)
    
    # Rule 5b: Item unit_price - conditional logic (IF suppliers THEN AI ELSE copy from Product)
    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """
        Deterministic rule decides when AI should run.
        IF Product has suppliers → use AI to select optimal supplier
        ELSE copy unit_price from Product
        """
        if not logic_row.is_inserted():
            return
        
        product = row.product
        if product.count_suppliers == 0:
            # No suppliers - use product's default unit_price
            logic_row.log(f"Item - Product '{product.name}' has no suppliers, using default unit_price")
            row.unit_price = product.unit_price
        else:
            # Has suppliers - invoke AI via Request Pattern
            logic_row.log(f"Item - Product '{product.name}' has {product.count_suppliers} suppliers, invoking AI")
            
            # Create SysSupplierReq using Request Pattern
            supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
            supplier_req = supplier_req_logic_row.row
            supplier_req_logic_row.link(to_parent=logic_row)
            supplier_req.product_id = row.product_id
            supplier_req.item_id = row.id
            
            # Insert triggers AI event handler which sets chosen_supplier_id and chosen_unit_price
            supplier_req_logic_row.insert(reason="AI supplier selection request")
            
            # CRITICAL: Copy AI result to target row
            row.unit_price = supplier_req.chosen_unit_price
            logic_row.log(f"Item - AI selected supplier, unit_price set to {row.unit_price}")
    
    Rule.early_row_event(on_class=models.Item, calling=ItemUnitPriceFromSupplier)
    
    app_logger.info("Check Credit Logic declared successfully")
