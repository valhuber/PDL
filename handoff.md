# Probabilistic Rules Design Session - Handoff Document

**Date:** November 13-14, 2025  
**Project:** GenAI Demo Agentic Runtime - Probabilistic Rules via Natural Language  
**Status:** Design complete, documentation updated, ready for implementation

---

## What We Accomplished

### 1. Created the "Rosetta Stone for Probabilistic Rules"
**File:** `docs/training/logic_bank_api_probabilistic.prompt`

A comprehensive training document that teaches ChatGPT/Copilot how to translate natural language into probabilistic logic using `Rule.ai_decision()`. This mirrors the existing `logic_bank_api.prompt` for deterministic rules, completing the DR/PR architecture.

### 2. Created User-Facing Documentation
**File:** `readme_probabilistic.md`

Complete guide showing two demo scenarios:
- **Scenario 1 (Greenfield):** `als genai create` generates complete system from one prompt
- **Scenario 2 (Brownfield):** Copilot adds PR to existing database

### 3. Updated Copilot Training
**File:** `.github/.copilot-instructions.md`

Added reference to the new Rosetta Stone so Copilot knows about probabilistic rules.

---

## The Core Design: Probabilistic Value Computation

### Key Insight
Probabilistic rules **compute column values** using AI, just like deterministic rules compute values with formulas:

```python
# Deterministic value computation
Rule.formula(derive=Item.amount, as_expression=lambda row: row.quantity * row.unit_price)

# Probabilistic value computation  
Rule.ai_decision(derive=SysSupplierReq.chosen_supplier_id, ...)
```

Once AI computes the value, **deterministic rules cascade automatically**:
```
AI picks supplier → unit_price set → item.amount calculated → 
order.total updated → customer.balance adjusted → credit_limit validated
```

### The Pattern: Request Pattern (Mandatory)

**Every AI decision MUST use a SysXxxReq audit table:**
- Governance & explainability
- Complete audit trail
- Debugging capability
- Regulatory compliance

**Convention: `Sys{Domain}Req` Structure**
```python
class SysSupplierReq(Base):
    id = Column(Integer, primary_key=True)
    chosen_supplier_id = Column(ForeignKey('supplier.id'))  # The AI decision
    request = Column(String(2000))  # Full AI prompt
    reason = Column(String(500))  # AI's explanation
    created_on = Column(DateTime, default=datetime.utcnow)
    # Context FKs
    item_id = Column(ForeignKey('item.id'))
    product_id = Column(ForeignKey('product.id'))
```

---

## Critical Design Decisions Made

### 1. SysXReq Table Generation Convention

**User Prompt:**
```text
use AI to select supplier [store in SysSupplierReq]
```

**Copilot Behavior:**
1. Check if `SysSupplierReq` exists in `database/models.py`
2. If exists and matches convention → Use it
3. If doesn't exist → Create it with standard structure + Alembic migration
4. **If exists but wrong structure → ERROR (entire request fails)**

**Error Example:**
```
Error: SysSupplierReq exists but doesn't match required convention.

Expected: chosen_supplier_id, request, reason, created_on
Found: selected_supplier_id, ai_prompt, justification

Options:
1. Rename fields to match convention (recommended)
2. Use different table: [store in MyCustomAudit]
3. Drop existing SysSupplierReq table

Please fix and re-run your request.
```

**Why fail completely?**
- Prevents broken half-implementations
- Forces convention adherence
- Clear checkpoint for user
- No debugging "why doesn't this work?"

### 2. Test Context via Config File

**Problem:** Need to simulate scenarios ("Suez Canal blocked", "Hurricane in Gulf") for testing/demos without changing code.

**Solution:** Add to `config/config.py`:
```python
class Config:
    # AI Testing Context (set to None for production)
    AI_WORLD_CONDITIONS = 'ship aground in Suez Canal'
    AI_MARKET_CONDITIONS = None
    AI_TRAFFIC_CONDITIONS = None
```

**Copilot generates:**
```python
from config import config

world_conditions = config.Config.AI_WORLD_CONDITIONS or 'normal operations'
considering={'world_conditions': world_conditions, 'customer_region': 'US'}
```

**Benefits:**
- Reproducible testing
- Demo different scenarios easily
- Version-controlled test conditions
- Simple toggle for production

### 3. Graceful Fallback (No API Key)

