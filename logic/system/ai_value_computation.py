"""
AI Value Computation Utilities - Introspection-based helper for probabilistic rules.

Provides compute_ai_value() function that uses SQLAlchemy introspection to:
- Discover candidate objects from relationships
- Serialize all candidate attributes automatically
- Call OpenAI with structured prompts
- Map AI responses back to request table columns
- Handle fallbacks gracefully (no API key, errors)
- Load test context from YAML
- Maintain complete audit trail

Convention: Request tables follow SysXxxReq pattern with chosen_* columns.
Example: SysSupplierReq has chosen_supplier_id, chosen_unit_price
         These map to supplier_id, unit_cost from ProductSupplier candidates.

You typically do not alter this file.
"""

import json
import os
from decimal import Decimal
from typing import Any, List, Dict, Optional
from pathlib import Path
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import ColumnProperty
from logic_bank.exec_row_logic.logic_row import LogicRow
import logging

app_logger = logging.getLogger(__name__)


def compute_ai_value(
    row: Any,
    logic_row: LogicRow,
    candidates: str,
    optimize_for: str,
    fallback: str = 'first',
    test_context_path: Optional[str] = None
) -> None:
    """
    Compute AI-selected value from candidate objects using introspection.
    
    Automatically discovers:
    - Candidate objects via relationship path (e.g., 'product.ProductSupplierList')
    - All candidate attributes via SQLAlchemy column introspection
    - Result columns via chosen_* prefix in request table
    - Field mappings via naming conventions (chosen_supplier_id -> supplier_id)
    
    Args:
        row: Request table row (e.g., SysSupplierReq instance)
        logic_row: LogicRow for logging and database operations
        candidates: Dot-notation path to candidate list (e.g., 'product.ProductSupplierList')
        optimize_for: Natural language optimization criteria for AI prompt
        fallback: Strategy when no API key ('first', 'min:field_name', 'max:field_name')
        test_context_path: Optional path to ai_test_context.yaml (defaults to config/ai_test_context.yaml)
    
    Returns:
        None (modifies row in place, setting chosen_* fields, request, reason, created_on)
    
    Example:
        compute_ai_value(
            row=sys_supplier_req,
            logic_row=logic_row,
            candidates='product.ProductSupplierList',
            optimize_for='fastest reliable delivery, reasonable cost',
            fallback='min:unit_cost'
        )
        # Sets: sys_supplier_req.chosen_supplier_id, chosen_unit_price, request, reason
    """
    
    logic_row.log(f"AI value computation starting for {row.__class__.__name__}")
    
    # 1. Get candidate objects via relationship path navigation
    candidate_list = _get_candidates(row, candidates, logic_row)
    if not candidate_list:
        logic_row.log(f"No candidates found at {candidates}")
        row.reason = f"Error: No candidates available at {candidates}"
        return
    
    logic_row.log(f"Found {len(candidate_list)} candidates")
    
    # 2. Serialize all candidate attributes via introspection
    # Discovers: supplier_id, supplier_name, unit_cost, lead_time_days, region, etc.
    serialized_candidates = _serialize_candidates(candidate_list, logic_row)
    
    # 3. Introspect request table to find chosen_* columns
    # Discovers: chosen_supplier_id, chosen_unit_price from row's columns
    result_columns = _get_result_columns(row)
    logic_row.log(f"Result columns to populate: {', '.join(result_columns.keys())}")
    
    # 4. Check for API key
    api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
    
    if not api_key:
        logic_row.log("No API key found, using fallback strategy")
        _apply_fallback(row, serialized_candidates, result_columns, fallback, logic_row)
        return
    
    # 5. Load test context from YAML (for demos/testing)
    world_conditions = _load_test_context(test_context_path, logic_row)
    
    # 6. Call OpenAI with structured prompt
    try:
        _call_openai(
            row=row,
            logic_row=logic_row,
            candidates=serialized_candidates,
            result_columns=result_columns,
            optimize_for=optimize_for,
            world_conditions=world_conditions,
            api_key=api_key
        )
    except Exception as e:
        logic_row.log(f"AI call failed: {str(e)}, using fallback")
        _apply_fallback(row, serialized_candidates, result_columns, fallback, logic_row)


def _get_candidates(row: Any, candidates_path: str, logic_row: LogicRow) -> List[Any]:
    """
    Navigate relationship path to get candidate objects.
    
    Example: 'product.ProductSupplierList' navigates row.product.ProductSupplierList
    """
    parts = candidates_path.split('.')
    current = row
    
    for part in parts:
        if not hasattr(current, part):
            logic_row.log(f"Path navigation failed at '{part}' in {candidates_path}")
            return []
        current = getattr(current, part)
        if current is None:
            logic_row.log(f"Null value encountered at '{part}' in {candidates_path}")
            return []
    
    if not isinstance(current, list):
        return [current] if current else []
    
    return current


