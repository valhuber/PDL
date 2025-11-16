"""
AI Supplier Selection Handler

Reusable AI handler implementing the Request Pattern for supplier selection.
Uses OpenAI to select optimal supplier based on cost, lead time, and world conditions.
"""

import datetime
import json
import os
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from openai import OpenAI
from database import models
import logging
import yaml
from pathlib import Path

app_logger = logging.getLogger(__name__)


def choose_supplier_with_ai(row: models.SysSupplierReq, old_row: models.SysSupplierReq, logic_row: LogicRow):
    """
    AI selects optimal supplier based on cost, lead time, and world conditions.
    
    Uses OpenAI API to make intelligent supplier selection considering:
    - Unit cost
    - Lead time in days
    - Supplier region
    - Current world conditions (from config/ai_test_context.yaml)
    
    Falls back to lowest cost supplier if API key missing or error occurs.
    """
    if not logic_row.is_inserted():
        return
    
    # Load test context for world conditions
    try:
        config_path = Path(__file__).parent.parent.parent / 'config' / 'ai_test_context.yaml'
        with open(config_path, 'r') as f:
            test_context = yaml.safe_load(f)
        world_conditions = test_context.get('world_conditions') or 'normal operations'
        logic_row.log(f"Test context loaded: {world_conditions}")
    except Exception as e:
        world_conditions = 'normal operations'
        app_logger.warning(f"Could not load test context: {e}")
    
    # Get supplier options from ProductSupplierList
    product = row.product
    suppliers = list(product.ProductSupplierList)
    
    if not suppliers:
        logic_row.log("ERROR: No suppliers found for product")
        raise ValueError(f"No suppliers available for product {product.name}")
    
    # Build candidate list
    supplier_options = []
    for ps in suppliers:
        supplier_options.append({
            'supplier_id': ps.supplier_id,
            'supplier_name': ps.supplier.name,
            'unit_cost': float(ps.unit_cost),
            'lead_time_days': ps.lead_time_days,
            'region': ps.supplier.region
        })
    
    # Store request for audit trail
    row.request = json.dumps({
        'product': product.name,
        'world_conditions': world_conditions,
        'supplier_options': supplier_options
    }, indent=2)
    
    # Try AI selection
    api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
    
    if not api_key:
        # Fallback: choose lowest cost supplier
        chosen = min(suppliers, key=lambda s: s.unit_cost)
        row.chosen_supplier_id = chosen.supplier_id
        row.chosen_unit_price = chosen.unit_cost
        row.reason = "Fallback: no API key available, using lowest cost supplier"
        logic_row.log(f"No API key - fallback to lowest cost: {chosen.supplier.name} @ {chosen.unit_cost}")
        return
    
    try:
        # Call OpenAI API
        logic_row.log("Calling OpenAI API for selection")
        client = OpenAI(api_key=api_key)
        
        messages = [
            {"role": "system", "content": "You are a supply chain optimization assistant that selects the best supplier based on cost, lead time, and current world conditions. You must respond with valid JSON only. Customers are US only."},
            {"role": "user", "content": f"Current world conditions: {world_conditions}"},
            {"role": "user", "content": f"Supplier options: {json.dumps(supplier_options, indent=2)}"},
            {"role": "user", "content": "Select the optimal supplier optimizing for fastest reliable delivery while keeping costs reasonable. Respond with JSON: {\"reasoning\": \"your explanation\", \"chosen_supplier_id\": selected_id}"}
        ]
        
        completion = client.chat.completions.create(
            model='gpt-4o-2024-08-06',
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        # Parse AI response
        response_data = json.loads(completion.choices[0].message.content)
        reasoning = response_data.get('reasoning', 'No reasoning provided')
        ai_supplier_id = response_data.get('chosen_supplier_id')
        
        # Find the chosen supplier
        chosen = None
        for ps in suppliers:
            if ps.supplier_id == ai_supplier_id:
                chosen = ps
                break
        
        if chosen is None:
            # AI returned invalid ID - fallback
            chosen = min(suppliers, key=lambda s: s.unit_cost)
            reasoning = f"AI selected invalid supplier ID {ai_supplier_id}, using fallback (lowest cost)"
            logic_row.log(f"AI error - invalid supplier ID: {ai_supplier_id}")
        
        row.chosen_supplier_id = chosen.supplier_id
        row.chosen_unit_price = chosen.unit_cost
        row.reason = reasoning
        logic_row.log(f"Set chosen_supplier_id = {row.chosen_supplier_id}")
        logic_row.log(f"Set chosen_unit_price = {row.chosen_unit_price}")
        
    except Exception as e:
        # Error calling AI - fallback to lowest cost
        app_logger.error(f"AI selection error: {e}")
        chosen = min(suppliers, key=lambda s: s.unit_cost)
        row.chosen_supplier_id = chosen.supplier_id
        row.chosen_unit_price = chosen.unit_cost
        row.reason = f"AI error: {str(e)}, using fallback (lowest cost)"
        logic_row.log(f"AI exception - fallback to lowest cost: {chosen.supplier.name}")


def declare_logic():
    """Register AI supplier selection event handler"""
    Rule.early_row_event(on_class=models.SysSupplierReq, calling=choose_supplier_with_ai)
    app_logger.info("AI Supplier Selection logic declared successfully")
