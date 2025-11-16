"""
AI Supplier Selection - Probabilistic Rule Implementation

This module implements AI-driven supplier selection using the Request Pattern.
When an Item needs a supplier, this AI handler selects the optimal supplier
based on cost, lead time, and current world conditions.

Uses the introspection-based compute_ai_value() utility from logic/system/ai_value_computation.py
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from logic.system.ai_value_computation import compute_ai_value
from database import models
import logging

app_logger = logging.getLogger(__name__)


def declare_logic():
    """
    Declares AI supplier selection logic.
    
    This rule fires when SysSupplierReq is inserted (Request Pattern).
    AI selects optimal supplier from product's ProductSupplierList based on:
    - Unit cost
    - Lead time
    - Supplier region
    - Current world conditions (from config/ai_test_context.yaml)
    
    Results stored in:
    - chosen_supplier_id: The selected supplier
    - chosen_unit_price: The unit cost from that supplier
    - reason: AI's explanation for the choice
    - request: Full prompt sent to AI (for audit)
    - created_on: Timestamp (auto-set by model default)
    """
    
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )


def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """
    AI selects optimal supplier based on cost, lead time, and world conditions.
    
    Uses compute_ai_value() utility which automatically:
    - Discovers candidate suppliers from row.product.ProductSupplierList
    - Introspects all candidate fields (supplier_id, supplier_name, unit_cost, lead_time_days, region)
    - Introspects result columns (chosen_supplier_id, chosen_unit_price)
    - Maps AI response to result columns
    - Loads world conditions from config/ai_test_context.yaml
    - Handles fallback when no API key (selects supplier with lowest unit_cost)
    - Stores complete audit trail
    
    Args:
        row: SysSupplierReq instance being inserted
        old_row: Previous row state (None for inserts)
        logic_row: LogicRow for logging and operations
    """
    # Only process on insert
    if not logic_row.is_inserted():
        return
    
    logic_row.log(f"SysSupplierReq - AI selecting supplier for Product {row.product_id}")
    logic_row.log(f"get_supplier_price_from_ai - Product has {row.product.count_suppliers} suppliers")
    
    # Use introspection-based utility for AI value computation
    compute_ai_value(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='fastest reliable delivery while keeping costs reasonable',
        fallback='min:unit_cost'  # If no API key, select cheapest supplier
    )
    
    # Log results (chosen_supplier_id and chosen_unit_price are set by compute_ai_value)
    logic_row.log(f"SysSupplierReq - AI selected supplier ID: {row.chosen_supplier_id}, unit_price: ${row.chosen_unit_price}")
    logic_row.log(f"SysSupplierReq - Reason: {row.reason}")