def _serialize_candidates(candidate_list: List[Any], logic_row: LogicRow) -> List[Dict[str, Any]]:
    """
    Serialize candidate objects to JSON-friendly dicts via introspection.
    
    Discovers all scalar columns (id, name, cost, etc.) and related entity attributes.
    Example output: [{'supplier_id': 1, 'supplier_name': 'Acme', 'unit_cost': 10.5, ...}, ...]
    """
    if not candidate_list:
        return []
    
    # Introspect first candidate's model to get columns
    first_candidate = candidate_list[0]
    mapper = sa_inspect(first_candidate.__class__)
    
    # Get scalar columns: id, supplier_id, unit_cost, lead_time_days, etc.
    scalar_columns = [
        col.key for col in mapper.column_attrs
        if isinstance(col, ColumnProperty)
    ]
    
    serialized = []
    for candidate in candidate_list:
        candidate_dict = {}
        
        # Add scalar attributes
        for col_name in scalar_columns:
            value = getattr(candidate, col_name, None)
            # Convert Decimal to float for JSON serialization
            if isinstance(value, Decimal):
                value = float(value)
            candidate_dict[col_name] = value
        
        # Add related entity attributes (e.g., supplier.name, supplier.region)
        for relationship in mapper.relationships:
            related_obj = getattr(candidate, relationship.key, None)
            if related_obj and not isinstance(related_obj, list):
                # Get name and other key attributes from related entity
                for attr in ['name', 'region', 'code', 'status']:
                    if hasattr(related_obj, attr):
                        related_value = getattr(related_obj, attr, None)
                        candidate_dict[f"{relationship.key}_{attr}"] = related_value
        
        serialized.append(candidate_dict)
    
    # Log sample fields for readability
    if serialized:
        sample_fields = ', '.join(list(serialized[0].keys())[:5])
        logic_row.log(f"Serialized candidate fields: {sample_fields}, ...")
    
    return serialized


def _get_result_columns(row: Any) -> Dict[str, str]:
    """
    Introspect request table to find chosen_* columns and map to candidate fields.
    
    Example: chosen_supplier_id -> supplier_id, chosen_unit_price -> unit_cost/unit_price
    Returns: {'chosen_supplier_id': 'supplier_id', 'chosen_unit_price': 'unit_cost'}
    """
    mapper = sa_inspect(row.__class__)
    result_columns = {}
    
    for col in mapper.column_attrs:
        col_name = col.key
        if col_name.startswith('chosen_'):
            # Strip 'chosen_' prefix to get target field
            # chosen_supplier_id -> supplier_id
            # chosen_unit_price -> unit_price (will try unit_cost as well)
            target_field = col_name.replace('chosen_', '')
            result_columns[col_name] = target_field
    
    return result_columns


def _load_test_context(test_context_path: Optional[str], logic_row: LogicRow) -> str:
    """
    Load AI test context from YAML file.
    
    Defaults to config/ai_test_context.yaml if not specified.
    Returns 'normal operations' if file not found or no world_conditions set.
    """
    if test_context_path is None:
        # Default path: config/ai_test_context.yaml relative to project root
        config_dir = Path(__file__).parent.parent.parent / 'config'
        test_context_path = str(config_dir / 'ai_test_context.yaml')
    
    try:
        import yaml
        if Path(test_context_path).exists():
            with open(test_context_path, 'r') as f:
                test_context = yaml.safe_load(f)
                world_conditions = test_context.get('world_conditions')
                if world_conditions:
                    logic_row.log(f"Test context loaded: {world_conditions}")
                    return world_conditions
    except Exception as e:
        logic_row.log(f"Could not load test context: {e}")
    
    return 'normal operations'


