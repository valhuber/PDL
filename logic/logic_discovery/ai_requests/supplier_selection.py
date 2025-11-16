"""
Reusable AI handler for supplier selection.

This module provides the Request Pattern implementation for supplier selection,
creating audit records and returning computed prices.
"""

import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule


def get_supplier_price_from_ai(row, logic_row, candidates, optimize_for, fallback):
    """
    Create SysSupplierReq audit record and return AI-selected price.
    
    Uses LogicBank triggered insert pattern to avoid "Session is already flushing" error.
    The event handler populates audit fields during insert.
    
    Args:
        row: Item row being processed
        logic_row: LogicBank LogicRow instance
        candidates: Path to supplier list (e.g., 'product.ProductSupplierList')
        optimize_for: AI optimization criteria
        fallback: Fallback strategy (e.g., 'min:unit_cost')
        
    Returns:
        float: Chosen unit price from AI or fallback
    """
    # Create audit record using LogicBank triggered insert
    sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    sys_supplier_req = sys_supplier_req_logic_row.row
    sys_supplier_req_logic_row.link(to_parent=logic_row)
    
    # Set request context
    sys_supplier_req.product_id = row.product_id
    sys_supplier_req.item_id = row.id
    sys_supplier_req.request = f"Select optimal supplier: {fallback}"
    
    # Insert triggers event handler which populates chosen_* fields
    sys_supplier_req_logic_row.insert(reason="Supplier AI Request")
    
    # Return value populated by event handler
    return sys_supplier_req.chosen_unit_price


def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    Event handler that populates SysSupplierReq audit fields.
    
    Fires DURING insert (early_row_event), so values are available
    when the formula returns.
    
    For now uses simple fallback (lowest cost supplier).
    Future: Call actual AI service for optimization.
    """
    if not logic_row.is_inserted():
        return
    
    # Get suppliers for this product
    suppliers = row.product.ProductSupplierList
    
    if not suppliers:
        logic_row.log("No suppliers available for product")
        return
    
    # Simple fallback: choose supplier with lowest cost
    # TODO: Replace with actual AI service call
    min_supplier = min(suppliers, key=lambda s: s.unit_cost)
    
    # Populate audit fields
    row.chosen_supplier_id = min_supplier.supplier_id
    row.chosen_unit_price = min_supplier.unit_cost
    row.reason = f"Selected supplier {min_supplier.supplier_id} with lowest cost"
    
    logic_row.log(f"Supplier selection: {row.reason}")


def declare_logic():
    """
    Register event handler for auto-discovery.
    """
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )
