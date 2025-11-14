"""
TEMPLATE: Probabilistic + Deterministic Rules Implementation
Use this template when implementing AI-driven supplier selection (or similar decisions)

This is a working reference implementation showing the complete pattern.
Copy and adapt sections as needed for your specific use case.
"""

import datetime
import json
import os
from decimal import Decimal
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from database import models
import logging

app_logger = logging.getLogger(__name__)

def declare_logic():
    """
    TEMPLATE STRUCTURE:
    1. Deterministic guardrails (constraints)
    2. Deterministic calculations (sums, formulas)
    3. Conditional logic (decides when AI runs)
    4. AI event handler (probabilistic decision)
    """
    
    # ========================================
    # SECTION 1: DETERMINISTIC GUARDRAILS
    # ========================================
    
    Rule.constraint(
        validate=models.Customer,
        as_condition=lambda row: row.balance is None or row.credit_limit is None or row.balance <= row.credit_limit,
        error_msg="Customer balance ({row.balance}) exceeds credit limit ({row.credit_limit})"
    )
    
    # ========================================
    # SECTION 2: DETERMINISTIC CALCULATIONS
    # ========================================
    
    Rule.sum(
        derive=models.Customer.balance,
        as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None
    )
    
    Rule.sum(
        derive=models.Order.amount_total,
        as_sum_of=models.Item.amount
    )
    
    Rule.formula(
        derive=models.Item.amount,
        as_expression=lambda row: row.quantity * (row.unit_price or 0)
    )
    
    # Count suppliers for conditional logic
    Rule.count(
        derive=models.Product.count_suppliers,
        as_count_of=models.ProductSupplier,
        calling=lambda row: row.product_id == row.id
    )
    
    # ========================================
    # SECTION 3: CONDITIONAL LOGIC (When to invoke AI)
    # ========================================
    
    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """
        PATTERN: Deterministic rule decides when AI should run.
        
        Logic Flow:
        1. Check if product has suppliers
        2. If NO suppliers → use product unit_price
        3. If YES suppliers → create SysSupplierReq (triggers AI)
        """
        if row.product is None:
            return Decimal('0')
            
        if row.product.count_suppliers == 0 or row.product.count_suppliers is None:
            app_logger.debug(f"Item {row.id} - No suppliers, using product.unit_price")
            return row.product.unit_price
        
        # Product has suppliers - invoke AI via Request Pattern
        app_logger.info(f"Item {row.id} - {row.product.count_suppliers} suppliers, invoking AI")
        
        # REQUEST PATTERN: Create audit/request object
        sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
        sys_supplier_req = sys_supplier_req_logic_row.row
        sys_supplier_req_logic_row.link(to_parent=logic_row)
        sys_supplier_req.product_id = row.product_id
        sys_supplier_req.item_id = row.id
        
        # Insert triggers AI event handler below
        sys_supplier_req_logic_row.insert(reason="AI Supplier Selection Request")
        
        # Return the AI-selected price
        return sys_supplier_req.chosen_unit_price
    
    Rule.formula(
        derive=models.Item.unit_price,
        calling=ItemUnitPriceFromSupplier
    )
    
    # ========================================
    # SECTION 4: AI EVENT HANDLER (Probabilistic Decision)
    # ========================================
    
    def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
        """
        PATTERN: AI computes supplier_id value probabilistically, stores audit trail.
        
        Key Features:
        - Graceful fallback if no API key
        - Complete audit trail (request, reason, chosen values)
        - Test context from YAML file
        - Error handling with fallback
        """
        if not logic_row.is_inserted():
            return
        
        # Step 1: Get candidate suppliers
        supplier_options = []
        for ps in row.product.ProductSupplierList:
            supplier_options.append({
                'supplier_id': ps.supplier_id,
                'supplier_name': ps.supplier.name if ps.supplier else 'Unknown',
                'unit_cost': float(ps.unit_cost) if ps.unit_cost else 0.0,
                'lead_time_days': ps.lead_time_days if ps.lead_time_days else 999,
                'region': ps.supplier.region if ps.supplier else 'Unknown'
            })
        
        if not supplier_options:
            app_logger.error(f"SysSupplierReq {row.id} - No suppliers found")
            row.reason = "Error: No suppliers available"
            row.chosen_unit_price = row.product.unit_price or Decimal('0')
            return
        
        # Step 2: Check for API key
        api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
        
        if not api_key:
            # FALLBACK PATTERN: No API key → use lowest cost
            app_logger.info(f"SysSupplierReq {row.id} - No API key, fallback to lowest cost")
            chosen = min(supplier_options, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = chosen['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen['unit_cost']))
            row.reason = f"Fallback: No API key. Selected {chosen['supplier_name']} (lowest cost: ${chosen['unit_cost']})"
            row.request = f"Supplier options: {json.dumps(supplier_options, indent=2)}"
            return
        
        # Step 3: Call OpenAI with test context
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # TEST CONTEXT PATTERN: Load from config/ai_test_context.yaml
            world_conditions = 'normal operations'
            try:
                import yaml
                from pathlib import Path
                config_dir = Path(__file__).parent.parent.parent / 'config'
                context_file = config_dir / 'ai_test_context.yaml'
                if context_file.exists():
                    with open(context_file, 'r') as f:
                        test_context = yaml.safe_load(f)
                        world_conditions = test_context.get('world_conditions') or 'normal operations'
            except Exception as e:
                app_logger.debug(f"Could not load AI test context: {e}")
            
            # Construct AI prompt
            system_message = """You are a supply chain optimization assistant. 
Analyze supplier options and select the best one based on cost, lead time, and current world conditions.
Respond with JSON: {"chosen_supplier_id": <id>, "reason": "<explanation>"}"""
            
            user_context = f"""Current world conditions: {world_conditions}

Supplier options:
{json.dumps(supplier_options, indent=2)}

Task: Choose the optimal supplier considering:
1. Unit cost (lower is better)
2. Lead time (shorter is better)  
3. World conditions (e.g., if Suez Canal is blocked, avoid Near East suppliers)
4. Region and reliability

Optimize for fastest reliable delivery while keeping costs reasonable."""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_context}
            ]
            
            app_logger.debug(f"SysSupplierReq {row.id} - Calling OpenAI")
            
            completion = client.chat.completions.create(
                model='gpt-4o-2024-08-06',
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            response_text = completion.choices[0].message.content
            response_data = json.loads(response_text)
            
            chosen_id = response_data.get('chosen_supplier_id')
            ai_reason = response_data.get('reason', 'No reason provided')
            
            # Find chosen supplier
            chosen = next((s for s in supplier_options if s['supplier_id'] == chosen_id), None)
            
            if not chosen:
                app_logger.warning(f"AI chose invalid supplier {chosen_id}, using first")
                chosen = supplier_options[0]
                ai_reason = f"AI selection invalid, defaulted to {chosen['supplier_name']}"
            
            # AUDIT TRAIL: Store complete decision context
            row.chosen_supplier_id = chosen['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen['unit_cost']))
            row.reason = ai_reason
            row.request = json.dumps({
                'world_conditions': world_conditions,
                'supplier_options': supplier_options,
                'model': 'gpt-4o-2024-08-06'
            }, indent=2)
            
            app_logger.info(f"SysSupplierReq {row.id} - AI selected {chosen['supplier_name']} (${chosen['unit_cost']})")
            app_logger.info(f"  Reason: {ai_reason}")
            
        except Exception as e:
            # ERROR FALLBACK: On any error, use lowest cost
            app_logger.error(f"SysSupplierReq {row.id} - AI error: {e}, using fallback")
            chosen = min(supplier_options, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = chosen['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen['unit_cost']))
            row.reason = f"Fallback: AI error ({str(e)[:100]}). Selected {chosen['supplier_name']}"
            row.request = f"Error: {str(e)}. Options: {json.dumps(supplier_options, indent=2)}"
    
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )
    
    app_logger.info("Probabilistic + Deterministic logic loaded")


# ========================================
# KEY PATTERNS SUMMARY
# ========================================
"""
1. REQUEST PATTERN (Mandatory)
   - Create SysXxxReq table for every AI decision
   - Structure: chosen_xxx_id, chosen_xxx_price, request, reason, created_on
   - Purpose: Audit trail, governance, debugging

2. CONDITIONAL PATTERN
   - Deterministic rule decides IF/WHEN AI runs
   - Example: if count_suppliers > 0 then invoke AI else use default

3. FALLBACK PATTERN
   - No API key → Infer from optimization criteria (lowest cost, shortest time, etc.)
   - AI error → Same fallback logic
   - Always store reasoning in audit trail

4. TEST CONTEXT PATTERN
   - Store test conditions in config/ai_test_context.yaml
   - Load at runtime for reproducible testing
   - Easy to change scenarios without code changes

5. AUDIT TRAIL PATTERN
   - request: Full context sent to AI
   - reason: AI's explanation
   - chosen_xxx: The selected value(s)
   - created_on: Timestamp for tracking
"""
