"""
Check Credit Logic - Deterministic + Probabilistic Rules

Natural Language Requirements:
1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total (date_shipped is null)
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price:
   - IF Product has suppliers (Product.count_suppliers > 0),
     use AI to select optimal supplier based on cost, lead time, and world conditions
     [store in SysSupplierReq]
   - ELSE copy from Product.unit_price

Implementation uses logic/system/ai_value_computation.py for introspection-based AI calls.
"""

from decimal import Decimal
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models
from logic.system.ai_value_computation import compute_ai_value

def declare_logic():
    """
    Declarative rules for Check Credit use case.
    Combines deterministic business rules with probabilistic AI decisions.
    """
    
    # 1. Credit Limit Constraint (Guardrail)
    Rule.constraint(
        validate=models.Customer,
        as_condition=lambda row: row.balance is None or row.credit_limit is None or row.balance <= row.credit_limit,
        error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
    )
    
    # 2. Customer Balance = Sum of Unshipped Orders
    Rule.sum(
        derive=models.Customer.balance,
        as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None
    )
    
    # 3. Order Total = Sum of Item Amounts
    Rule.sum(
        derive=models.Order.amount_total,
        as_sum_of=models.Item.amount
    )
    
    # 4. Item Amount = Quantity * Unit Price
    Rule.formula(
        derive=models.Item.amount,
        as_expression=lambda row: row.quantity * (row.unit_price or 0)
    )
    
    # 5a. Product.count_suppliers = Count of ProductSuppliers
    Rule.count(
        derive=models.Product.count_suppliers,
        as_count_of=models.ProductSupplier
    )
    
    # 5b. Item Unit Price - Conditional Logic (Deterministic decides when AI runs)
    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """
        Deterministic rule decides when AI should run.
        If product has suppliers, use AI to choose optimal supplier.
        Otherwise, copy from product unit_price.
        """
        if row.product is None:
            logic_row.log("Item - No product assigned, unit_price = 0")
            return Decimal('0')
            
        if row.product.count_suppliers == 0 or row.product.count_suppliers is None:
            logic_row.log("Item - Product has no suppliers, using product.unit_price")
            return row.product.unit_price
        
        # Product has suppliers - use AI to select optimal one
        logic_row.log(f"Item - Product has {row.product.count_suppliers} suppliers, invoking AI")
        
        # Create SysSupplierReq (Request Pattern for audit trail)
        sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
        sys_supplier_req = sys_supplier_req_logic_row.row
        sys_supplier_req_logic_row.link(to_parent=logic_row)
        sys_supplier_req.product_id = row.product_id
        sys_supplier_req.item_id = row.id
        
        # Insert triggers AI event handler
        sys_supplier_req_logic_row.insert(reason="Supplier AI Selection Request")
        
        return sys_supplier_req.chosen_unit_price
    
    Rule.formula(
        derive=models.Item.unit_price,
        calling=ItemUnitPriceFromSupplier
    )
    
    # 5c. AI Event Handler - Probabilistic Supplier Selection (using introspection utility)
    def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
        """
        Probabilistic rule: Use AI to compute optimal supplier_id and unit_price.
        
        Uses logic.system.ai_value_computation for introspection-based AI calls.
        Discovers: candidate fields (supplier_id, supplier_name, unit_cost, lead_time_days, region, etc.)
                  result fields (chosen_supplier_id, chosen_unit_price)
        Maps: chosen_supplier_id <- supplier_id, chosen_unit_price <- unit_cost
        """
        if not logic_row.is_inserted():
            return  # Only run on insert
        
        # Introspection-based AI value computation
        # Automatically discovers all ProductSupplier fields and maps to chosen_* columns
        compute_ai_value(
            row=row,
            logic_row=logic_row,
            candidates='product.ProductSupplierList',
            optimize_for='fastest reliable delivery while keeping costs reasonable',
            fallback='min:unit_cost'
        )
    
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )
