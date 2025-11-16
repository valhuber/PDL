"""
Supplier Selection AI Handler

Handles AI-powered supplier selection based on cost, lead time, and world conditions.
Uses Request Pattern with SysSupplierReq audit table.
"""

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models
import logging
import os
import json
from pathlib import Path
import yaml

app_logger = logging.getLogger("api_logic_server_app")

def declare_logic():
    """
    AI Supplier Selection Logic
    
    When SysSupplierReq is inserted:
    1. Load test context (world conditions)
    2. Gather supplier candidates from ProductSupplierList
    3. Call OpenAI API for optimal selection
    4. Store chosen_supplier_id, chosen_unit_price, and reasoning
    5. Fallback to lowest cost if API unavailable
    """
    
    def select_supplier_with_ai(row: models.SysSupplierReq, old_row: models.SysSupplierReq, logic_row: LogicRow):
        """
        AI-powered supplier selection considering cost, lead time, and world conditions
        """
        if not logic_row.is_inserted():
            return
        
        # Load test context for world conditions
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'ai_test_context.yaml'
        world_conditions = 'normal operations'
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    test_context = yaml.safe_load(f)
                    world_conditions = test_context.get('world_conditions') or 'normal operations'
                logic_row.log(f"Test context loaded: {world_conditions}")
            except Exception as e:
                logic_row.log(f"Could not load test context: {e}")
        
        # Get product and suppliers
        product = row.product
        if not product or not product.ProductSupplierList:
            logic_row.log("Error: No product or suppliers available")
            return
        
        # Build candidate list
        suppliers = []
        for ps in product.ProductSupplierList:
            suppliers.append({
                'supplier_id': ps.supplier_id,
                'supplier_name': ps.supplier.name if ps.supplier else 'Unknown',
                'unit_cost': float(ps.unit_cost) if ps.unit_cost else 0,
                'lead_time_days': ps.lead_time_days or 0,
                'region': ps.supplier.region if ps.supplier else 'Unknown'
            })
        
        logic_row.log(f"Evaluating {len(suppliers)} suppliers: {[s['supplier_name'] for s in suppliers]}")
        
        # Check for OpenAI API key
        api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
        
        if not api_key:
            # Fallback: Choose supplier with lowest cost
            chosen_supplier = min(suppliers, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = chosen_supplier['supplier_id']
            row.chosen_unit_price = chosen_supplier['unit_cost']
            row.reason = f"Fallback: No API key available, selected lowest cost supplier: {chosen_supplier['supplier_name']} (${chosen_supplier['unit_cost']})"
            logic_row.log(row.reason)
            return
        
        # Call OpenAI API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # Construct prompt
            system_prompt = """You are an intelligent supply chain optimization assistant. 
Select the best supplier based on cost, lead time, and current world conditions.
Consider trade-offs and provide clear reasoning.
Respond with JSON: {"chosen_supplier_id": <id>, "reasoning": "<explanation>"}"""
            
            user_prompt = f"""Current world conditions: {world_conditions}

Product: {product.name}

Available suppliers:
{json.dumps(suppliers, indent=2)}

Task: Select the optimal supplier considering:
1. Unit cost (lower is better)
2. Lead time (shorter is better)
3. Regional risks given current world conditions
4. Balance between cost and reliability

Respond with JSON containing:
- chosen_supplier_id: the supplier_id of the best choice
- reasoning: brief explanation of why this supplier is optimal"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            logic_row.log("Calling OpenAI API for supplier selection")
            
            completion = client.chat.completions.create(
                model='gpt-4o-2024-08-06',
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            response_content = completion.choices[0].message.content
            response_dict = json.loads(response_content)
            
            chosen_supplier_id = response_dict.get('chosen_supplier_id')
            reasoning = response_dict.get('reasoning', 'No reasoning provided')
            
            # Find the chosen supplier to get unit_cost
            chosen_supplier = next((s for s in suppliers if s['supplier_id'] == chosen_supplier_id), None)
            
            if chosen_supplier:
                row.chosen_supplier_id = chosen_supplier_id
                row.chosen_unit_price = chosen_supplier['unit_cost']
                row.reason = reasoning
                logic_row.log(f"AI selected supplier: {chosen_supplier['supplier_name']} (${chosen_supplier['unit_cost']})")
                logic_row.log(f"Reasoning: {reasoning}")
            else:
                # AI returned invalid ID - fallback
                fallback_supplier = min(suppliers, key=lambda s: s['unit_cost'])
                row.chosen_supplier_id = fallback_supplier['supplier_id']
                row.chosen_unit_price = fallback_supplier['unit_cost']
                row.reason = f"AI returned invalid supplier_id, using fallback: {fallback_supplier['supplier_name']}"
                logic_row.log(row.reason)
            
        except Exception as e:
            # Error calling API - fallback to lowest cost
            logic_row.log(f"Error calling OpenAI API: {e}")
            fallback_supplier = min(suppliers, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = fallback_supplier['supplier_id']
            row.chosen_unit_price = fallback_supplier['unit_cost']
            row.reason = f"API error, fallback to lowest cost: {fallback_supplier['supplier_name']} (${fallback_supplier['unit_cost']})"
            logic_row.log(row.reason)
        
        # Store full request for audit
        row.request = json.dumps({
            'world_conditions': world_conditions,
            'product': product.name,
            'suppliers': suppliers
        }, indent=2)
    
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=select_supplier_with_ai
    )
    
    app_logger.info("✅ AI Supplier Selection handler loaded")
