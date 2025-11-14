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
        as_count_of=models.ProductSupplier,
        calling=lambda row: row.product_id == row.id  # counting relationship
    )
    
    # 5b. Item Unit Price - Conditional Logic (Deterministic decides when AI runs)
    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """
        Deterministic rule decides when AI should run.
        If product has suppliers, use AI to choose optimal supplier.
        Otherwise, copy from product unit_price.
        """
        if row.product is None:
            return Decimal('0')
            
        if row.product.count_suppliers == 0 or row.product.count_suppliers is None:
            app_logger.debug(f"Item {row.id} - Product has no suppliers, using product.unit_price")
            return row.product.unit_price
        
        # Product has suppliers - use AI to select optimal one
        app_logger.info(f"Item {row.id} - Product has {row.product.count_suppliers} suppliers, invoking AI")
        
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
    
    # 5c. AI Event Handler - Probabilistic Supplier Selection
    def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
        """
        Probabilistic rule: Use AI to compute optimal supplier_id and unit_price.
        Falls back gracefully if API key unavailable.
        Stores complete audit trail for governance.
        """
        if not logic_row.is_inserted():
            return  # Only run on insert
        
        # Get supplier candidates from ProductSupplier relationships
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
            app_logger.error(f"SysSupplierReq {row.id} - No supplier options found for product {row.product_id}")
            row.reason = "Error: No suppliers available"
            row.chosen_unit_price = row.product.unit_price or Decimal('0')
            return
        
        # Check for API key
        api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
        
        if not api_key:
            # Graceful fallback: Choose lowest cost supplier
            app_logger.info(f"SysSupplierReq {row.id} - No API key, using fallback (lowest cost)")
            chosen_supplier = min(supplier_options, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = chosen_supplier['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen_supplier['unit_cost']))
            row.reason = f"Fallback: No API key available. Selected {chosen_supplier['supplier_name']} (lowest cost: ${chosen_supplier['unit_cost']})"
            row.request = f"Supplier options: {json.dumps(supplier_options, indent=2)}"
            return
        
        # Call OpenAI for intelligent supplier selection
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # Get world conditions from test context YAML (for testing/demos)
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
            
            app_logger.debug(f"SysSupplierReq {row.id} - Calling OpenAI API")
            
            completion = client.chat.completions.create(
                model='gpt-4o-2024-08-06',
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            response_text = completion.choices[0].message.content
            response_data = json.loads(response_text)
            
            chosen_supplier_id = response_data.get('chosen_supplier_id')
            ai_reason = response_data.get('reason', 'No reason provided')
            
            # Find the chosen supplier in options
            chosen_supplier = next((s for s in supplier_options if s['supplier_id'] == chosen_supplier_id), None)
            
            if not chosen_supplier:
                app_logger.warning(f"SysSupplierReq {row.id} - AI chose invalid supplier {chosen_supplier_id}, using first")
                chosen_supplier = supplier_options[0]
                ai_reason = f"AI selection invalid, defaulted to {chosen_supplier['supplier_name']}"
            
            # Store results
            row.chosen_supplier_id = chosen_supplier['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen_supplier['unit_cost']))
            row.reason = ai_reason
            row.request = json.dumps({
                'world_conditions': world_conditions,
                'supplier_options': supplier_options,
                'model': 'gpt-4o-2024-08-06'
            }, indent=2)
            
            app_logger.info(f"SysSupplierReq {row.id} - AI selected supplier {chosen_supplier['supplier_name']} (${chosen_supplier['unit_cost']})")
            app_logger.info(f"  Reason: {ai_reason}")
            
        except Exception as e:
            # Fallback on any error
            app_logger.error(f"SysSupplierReq {row.id} - AI call failed: {str(e)}, using fallback")
            chosen_supplier = min(supplier_options, key=lambda s: s['unit_cost'])
            row.chosen_supplier_id = chosen_supplier['supplier_id']
            row.chosen_unit_price = Decimal(str(chosen_supplier['unit_cost']))
            row.reason = f"Fallback: AI error ({str(e)[:100]}). Selected {chosen_supplier['supplier_name']} (lowest cost)"
            row.request = f"Error occurred, fallback used. Supplier options: {json.dumps(supplier_options, indent=2)}"
    
    Rule.early_row_event(
        on_class=models.SysSupplierReq,
        calling=supplier_id_from_ai
    )
    
    app_logger.info("Check Credit logic loaded: deterministic rules + probabilistic supplier selection")