**When `APILOGICSERVER_CHATGPT_APIKEY` is missing:**
- ✅ System continues working
- ✅ Uses deterministic fallback logic
- ✅ Copilot **infers fallback from optimization criteria**:
  - "optimize for cost" → choose lowest cost
  - "optimize for speed" → choose shortest lead time
  - "optimize for reliability" → choose highest rated
  - No optimization specified → choose first available
- ✅ Stores reasoning: "Fallback: no API key available, using [strategy]"
- ✅ Complete audit trail maintained

**Key:** User doesn't specify fallback - Copilot infers it from context!

### 4. Scope Validation

**Probabilistic rules are for VALUE COMPUTATION and SELECTION only.**

**✅ Valid patterns:**
- "choose/select X from Y based on Z"
- "compute/calculate/set X considering Y"
- "determine X by evaluating Y options"

**❌ Invalid patterns (MUST ERROR):**
- "ensure X is Y" (enforcement, not computation)
- "make X happen" (action, not decision)
- "predict X" (without selection context - that's ML models)
- "guarantee X" (too vague/subjective)

**Example Error:**
```
Error: Cannot implement "ensure all customers are happy"

Reason: Not a computable value or selection decision.

Probabilistic rules can:
✅ Select from concrete candidates
✅ Compute based on measurable factors

They cannot:
❌ Ensure subjective states
❌ Make open-ended predictions

Please reformulate as a selection or computation.
```

---

## Scenario 2: Complete User Prompt (Brownfield)

**Starting Point:** Customer, Order, Item, Product, Supplier, ProductSupplier tables exist

**User gives Copilot:**
```text
I have an existing order management system. Please implement Check Credit logic 
using LogicBank declarative rules in logic/logic_discovery/check_credit.py:

1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total (date_shipped is null)
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
     [store in SysSupplierReq]
   - ELSE copy from Product.unit_price
```

**Copilot generates:**
- ✅ All deterministic rules (constraint, sum, formula, copy)
- ✅ Product.count_suppliers count rule
- ✅ **SysSupplierReq audit table** (if doesn't exist)
- ✅ **Alembic migration** to create the table
- ✅ Conditional formula with IF/ELSE logic
- ✅ SysSupplierReq request pattern with insert
- ✅ AI event handler calling OpenAI
- ✅ Relationship navigation to ProductSupplierList
- ✅ Error handling and fallback logic
- ✅ Test context from config/config.py

**User action:** Run migration, restart server

**Result:** Add Egyptian Cotton Sheets → AI selects NJ supplier ($205) over Near East ($105) due to Suez Canal → Logic cascades → Credit validated → Complete audit trail in SysSupplierReq.

**Key:** One prompt, complete implementation (including table creation), no manual coding.

---

## The Working Implementation (Reference)

**File:** `logic/logic_discovery/check_credit.py`

This is the pattern we're teaching Copilot to generate from natural language:

**Key Code Sections:**

1. **Conditional Formula (triggers AI when needed):**
```python
def ItemUnitPriceFromSupplier(row: models.Item, old_row, logic_row):
    if row.product.count_suppliers == 0:
        return row.product.unit_price  # No suppliers - use default
    
    # Create SysSupplierReq (Request Pattern)
    sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    sys_supplier_req = sys_supplier_req_logic_row.row
    sys_supplier_req_logic_row.link(to_parent=logic_row)
    sys_supplier_req.product_id = row.product_id
    sys_supplier_req.item_id = row.id
    sys_supplier_req_logic_row.insert(reason="Supplier Svc Request")
    return sys_supplier_req.chosen_unit_price

Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)
```

2. **AI Event Handler:**
```python
def choose_supplier_for_item_with_ai(row: SysSupplierReq, old_row, logic_row):
    # Get supplier candidates
    supplier_options = [
        {'supplier_id': s.supplier_id, 'unit_cost': float(s.unit_cost),
         'lead_time_days': s.lead_time_days, 'region': s.supplier.region}
        for s in row.product.ProductSupplierList
    ]
    
    # Check API key
    api_key = os.getenv("APILOGICSERVER_CHATGPT_APIKEY")
    if not api_key:
        reasoning = "Fallback: no API key; defaulting to first supplier"
        chosen_supplier = supplier_options[0]
    else:
        # Call OpenAI
        world_conditions = 'ship aground in Suez Canal'  # From config in production
        messages = [
            {"role": "system", "content": "You are a supply chain optimization assistant..."},
            {"role": "user", "content": f"Current world conditions: {world_conditions}"},
            {"role": "user", "content": f"Supplier options: {json.dumps(supplier_options)}"},
            {"role": "user", "content": "Respond with JSON..."}
        ]
        completion = client.chat.completions.create(
            model='gpt-4o-2024-08-06',
            messages=messages,
            response_format={"type": "json_object"}
        )
        # Parse response, extract chosen supplier
        
    # Store results
    row.chosen_supplier_id = chosen_supplier.supplier_id
    row.chosen_unit_price = chosen_supplier.unit_cost
    row.reason = reasoning

Rule.early_row_event(models.SysSupplierReq, calling=choose_supplier_for_item_with_ai)
```

---

## What We Learned: AI Design Collaboration

### AI Struggled With:
1. **Missing the trigger** - showed Rule.ai_decision() but didn't explain what calls it
2. **Systemic integration** - how components wire together
3. **Missing the target** - didn't understand goal was "als genai create" one-shot generation until explicitly stated
4. **Request object inference** - too ambitious to infer complete table structure from vague prompts

### AI Excelled At:
1. **Pattern application** - once shown Request Pattern, applied it correctly
2. **Parallel structure** - understood DR/PR symmetry when pointed out
3. **Documentation** - good at elaborating once architecture was clear
4. **Iteration** - quickly incorporated feedback and refined

### Key Lesson: "You Gotta Tell AI the Target!"

The deployment model fundamentally shapes the solution:
- Interactive coding assistant?
- One-shot generation?
- Incremental feature addition?

Must establish the target upfront!

---

## Files Modified

### Created:
1. `docs/training/logic_bank_api_probabilistic.prompt` - Rosetta Stone for PR
2. `readme_probabilistic.md` - User guide with scenarios

### Updated:
1. `.github/.copilot-instructions.md` - Added PR reference
2. (This handoff document)

### Reference (existing, working code):
1. `logic/logic_discovery/check_credit.py` - The pattern we're teaching
2. `database/models.py` - Shows SysSupplierReq structure

---

## Next Steps (Implementation Phase)

### Phase 1: Test the Rosetta Stone
1. Give Copilot the Scenario 2 prompt (above)
2. See if it generates the complete implementation
3. Identify gaps in training
4. Refine Rosetta Stone

### Phase 2: Enhance Training
Based on testing, add:
- More complete end-to-end examples
- Explicit integration patterns
- Common pitfalls and anti-patterns

### Phase 3: Implement `Rule.ai_decision()` API
Currently we have the **design** and **training** for an API that doesn't exist yet.
The actual `Rule.ai_decision()` class needs to be implemented in LogicBank.

**OR** - continue using the manual pattern (what check_credit.py does) and the Rosetta Stone teaches that pattern.

### Phase 4: Test Scenario 1 (Greenfield)
Full `als genai create` with one prompt generating complete system.

---

## Key Quotes from the Session

> "You will thank us later" = governance, explainability, debugging all come free!

> "You gotta tell AI the target!" - deployment model fundamentally shapes solution

> "It's computing a **value** (supplier_id, price) - just like Rule.formula computes values"

> "Fail fast and clearly" - entire request stops on convention mismatch

---

## Open Questions for Next Session

1. Should `Rule.ai_decision()` be implemented as actual API, or keep teaching the manual pattern?
2. How to test: Give Copilot the Scenario 2 prompt in a fresh workspace?
3. Does the Rosetta Stone need more complete end-to-end examples?
4. Should we add config/config.py updates to the generated code?

---

## Context for AI in Next Session

**This project enables ChatGPT/Copilot to generate complete working systems with both deterministic and probabilistic rules from natural language.**

**Current state:**
- ✅ Deterministic rules (DR) working via `logic_bank_api.prompt`
- ✅ Probabilistic rules (PR) design complete
- ✅ Rosetta Stone created: `logic_bank_api_probabilistic.prompt`
- ✅ User documentation complete: `readme_probabilistic.md`
- ✅ Working reference implementation: `check_credit.py`
- ⏳ Need to test: Give Copilot the Scenario 2 prompt, see what it generates

**The vision:** One natural language prompt → Complete working system with AI-powered logic → Press F5 → It runs.

**The challenge:** Teaching AI to generate complete, wired implementations (not code snippets) from minimal natural language.

---

**End of Handoff Document**
