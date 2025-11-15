import datetime
from decimal import Decimal
import json
import os
from time import time
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.rule_extensions import RuleExtension
from logic_bank.logic_bank import Rule
from openai import OpenAI
from sqlalchemy import JSON
from database import models
import logging

app_logger = logging.getLogger(__name__)


def declare_logic():
    """
    Check Credit Use Case Logic
    
    Natural Language Requirements:
    1. The Customer's balance is less than the credit limit
    2. The Customer's balance is the sum of the Order amount_total where date_shipped is null
    3. The Order's amount_total is the sum of the Item amount
    4. The Item amount is the quantity * unit_price
    5. The Item unit_price is copied from the Product unit_price
    """
    
    # 1. The Customer's balance is less than the credit limit
    Rule.constraint(validate=models.Customer,
                   as_condition=lambda row: row.balance <= row.credit_limit,
                   error_msg="Customer balance exceeds credit limit")
    
    # 2. The Customer's balance is the sum of the Order amount_total where date_shipped is null
    Rule.sum(derive=models.Customer.balance, 
             as_sum_of=models.Order.amount_total,
             where=lambda row: row.date_shipped is None)
    
    # 3. The Order's amount_total is the sum of the Item amount
    Rule.sum(derive=models.Order.amount_total, 
             as_sum_of=models.Item.amount)
    
    # 4. The Item amount is the quantity * unit_price
    Rule.formula(derive=models.Item.amount, 
                 as_expression=lambda row: row.quantity * row.unit_price)
    
    ''' item.unit_price copy rule disabled - superceded by supplier rules
    # 5. The Item unit_price is copied from the Product unit_price
    Rule.copy(derive=models.Item.unit_price, 
              from_parent=models.Product.unit_price)
    '''


    # New rules for Supplier and ProductSupplier

    # count indicates products has suppliers - and we must choose one (via AI)
    Rule.count(derive=models.Product.count_suppliers, as_count_of=models.ProductSupplier)

    def ItemUnitPriceFromSupplier(row: models.Item, old_row: models.Item, logic_row: LogicRow):
        """Deterministic rule decides when AI should run."""
        if row.product.count_suppliers == 0:
            logic_row.debug(f"Item {row.id} - Product not from supplier")
            return row.product.unit_price  # No change if no supplier
        # triggered inserts - https://apilogicserver.github.io/Docs/Logic-Use/#in-logic
        logic_row.log(f"Formula ItemUnitPriceFromSupplier(): use AI to compute unit_price by inserting SysSupplierReq (request pattern) to choose supplier")
        sys_supplier_req_logic_row : models.SysSupplierReq = logic_row.new_logic_row(models.SysSupplierReq)
        sys_supplier_req = sys_supplier_req_logic_row.row
        sys_supplier_req_logic_row.link(to_parent=logic_row)
        sys_supplier_req.product_id = row.product_id
        sys_supplier_req.item_id = row.id
        # this calls choose_supplier_for_item_with_ai, 
        #      which sets chosen_supplier_id and chosen_unit_price
        sys_supplier_req_logic_row.insert(reason="Supplier Svc Request ", row=sys_supplier_req)  # triggers rules...
        return sys_supplier_req.chosen_unit_price

    Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)   # invokes the function above


    def choose_supplier_for_item_with_ai(row: models.SysSupplierReq, old_row: models.SysSupplierReq, logic_row: LogicRow):
        '''  Choose a supplier for the SysSupplierReq using AI (simulated here).
             Sets chosen_supplier_id and chosen_unit_price on the SysSupplierReq row.
             If no APIKey (use the stub out) or ai error, defaults to first candidate.
        '''
        def call_ai_service_to_choose_supplier(suppliers: list[models.ProductSupplier]) -> tuple[models.ProductSupplier, str, str]:
            # Simulate AI service call - in reality, this would call an external AI service
            return_supplier = None            
            debug_test = True  # Set True to simulate a disruption scenario
            start_time = time()
            api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
            if not api_key:
                reasoning = "Failure: no API key for AI service; defaulting to first supplier"
            else:
                client = OpenAI(api_key=api_key)
                world_conditions = 'ship aground in Suez Canal' if debug_test else ''
                supplier_options = [{'supplier_id': s.supplier_id, 'unit_cost': float(s.unit_cost), 
                                     'lead_time_days': s.lead_time_days, 'region': s.region} 
                        for s in suppliers]
                messages = [
                    {"role": "system", "content": "You are a supply chain optimization assistant that selects the best supplier based on cost, lead time, and current world conditions. You must respond with valid JSON only.  Customers are US only."},
                    {"role": "user", "content": f"Current world conditions: {world_conditions}"},
                    {"role": "user", "content": f"Supplier options: {json.dumps(supplier_options)}"},
                    {"role": "user", "content": """Respond with a JSON object containing:
                    - 'reasoning': A brief explanation of your decision process
                    - 'ai_supplier': An object with 'supplier_id', 'unit_cost', and 'lead_time_days' for your selected supplier"""}
                ]
                completion = client.chat.completions.create(
                    model='gpt-4o-2024-08-06',
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                data = completion.choices[0].message.content
                request = json.dumps(messages)
                response_dict = json.loads(data)  # Now guaranteed to be pure JSON
                
                # Extract reasoning and chosen supplier
                reasoning = response_dict.get('reasoning', 'No reasoning provided')
                ai_supplier_id = response_dict.get('ai_supplier', {}).get('supplier_id')
                
                if not ai_supplier_id:
                    reasoning = "Failure: AI response missing 'ai_supplier' field"
                else:
                    for supplier in suppliers:  # Find the selected supplier in our list
                        if supplier.supplier_id == ai_supplier_id:
                            return_supplier = supplier
                            break
                    if return_supplier is None:
                        reasoning = f"AI selected supplier {ai_supplier_id} not found in candidates, using first available"
                    
            if return_supplier is None:  # Fallback if AI selected supplier not found
                return_supplier = suppliers[0]
            return return_supplier, reasoning, request
        
        def get_supplier_options(row: models.SysSupplierReq) -> list[models.ProductSupplier]:
            # Gather supplier options for the given SysSupplierReq
            supplier_options = []
            if row.product and row.product.ProductSupplierList:
                for each_supplier in row.product.ProductSupplierList:
                    # Add supplier with region info to the suppliers list
                    supplier_with_region = each_supplier
                    supplier_with_region.region = each_supplier.supplier.region if hasattr(each_supplier.supplier, 'region') else None
                    supplier_options.append(supplier_with_region)
                    logic_row.log(f"SysSupplierReq {row.id} has supplier candidate {each_supplier.supplier_id} ")
            return supplier_options

        if logic_row.is_inserted():
            # Call AI service to choose supplier based on request and top_n
            supplier_options = get_supplier_options(row=row)
            chosen_supplier, reason, request = call_ai_service_to_choose_supplier(supplier_options)
            row.chosen_supplier_id = chosen_supplier.supplier_id
            row.chosen_unit_price = chosen_supplier.unit_cost
            row.request = request
            row.reason = reason  # audit trail for governance
            logic_row.log(f"Chosen supplier {row.chosen_supplier_id} with reason '{reason}' for SysSupplierReq {row.id}")

    Rule.early_row_event(models.SysSupplierReq, calling=choose_supplier_for_item_with_ai)

