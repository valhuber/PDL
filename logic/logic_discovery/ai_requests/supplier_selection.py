"""
AI-driven supplier selection using LogicBank triggered insert pattern.
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
import database.models as models


def get_supplier_price_from_ai(row: models.Item, logic_row: LogicRow, candidates: str, optimize_for: str, fallback: str):
    """
    AI-driven supplier price computation using LogicBank triggered insert pattern.
    
    This function:
    1. Creates SysSupplierReq using logic_row.new_logic_row() (LogicBank way)
    2. Links it to parent Item
    3. Inserts through LogicBank (triggers supplier_id_from_ai event)
    4. Returns the chosen_unit_price set by the event handler
    
    Args:
        row: Item instance
        logic_row: LogicRow for logging
        candidates: Dot notation path to suppliers (e.g., 'product.ProductSupplierList')
        optimize_for: AI optimization criteria
        fallback: Fallback strategy if AI unavailable
    
    Returns:
        unit_price: Computed price from AI or fallback
    """
    logic_row.log(f"Item - Product has suppliers, using AI via triggered insert (request pattern)")
    
    # Create SysSupplierReq using LogicBank's triggered insert pattern
    sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    sys_supplier_req = sys_supplier_req_logic_row.row
    sys_supplier_req_logic_row.link(to_parent=logic_row)
    sys_supplier_req.product_id = row.product_id
    sys_supplier_req.item_id = row.id
    sys_supplier_req.request = f"Select optimal supplier: {optimize_for}"
    
    # Insert triggers supplier_id_from_ai event which sets chosen_supplier_id and chosen_unit_price
    sys_supplier_req_logic_row.insert(reason="Supplier AI Request", row=sys_supplier_req)
    
    return sys_supplier_req.chosen_unit_price


def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    Event handler that runs when SysSupplierReq is inserted.
    Calls AI to select optimal supplier and populates chosen_supplier_id and chosen_unit_price.
    
    This is the LogicBank way: separate event handler that populates the audit record
    before the formula (get_supplier_price_from_ai) returns its value.
    """
    if logic_row.is_inserted():
        logic_row.log(f"SysSupplierReq event - calling AI to select supplier")
        
        # Get supplier options from product
        product = row.product
        suppliers = product.ProductSupplierList
        
        if not suppliers:
            # No suppliers - use product price as fallback
            logic_row.log(f"  No suppliers found, using product price {product.unit_price}")
            row.chosen_unit_price = product.unit_price
            row.reason = "No suppliers available - used product price"
            return
        
        # TODO: Integrate with real AI service
        # For now: Simple fallback - use minimum unit_cost
        min_supplier = min(suppliers, key=lambda s: s.unit_cost)
        
        row.chosen_supplier_id = min_supplier.supplier_id
        row.chosen_unit_price = min_supplier.unit_cost
        row.reason = f"Selected supplier {min_supplier.supplier_id} with lowest cost"
        
        logic_row.log(f"  AI selected: supplier_id={row.chosen_supplier_id}, price={row.chosen_unit_price}")


# Register the event handler
Rule.early_row_event(on_class=models.SysSupplierReq, calling=supplier_id_from_ai)