def _apply_fallback(
    row: Any,
    candidates: List[Dict[str, Any]],
    result_columns: Dict[str, str],
    fallback_strategy: str,
    logic_row: LogicRow
) -> None:
    """
    Apply fallback selection strategy when API key unavailable or AI call fails.
    
    Strategies:
    - 'first': Choose first candidate
    - 'min:field': Choose candidate with minimum value for field
    - 'max:field': Choose candidate with maximum value for field
    """
    if not candidates:
        row.reason = "Fallback failed: No candidates available"
        return
    
    # Parse strategy
    if fallback_strategy == 'first':
        chosen = candidates[0]
        reason = f"Fallback: No API key. Selected first candidate"
    elif fallback_strategy.startswith('min:'):
        field = fallback_strategy.split(':', 1)[1]
        chosen = min(candidates, key=lambda c: c.get(field, float('inf')))
        reason = f"Fallback: No API key. Selected minimum {field} ({chosen.get(field)})"
    elif fallback_strategy.startswith('max:'):
        field = fallback_strategy.split(':', 1)[1]
        chosen = max(candidates, key=lambda c: c.get(field, float('-inf')))
        reason = f"Fallback: No API key. Selected maximum {field} ({chosen.get(field)})"
    else:
        chosen = candidates[0]
        reason = f"Fallback: Unknown strategy '{fallback_strategy}', used first"
    
    logic_row.log(reason)
    
    # Map chosen candidate fields to result columns
    _map_result_fields(row, chosen, result_columns, logic_row)
    
    row.reason = reason
    row.request = json.dumps({'candidates': candidates, 'strategy': fallback_strategy}, indent=2)


def _call_openai(
    row: Any,
    logic_row: LogicRow,
    candidates: List[Dict[str, Any]],
    result_columns: Dict[str, str],
    optimize_for: str,
    world_conditions: str,
    api_key: str
) -> None:
    """
    Call OpenAI API to select optimal candidate based on criteria.
    
    Constructs structured prompt with candidates and optimization criteria.
    Parses JSON response and maps chosen fields to result columns.
    """
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # Construct system message
    system_message = """You are an intelligent selection assistant.
Analyze the candidate options and select the best one based on the optimization criteria and current conditions.
Respond with JSON matching this structure: {"chosen_index": <0-based index>, "reason": "<explanation>"}"""
    
    # Construct user context
    user_context = f"""Current conditions: {world_conditions}

Candidate options:
{json.dumps(candidates, indent=2)}

Optimization criteria: {optimize_for}

Task: Choose the optimal candidate considering all factors. Respond with the index (0-based) of your chosen candidate and explain your reasoning."""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_context}
    ]
    
    logic_row.log("Calling OpenAI API for selection")
    
    completion = client.chat.completions.create(
        model='gpt-4o-2024-08-06',
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7
    )
    
    response_text = completion.choices[0].message.content
    response_data = json.loads(response_text)
    
    chosen_index = response_data.get('chosen_index', 0)
    ai_reason = response_data.get('reason', 'No reason provided')
    
    # Validate index
    if chosen_index < 0 or chosen_index >= len(candidates):
        logic_row.log(f"AI chose invalid index {chosen_index}, using first candidate")
        chosen_index = 0
        ai_reason = f"AI selection invalid (index {chosen_index}), defaulted to first. Original reason: {ai_reason}"
    
    chosen = candidates[chosen_index]
    
    logic_row.log(f"AI selected candidate {chosen_index}: {ai_reason[:100]}")
    
    # Map chosen candidate fields to result columns
    _map_result_fields(row, chosen, result_columns, logic_row)
    
    row.reason = ai_reason
    row.request = json.dumps({
        'world_conditions': world_conditions,
        'candidates': candidates,
        'optimize_for': optimize_for,
        'model': 'gpt-4o-2024-08-06'
    }, indent=2)


def _map_result_fields(
    row: Any,
    chosen: Dict[str, Any],
    result_columns: Dict[str, str],
    logic_row: LogicRow
) -> None:
    """
    Map chosen candidate fields to request table result columns.
    
    Handles naming variations:
    - chosen_unit_price can map to unit_cost or unit_price
    - chosen_supplier_id maps to supplier_id
    
    Example: chosen_supplier_id=1, chosen_unit_price=10.5 from supplier_id, unit_cost
    """
    for result_col, target_field in result_columns.items():
        value = None
        
        # Direct match
        if target_field in chosen:
            value = chosen[target_field]
        # Try variations: unit_price -> unit_cost
        elif target_field.replace('_price', '_cost') in chosen:
            value = chosen[target_field.replace('_price', '_cost')]
        elif target_field.replace('_cost', '_price') in chosen:
            value = chosen[target_field.replace('_cost', '_price')]
        
        if value is not None:
            # Convert to Decimal for price/cost fields, keep integers as integers for ID fields
            if isinstance(value, (int, float)):
                if '_id' in result_col or result_col.endswith('_id'):
                    value = int(value)  # Keep ID fields as integers
                elif '_price' in result_col or '_cost' in result_col or '_amount' in result_col:
                    value = Decimal(str(value))  # Convert monetary fields to Decimal
                # else: keep as-is for other numeric fields
            setattr(row, result_col, value)
            logic_row.log(f"Set {result_col} = {value}")
        else:
            logic_row.log(f"Warning: Could not map {target_field} to {result_col}")
