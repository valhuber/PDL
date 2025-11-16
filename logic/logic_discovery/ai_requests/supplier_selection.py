"""
AI Supplier Selection Handler - Probabilistic Value Computation

Uses introspection-based compute_ai_value() utility to:
- Navigate product.ProductSupplierList relationship automatically
- Introspect all candidate fields (supplier_id, unit_cost, lead_time_days, etc.)
- Call OpenAI with structured prompt
- Map AI response to SysSupplierReq.chosen_supplier_id and chosen_unit_price
- Handle graceful fallback when no API key
- Store complete audit trail (request, reason, created_on)

This AI handler fires when SysSupplierReq is inserted via Request Pattern.
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models
from logic.system.ai_value_computation import compute_ai_value


def declare_logic():
    """
    Register AI supplier selection handler.
    
    Fires on SysSupplierReq insert, uses introspection-based utility
    to automatically discover candidates and compute optimal selection.
    """
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )


def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    AI selects optimal supplier based on cost, lead time, and world conditions.
    
    Uses compute_ai_value() utility which automatically:
    - Navigates row.product.ProductSupplierList to get candidates
    - Introspects ProductSupplier columns: supplier_id, supplier_name, unit_cost, lead_time_days
    - Introspects Supplier columns via relationship: name, region
    - Introspects SysSupplierReq result columns: chosen_supplier_id, chosen_unit_price
    - Maps AI response: chosen_supplier_id ← supplier_id, chosen_unit_price ← unit_cost
    - Loads world_conditions from config/ai_test_context.yaml
    - Calls OpenAI with structured prompt
    - Handles fallback: min:unit_cost when no API key
    - Stores complete audit trail
    
    Args:
        row: SysSupplierReq instance being inserted
        old_row: Previous state (None for insert)
        logic_row: LogicBank wrapper for logging and operations
    """
    # Only process on insert
    if not logic_row.is_inserted():
        return
    
    logic_row.log(f"SysSupplierReq - AI supplier selection starting")
    
    # Introspection-based AI value computation
    compute_ai_value(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='fastest reliable delivery while keeping costs reasonable, considering world conditions like supply chain disruptions',
        fallback='min:unit_cost'  # Choose cheapest if no API key
    )
    
    logic_row.log(f"SysSupplierReq - AI selection complete: supplier_id={row.chosen_supplier_id}, unit_price={row.chosen_unit_price}")
