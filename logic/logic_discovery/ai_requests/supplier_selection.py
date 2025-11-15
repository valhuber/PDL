"""
Supplier Selection AI Handler

Reusable function for AI-driven supplier selection based on cost, lead time,
and world conditions. Returns the selected supplier's unit price.
"""

import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from logic.system.ai_value_computation import compute_ai_value


def get_supplier_price_from_ai(
    row: models.Item,
    logic_row: LogicRow,
    candidates: str = 'product.ProductSupplierList',
    optimize_for: str = 'fastest reliable delivery while keeping costs reasonable',
    fallback: str = 'min:unit_cost'
):
    """
    Use AI to select optimal supplier and return the unit price.
    
    This function encapsulates the Request Pattern:
    1. Creates SysSupplierReq audit object
    2. Inserts it (triggers AI event handler)
    3. Returns the AI-selected unit_price
    
    All audit details (chosen_supplier_id, reason, etc.) remain in SysSupplierReq table.
    
    Args:
        row: The Item row requesting supplier selection
        logic_row: LogicRow for the Item
        candidates: Path to candidate suppliers (default: 'product.ProductSupplierList')
        optimize_for: Natural language optimization criteria
        fallback: Fallback strategy if AI unavailable (default: 'min:unit_cost')
        
    Returns:
        Decimal: The unit_price from the AI-selected supplier
    """
    logic_row.log(f"get_supplier_price_from_ai - Product has {row.product.count_suppliers} suppliers")
    
    # Create audit/request object using Request Pattern
    sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    sys_supplier_req = sys_supplier_req_logic_row.row
    sys_supplier_req_logic_row.link(to_parent=logic_row)
    sys_supplier_req.product_id = row.product_id
    sys_supplier_req.item_id = row.id
    sys_supplier_req.request = f"Select optimal supplier for {row.product.name}"
    
    # Insert triggers the AI event handler (supplier_id_from_ai)
    sys_supplier_req_logic_row.insert(reason="AI supplier selection request")
    
    # Return the computed value (audit details remain in sys_supplier_req)
    return sys_supplier_req.chosen_unit_price


# =============================================================================
# AI Event Handler - Populates audit fields
# =============================================================================

def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    AI event handler: selects optimal supplier based on cost, lead time, and world conditions.
    Populates audit fields (chosen_supplier_id, chosen_unit_price, reason) in SysSupplierReq.
    
    This is called by the LogicBank engine when SysSupplierReq is inserted.
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
    
    # All audit fields (chosen_supplier_id, chosen_unit_price, reason) are set by compute_ai_value()
    # The calling formula will read chosen_unit_price as the return value


def declare_logic():
    """
    Register AI request handler rules.
    Called by auto-discovery system.
    """
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )
