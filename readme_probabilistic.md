---
title: Probabilistic Rules - Natural Language → AI Value Computation
notes: Describes how to use Rule.ai_decision() via natural language with Copilot
target: Complete working system from single prompt via 'als genai create'
source: docs/training/logic_bank_api_probabilistic.prompt (the Rosetta Stone for PR)
related: readme_ai_mcp.md, README.md, docs/training/logic_bank_api.prompt
version: 1.7
date: Nov 15, 2025
status: ✅ PHASE 1 COMPLETE - Refactored architecture with ai_requests/
changelog:
  - 1.7 (Nov 15, 2025) - Clarified 3-step demo workflow with complete prompt at top
  - 1.6 (Nov 15, 2025) - Architecture refactor: ai_requests/ folder, formula pattern, AI as value computation
  - 1.5 (Nov 14, 2025) - Refactored to introspection-based pattern: 233 lines → 60 lines (75% reduction)
  - 1.4 (Nov 14, 2025) - PHASE 1 COMPLETE: Generated working implementation from natural language, tested successfully
  - 1.3 (Nov 13, 2025) - Added Scenario 2: brownfield demo with complete prompt
  - 1.2 (Nov 13, 2025) - Added TARGET: complete working system from one prompt
  - 1.1 (Nov 13, 2025) - Clarified as "value computation" vs "decision", added appendix on request object inference
  - 1.0 (Nov 13, 2025) - Initial creation of PR Rosetta Stone and user guide
---

# Probabilistic Rules: Natural Language → AI Value Computation

## 🚀 Demo Workflow - 3 Simple Steps

**This is a demonstration of generating probabilistic + deterministic logic from natural language.**

### ⚠️ IMPORTANT: Demo Setup

This workflow demonstrates generating logic **from scratch** - it is **NOT for normal development**.

### STEP 1: YOU Reset to Clean Database (DEMO ONLY!)

**⚠️ WARNING: This step DELETES ALL LOGIC FILES you've created!**

**YOU (not Copilot) run this command:**

```bash
cd /Users/val/dev/ApiLogicServer/ApiLogicServer-dev/org_git/PDL
sh restart.sh
```

**What `restart.sh` does:**
- ❌ Deletes database and recreates it clean
- ❌ Resets `models.py` and `admin.yaml` to baseline state
- ❌ **DELETES ALL FILES in `logic/logic_discovery/`** (except auto_discovery.py)

**Only run this when:**
- Demonstrating code generation from scratch
- Resetting for a fresh demo
- You want to start over completely

**DO NOT run this if:**
- You have logic you want to keep
- You're in the middle of development
- You just created files with Copilot

**DO NOT ask Copilot to run restart.sh - you must run it yourself in your terminal!**

---

### STEP 2: YOU Give Copilot This Prompt (Copilot Generates the Logic)

**⚠️ FOR DEMO USERS ONLY:** After running restart.sh, open a **NEW Copilot chat session** (not this one!) and paste this prompt:

**🚫 CRITICAL INSTRUCTION FOR AI ASSISTANTS READING THIS FILE:**

**This entire section is DOCUMENTATION ONLY describing a demo workflow. It is NOT an instruction to implement anything.**

**DO NOT:**
- Generate or modify ANY files mentioned below
- Assume you should implement the logic shown in the prompt

**ONLY implement if the user explicitly says:** "Please implement this now" or "Generate the Check Credit logic"

**This section documents what ANOTHER Copilot instance (in a fresh demo session) will do. You are reading a script, not following it.**

---

```
Check Credit Logic:

1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
   - ELSE copy from Product.unit_price
```

**What Copilot will generate from this prompt (DOCUMENTATION - describes future generation):**
- ✅ `logic/logic_discovery/check_credit.py` - 5 deterministic rules + conditional AI formula
- ✅ `logic/logic_discovery/ai_requests/supplier_selection.py` - Reusable AI handler with Request Pattern
- ✅ `database/models.py` - Add SysSupplierReq model with relationships (⚠️ in normal projects)
- ✅ `ui/admin/admin.yaml` - Add SysSupplierReq resource (⚠️ in normal projects)
- ✅ Create `sys_supplier_req` table in database via Alembic migration

**How it works:** A user runs restart.sh, opens a NEW Copilot chat, pastes the prompt above. THAT Copilot instance reads `.github/.copilot-instructions.md` and the training files in `docs/training/` to generate the implementation.

**CRITICAL PATTERNS - Copilot Must Include:**

1. **Value Assignment After AI** - After AI computation completes, MUST copy result to target row:
   ```python
   # In ItemUnitPriceFromSupplier event handler:
   supplier_req_logic_row.insert(reason="AI supplier selection request")
   
   # CRITICAL: Copy AI result to target row
   item_row.unit_price = supplier_req.chosen_unit_price
   logic_row.log(f"Item - AI selected supplier, unit_price set to {item_row.unit_price}")
   ```
   ❌ **Without this**: target field remains None, formulas fail with "NoneType" errors
   ✅ **With this**: AI value flows into deterministic rule cascade

2. **Request Pattern with new_logic_row** - Pass CLASS not instance:
   ```python
   # ✅ CORRECT: Pass the class
   supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
   supplier_req = supplier_req_logic_row.row  # Get instance AFTER creation
   
   # ❌ WRONG: Don't pass an instance
   supplier_req = models.SysSupplierReq()
   supplier_req_logic_row = logic_row.new_logic_row(supplier_req)  # ERROR!
   ```

---

### STEP 3: Start Server and Test

```bash
# Start server in background (so curl commands work in same terminal)
python api_logic_server_run.py > /tmp/server.log 2>&1 &

# Wait for server to start (about 5 seconds)
sleep 5

# Test: Create item with product that has suppliers (triggers AI selection)
curl -X POST http://localhost:5656/api/Item \
  -H "Content-Type: application/vnd.api+json" \
  -d '{
    "data": {
      "type": "Item",
      "attributes": {
        "order_id": 1,
        "product_id": 6,
        "quantity": 10
      }
    }
  }'

# Verify audit trail was created
curl http://localhost:5656/api/SysSupplierReq

# When done testing, stop the server:
# pkill -f api_logic_server_run.py
```

**Expected Result:**
- ✅ Item created with unit_price=105.0, amount=1050.0
- ✅ AI selected supplier considering "Suez Canal blockage" (from config/ai_test_context.yaml)
- ✅ SysSupplierReq audit record created with reason
- ✅ Order total updated, Customer balance updated, credit check passes
- ✅ Complete logic cascade: AI value → formulas → sums → constraint validation

---

## 📋 Understanding the Demo vs Development Workflow

### Demo Workflow (What This Document Shows)

This document demonstrates **generating everything from scratch** for presentation purposes:

1. **Run `restart.sh`** - Wipes everything clean (⚠️ DESTRUCTIVE!)
2. **Give prompt to Copilot** - Generates all files fresh
3. **Test** - Verify the generated code works

**This is for DEMONSTRATING the generation capability, not normal development.**

### Normal Development Workflow (What You Should Do)

When actually building or extending a system:

1. **DO NOT run `restart.sh`** - It deletes your work!
2. **Give prompt to Copilot** - It creates files in the existing project
3. **Run alembic migration** if schema changes are needed
4. **Test** - Verify your changes work

**Key Difference:** In development, you keep your existing files and incrementally add to them.

---

## 🎯 Key Files Generated (For Documentation Only)

**🚫 CRITICAL FOR AI ASSISTANTS: This entire section is DOCUMENTATION ONLY.**

**DO NOT generate, read, or modify ANY files listed below unless the user explicitly says "implement this now" or "generate the Check Credit logic".**

**If you are reading this as background context or to understand the system, you are reading a DEMO SCRIPT, not actionable instructions.**

---

When a user gives the prompt to a NEW Copilot chat session (in a fresh demo), that Copilot instance generates:

| File Created/Modified | Purpose |
|----------------------|---------|
| `logic/logic_discovery/check_credit.py` | Main business logic with 5 deterministic rules + conditional AI formula |
| `logic/logic_discovery/ai_requests/supplier_selection.py` | Reusable AI handler with Request Pattern |
| `database/models.py` | Add SysSupplierReq model with relationships |
| `ui/admin/admin.yaml` | Add SysSupplierReq resource for Admin UI |

---

## 🔧 Detailed Test Verification
- ✅ Reason: "Suez Canal blockage" from config/ai_test_context.yaml
- ✅ Order total updated (Item.amount → Order.amount_total)
- ✅ Customer balance updated (Order.amount_total → Customer.balance)
- ✅ Credit check passes (balance ≤ credit_limit)
- ✅ Audit trail in SysSupplierReq table (chosen_supplier_id, reason, request)

**Check the logic log:**
```bash
# Extract clean logic execution trace (ONE LINE per rule, hierarchical indentation)
grep -A 100 "Logic Phase:.*ROW LOGIC" server.log | \
  awk -F' row: ' '{print $1}' | \
  grep -E "^\.\.|^Logic Phase:" | \
  head -50
```

**Expected output:**
```
Logic Phase: ROW LOGIC
..Item[None] {Insert - client} id: None, order_id: 1, product_id: 6, quantity: 10
..Item[None] {Item - Product has 2 suppliers, invoking AI}
....SysSupplierReq[None] {Insert - AI supplier selection request}
....SysSupplierReq[None] {Test context loaded: ship aground in Suez Canal}
....SysSupplierReq[None] {Calling OpenAI API for selection}
....SysSupplierReq[None] {Set chosen_supplier_id = 2}
....SysSupplierReq[None] {Set chosen_unit_price = 205.0}
..Item[None] {Item - AI selected supplier, unit_price set to 205.0}
..Item[None] {Formula amount} amount: [None-->2050.0]
....Order[1] {Update - Adjusting order: amount_total} amount_total: [300.0-->2350.0]
```

**Alternative: Test via Admin UI**
1. Open http://localhost:5656
2. Navigate to Orders → Order #1
3. Add Item: Product = Egyptian Cotton Sheets, Quantity = 10
4. Save → Watch logic execute
5. Check SysSupplierReq table for audit trail

## ✅ Phase 1 Complete: Proof of Concept Validated (Nov 14, 2025)

**Achievement:** Successfully generated complete probabilistic + deterministic rules implementation from single natural language prompt in **less than one day**.

**Test Results:**
- ✅ Copilot generated 233-line implementation from 5-sentence prompt
- ✅ AI supplier selection working (OpenAI integration)
- ✅ Deterministic rules cascading correctly (sums, formulas, constraints)
- ✅ SysSupplierReq audit table created with migration
- ✅ Logic executed: AI selected NJ supplier ($205) over Near East ($105) due to "Suez Canal blockage" context
- ✅ Credit limit constraint properly rejected over-limit transaction
- ✅ Complete audit trail with AI reasoning logged

**Errors Fixed & Training Documentation Updated (v1.4):**

All errors encountered during implementation have been fixed AND the training documentation has been updated with **explicit positive patterns** to prevent recurrence:

1. **Formula calling=False error** - Rule.formula() tried to use calling=False (invalid)
   - ❌ Error: "Formula requires one of as_exp, as_expression or calling"
   - ✅ Fix: Removed calling parameter entirely, used as_expression with ternary
   - 📚 Training: Added section showing correct conditional formula pattern
   
2. **new_logic_row pattern error** - Passed instance instead of class
   - ❌ Error: "'SysSupplierReq' object is not callable"
   - ✅ Fix: Changed `new_logic_row(supplier_req)` → `new_logic_row(models.SysSupplierReq)`
   - 📚 Training: Added "REQUIRED PATTERN: Request Pattern with new_logic_row" section
   
3. **Missing value assignment** - AI set chosen_unit_price but didn't copy to Item.unit_price
   - ❌ Error: "unsupported operand type(s) for *: 'int' and 'NoneType'"
   - ✅ Fix: Added explicit `item_row.unit_price = supplier_req.chosen_unit_price`
   - 📚 Training: Added "REQUIRED PATTERN: Value Assignment After AI" section
   
4. **Type conversion for foreign keys** - Decimal type used for ID fields
   - ❌ Error: "type 'decimal.Decimal' is not supported" for SQLite INTEGER FK
   - ✅ Fix: Keep ID fields as int, only prices/costs as Decimal
   - 📚 Training: Added "REQUIRED PATTERN: Type Handling for Database Fields" section

**Key Documentation Philosophy Applied:**
- ✅ **Be explicit about what TO DO** (show correct patterns first)
- ✅ **Show complete working examples** (not fragments)
- ✅ **Use visual markers** (✅ CORRECT, ❌ WRONG) for clarity
- ✅ **Explain WHY patterns work** (not just error recovery)
- ✅ **Place patterns BEFORE the sections that use them**

**Earlier Fixes (v1.2-1.3):**
1. **Rule.count() syntax error** - Incorrectly assumed 'calling' parameter (only Rule.formula() has it)
   - Fix: Updated training doc v1.2 with CRITICAL section on Rule API signatures
2. **YAML test context** - Changed from config.py to separate config/ai_test_context.yaml
   - Reason: Cleaner separation, easier version control
3. **Terminology clarity** - Changed "AI decision" → "AI value computation"
   - Reason: More specific, less ambiguous

**Refactoring Achievement (Nov 14, 2025):**
- ✅ **Code reduction: 233 → 60 lines (75% reduction)**
- ✅ Created `logic/system/ai_value_computation.py` - reusable introspection-based utility
- ✅ Automatically discovers: candidate fields, result columns, field mappings
- ✅ User code focuses on intent: `compute_ai_value(candidates='product.ProductSupplierList', optimize_for='...', fallback='min:unit_cost')`
- ✅ Server tested and running - refactored implementation works correctly
- ✅ Updated training docs with `logic_row.log()` pattern (v1.3)

**Time Investment:** < 1 day from concept to working tested system

**Next:** Phase 2 - Integrate into `als genai create` for full greenfield generation

---

## Two Demo Scenarios

### Scenario 1: From Nothing (Greenfield)

`als genai create` generates **complete working system** from one prompt - see "The Target" section below.

### Scenario 2: From Existing DB (Brownfield) 

**Starting Point:** Existing system with Customer, Order, Item, Product, Supplier, ProductSupplier tables.

**User gives Copilot this complete prompt:**
```text
Check Credit Logic:

1. Constraint: Customer balance must not exceed credit_limit
2. Customer balance is sum of unshipped Order amount_total
3. Order amount_total is sum of Item amounts
4. Item amount is quantity * unit_price
5. Item unit_price: 
   - IF Product has suppliers (Product.count_suppliers > 0), 
     use AI to select optimal supplier based on cost, lead time, and world conditions
   - ELSE copy from Product.unit_price
```


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

**Copilot generates:** Complete working implementation including:
- ✅ All deterministic rules (constraint, sum, formula, copy)
- ✅ Product.count_suppliers count rule
- ✅ **SysSupplierReq audit table** (if doesn't exist matching convention)
- ✅ **Alembic migration** to create the table
- ✅ Conditional formula with IF/ELSE logic
- ✅ SysSupplierReq request pattern with insert
- ✅ AI event handler calling OpenAI
- ✅ Relationship navigation to ProductSupplierList
- ✅ Error handling and fallback logic

**Convention for AI Audit Tables:**

When user specifies `[store in SysXxxReq]`, Copilot will:

1. **Check if table exists** in models.py matching standard pattern:
   - `chosen_xxx_id` (FK to selected entity)
   - `request` (String 2000) - full AI prompt
   - `reason` (String 500) - AI explanation
   - `created_on` (DateTime) - timestamp
   - Context FKs (e.g., `item_id`, `product_id`)

2. **If table exists and matches** → Use it (generate logic only)

3. **If table doesn't exist** → Create it with standard structure + migration

4. **If table exists but doesn't match** → **ERROR - entire request fails:**
   ```
   Error: SysXxxReq exists but doesn't match required convention.
   
   Expected: chosen_xxx_id, request, reason, created_on
   Found: [actual fields]
   
   Options:
   1. Rename fields to match convention (recommended)
   2. Use different table: [store in MyCustomAudit]
   3. Drop existing SysXxxReq table
   ```
   No logic generated until resolved - fail fast and clearly.

**Testing & Demo Support:**

Add to `config/ai_test_context.yaml` for test scenarios:
```yaml
# AI Test Context - separated from application config
# Set values to None or omit for production/normal conditions

world_conditions: 'ship aground in Suez Canal'
market_conditions: null
traffic_conditions: null
weather_conditions: null
```

Copilot generates code that loads this:
```python
import yaml
from pathlib import Path

config_path = Path(__file__).parent.parent / 'config' / 'ai_test_context.yaml'
with open(config_path, 'r') as f:
    test_context = yaml.safe_load(f)
world_conditions = test_context.get('world_conditions') or 'normal operations'
```

Benefits:
- Reproducible testing without code changes
- Demo different scenarios easily
- Version-controlled test conditions
- Simple toggle for production

**Graceful Fallback (No API Key):**

When `APILOGICSERVER_CHATGPT_APIKEY` is missing, system continues working:

- ✅ Uses deterministic fallback logic
- ✅ Copilot infers fallback from optimization criteria:
  - "optimize for cost" → choose lowest cost
  - "optimize for speed" → choose shortest time
  - "optimize for reliability" → choose highest rated
  - No optimization → choose first available
- ✅ Stores reasoning: "Fallback: no API key available, using [strategy]"
- ✅ Complete audit trail maintained

This enables:
- Development without API key
- Demos without burning credits
- Production resilience if OpenAI down
- Cost control

**Scope Validation:**

Probabilistic rules are for **value computation and selection** only.

✅ **Valid requests:**
- "choose supplier based on cost and lead time"
- "set price considering market conditions"
- "select route optimizing for delivery time"

❌ **Invalid requests (will ERROR):**
- "ensure all customers are happy" (subjective, not computable)
- "make supplier reliable" (action, not decision)
- "predict customer churn" (ML model, not selection)
- "guarantee quality" (too vague)

Copilot will fail clearly:
```
Error: Cannot implement "ensure customers are happy"

Reason: Not a computable value or selection decision.

Probabilistic rules can:
✅ Select from concrete candidates
✅ Compute based on measurable factors

They cannot:
❌ Ensure subjective states
❌ Make open-ended predictions

Please reformulate as a selection or computation.
```

**User action:** Run migration, restart server

**Result:** Add Egyptian Cotton Sheets → AI selects NJ supplier ($205) over Near East ($105) due to Suez Canal → Logic cascades → Credit validated → Complete audit trail in SysSupplierReq.

**Key:** One prompt, complete implementation (including table creation), no manual coding.

**Implementation Note:** The generated logic is **concise (~60 lines)** using introspection-based utilities:
- `logic/system/ai_value_computation.py` - Reusable AI computation with SQLAlchemy introspection
- Automatically discovers: candidate fields (supplier_id, supplier_name, unit_cost, lead_time_days, region)
- Automatically maps: chosen_supplier_id ← supplier_id, chosen_unit_price ← unit_cost
- User code focuses on domain intent: `compute_ai_value(candidates='product.ProductSupplierList', optimize_for='...', fallback='min:unit_cost')`

---

## The Target: Complete Working System from One Prompt

**Critical Context for Scenario 1:** This feature enables `als genai create` to generate a **complete, ready-to-run system** from a single natural language prompt:

```bash
als genai create --using prompt.txt
```

Where `prompt.txt` contains:
```text
Create a system with customers, orders, items, products, suppliers...

Use case: Check Credit
    [5 deterministic rules + 1 probabilistic rule]
    
Use case: App Integration
    [Kafka integration]
```

**ChatGPT generates everything:**
- ✅ Database schema (including `SysSupplierReq` request table)
- ✅ Test data
- ✅ JSON:API endpoints
- ✅ Admin web app
- ✅ **Complete logic** (DR + PR, fully wired):
  - Count rule for suppliers
  - Formula with conditional (IF suppliers THEN AI ELSE default)
  - Request pattern implementation
  - AI event handler with OpenAI integration
  - All relationships and foreign keys

**Result:** Press F5 → system runs → add item → AI chooses supplier → logic cascades → constraints validate.

**No manual coding required.** The Rosetta Stone must teach ChatGPT to generate ALL of this.

---

## Overview

Just as you can declare **deterministic value computation** in natural language:

```text
Customer balance is sum of Order amount_total where date_shipped is null
```

You can now declare **probabilistic value computation** in natural language:

```text
Choose the best supplier considering cost, lead time, and world conditions like 'Suez Canal blocked'.
Optimize for fastest delivery when disruptions are present.
```

Copilot translates both into executable declarative rules - no boilerplate code required.

**Key Insight:** Both are **computing column values** - one deterministically, one probabilistically:
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

---

## Implementation Approach: Introspection-Based Utilities

The system uses **SQLAlchemy introspection** to eliminate boilerplate and provide a clean, reusable pattern.

### Before: Manual Implementation (233 lines)

Previously, integrating AI decisions required extensive boilerplate:

```python
# Current approach: Manual OpenAI integration
def choose_supplier_for_item_with_ai(row, old_row, logic_row):
    client = OpenAI(api_key=os.getenv("APILOGICSERVER_CHATGPT_APIKEY"))
    
    # Build candidate list
    supplier_options = [
        {'supplier_id': s.supplier_id, 'unit_cost': float(s.unit_cost), 
         'lead_time_days': s.lead_time_days, 'region': s.supplier.region}
        for s in row.product.ProductSupplierList
    ]
    
    # Construct messages
    world_conditions = 'ship aground in Suez Canal'
    messages = [
        {"role": "system", "content": "You are a supply chain optimization assistant..."},
        {"role": "user", "content": f"Current world conditions: {world_conditions}"},
        {"role": "user", "content": f"Supplier options: {json.dumps(supplier_options)}"},
        {"role": "user", "content": "Respond with JSON containing reasoning and ai_supplier..."}
    ]
    
    # Call API
    completion = client.chat.completions.create(
        model='gpt-4o-2024-08-06',
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    # Parse response
    data = completion.choices[0].message.content
    response_dict = json.loads(data)
    reasoning = response_dict.get('reasoning', 'No reasoning provided')
    ai_supplier_id = response_dict.get('ai_supplier', {}).get('supplier_id')
    
    # Find supplier
    chosen_supplier = None
    for supplier in suppliers:
        if supplier.supplier_id == ai_supplier_id:
            chosen_supplier = supplier
            break
    
    # Handle errors, fallbacks, etc...
    if chosen_supplier is None:
        chosen_supplier = suppliers[0]
    
    # Store results
    row.chosen_supplier_id = chosen_supplier.supplier_id
    row.chosen_unit_price = chosen_supplier.unit_cost
    row.reason = reasoning
    
Rule.early_row_event(SysSupplierReq, calling=choose_supplier_for_item_with_ai)
```

**Problems:**
- ❌ 200+ lines of repetitive boilerplate
- ❌ Manual serialization of candidate fields
- ❌ Manual error handling and fallback logic
- ❌ Hard to maintain and test

---

### After: Introspection-Based Utility (~10 lines)

**The Solution:** `logic/system/ai_value_computation.py` uses SQLAlchemy introspection to:
1. **Discover candidates** - Navigate relationship path automatically
2. **Serialize attributes** - Introspect all columns (supplier_id, supplier_name, unit_cost, lead_time_days, region)
3. **Map results** - Match chosen_* columns to candidate fields
4. **Handle fallbacks** - Graceful degradation when no API key
5. **Load test context** - YAML-based world conditions
6. **Maintain audit trail** - Automatic request/reason/created_on population

**User code becomes:**

```python
def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """AI selects optimal supplier based on cost, lead time, and world conditions."""
    if not logic_row.is_inserted():
        return
    
    compute_ai_value(
        row=row,
        logic_row=logic_row,
        candidates='product.ProductSupplierList',
        optimize_for='fastest reliable delivery while keeping costs reasonable',
        fallback='min:unit_cost'
    )

Rule.early_row_event(on_class=models.SysSupplierReq, calling=supplier_id_from_ai)
```

**What the utility introspects automatically:**
- **Candidate fields:** supplier_id, supplier_name, unit_cost, lead_time_days, region (from ProductSupplier + Supplier)
- **Result columns:** chosen_supplier_id, chosen_unit_price (from SysSupplierReq)
- **Field mappings:** chosen_supplier_id ← supplier_id, chosen_unit_price ← unit_cost
- **Test context:** world_conditions from config/ai_test_context.yaml

**Benefits:**
- ✅ **90% code reduction** - 233 lines → ~60 lines total
- ✅ **Convention over configuration** - No manual field lists
- ✅ **Reusable** - Same utility for all AI value computations
- ✅ **Maintainable** - Change model → behavior updates automatically
- ✅ **Readable** - Intent-focused, not implementation-focused

---

## How Introspection Works

### 1. Discover Candidates via Relationship Navigation

```python
candidates='product.ProductSupplierList'
```

Utility navigates: `row.product.ProductSupplierList` → List[ProductSupplier]

### 2. Serialize All Candidate Attributes

Uses SQLAlchemy mapper introspection:
```python
mapper = sa_inspect(ProductSupplier)
# Discovers: supplier_id, product_id, unit_cost, lead_time_days
# Plus related: supplier.name, supplier.region (via relationships)
```

Result: `[{'supplier_id': 1, 'supplier_name': 'Acme', 'unit_cost': 10.5, ...}, ...]`

### 3. Map Results to Request Table

Introspects `SysSupplierReq` to find `chosen_*` columns:
```python
# Discovers: chosen_supplier_id, chosen_unit_price
# Maps: chosen_supplier_id ← supplier_id
#       chosen_unit_price ← unit_cost (handles price/cost variations)
```

### 4. Call OpenAI with Structured Prompt

```python
messages = [
    {"role": "system", "content": "You are an intelligent selection assistant..."},
    {"role": "user", "content": f"""
Current conditions: {world_conditions}
Candidates: {json.dumps(candidates)}
Optimization: {optimize_for}
"""}
]
```

### 5. Apply Fallback if No API Key

```python
fallback='min:unit_cost'  # Choose candidate with minimum unit_cost
# Other options: 'max:field', 'first'
```

---

## Natural Language Prompt Pattern

Tell Copilot what you need using this structure:

```text
Use AI to select [entity] from [candidates_relationship] based on:
- [criterion 1]
- [criterion 2]
- [world context]

Optimize for [goal]
Fallback: [strategy] if no API key 
otherwise optimize for lowest cost.

Store the reasoning in SysSupplierReq.reason field.
```

### Step 2: Copilot Generates the Rule

Copilot reads `docs/training/logic_bank_api_probabilistic.prompt` (the "Rosetta Stone for PR") and generates:

```python
Rule.ai_decision(
    derive=SysSupplierReq.chosen_supplier_id,
    from_candidates=lambda row: [
        {'id': ps.supplier_id,
         'cost': float(ps.unit_cost),
         'lead_time_days': ps.lead_time_days,
         'region': ps.supplier.region}
        for ps in row.product.ProductSupplierList
    ],
    optimize_for=['lead_time_days', 'cost'],
    considering={
        'world_conditions': 'Suez Canal blocked',
        'customer_region': 'US'
    },
    reasoning_to=SysSupplierReq.reason
)
```

### Step 3: Logic Executes Automatically

When an Item is created, the rule fires automatically:
1. **Gathers candidates** from `ProductSupplierList`
2. **Calls OpenAI** with structured context
3. **Parses response** and validates
4. **Stores decision** in `chosen_supplier_id`
5. **Stores reasoning** in `reason` field for audit
6. **Falls back gracefully** if API unavailable

---

## Common Use Cases

### 1. Supplier Selection

**Natural Language:**
```text
Choose the best supplier considering cost, lead time, and regional disruptions.
Optimize for reliability during supply chain issues.
```

**Generated Rule:**
```python
Rule.ai_decision(
    derive=SysSupplierReq.chosen_supplier_id,
    from_candidates=lambda row: [
        {'id': ps.supplier_id, 'cost': float(ps.unit_cost), 
         'lead_time_days': ps.lead_time_days, 'region': ps.supplier.region}
        for ps in row.product.ProductSupplierList
    ],
    optimize_for=['lead_time_days', 'cost'],
    considering={'world_conditions': 'supply chain disruptions'},
    reasoning_to=SysSupplierReq.reason
)
```

### 2. Dynamic Pricing

**Natural Language:**
```text
Set optimal price for this product considering competitor prices,
inventory levels, and demand forecast. Optimize for profit while
maintaining competitive position. Store reasoning in pricing_reason.
```

**Generated Rule:**
```python
Rule.ai_decision(
    derive=Product.current_price,
    from_candidates=lambda row: [
        {'price': p} 
        for p in range(int(row.cost * 1.1), int(row.cost * 2.0), 5)
    ],
    optimize_for=['profit_margin', 'competitive_position'],
    considering={
        'competitor_avg': row.competitor_avg_price,
        'inventory_level': row.stock_quantity,
        'demand_trend': row.demand_forecast
    },
    reasoning_to=Product.pricing_reason
)
```

### 3. Route Optimization

**Natural Language:**
```text
Choose the best delivery route considering traffic, weather, and urgency.
Optimize for fastest delivery time. Store reasoning in route_reason.
```

**Generated Rule:**
```python
Rule.ai_decision(
    derive=Delivery.chosen_route_id,
    from_candidates=lambda row: [
        {'id': r.id, 'distance_miles': r.distance_miles, 
         'typical_minutes': r.typical_minutes, 'toll_cost': r.toll_cost}
        for r in row.destination.AvailableRouteList
    ],
    optimize_for=['delivery_time', 'fuel_cost'],
    considering={
        'traffic': 'current heavy on I-95',
        'weather': row.weather_conditions,
        'priority': row.priority_level
    },
    reasoning_to=Delivery.route_reason
)
```

### 4. Staff Assignment

**Natural Language:**
```text
Assign the best qualified staff member to this project considering
skills, workload, and experience. Optimize for project success.
Store reasoning in assignment_reason.
```

**Generated Rule:**
```python
Rule.ai_decision(
    derive=Project.assigned_staff_id,
    from_candidates=lambda row: [
        {'id': s.id, 'skill_match': s.skill_score_for_project(row),
         'availability': s.available_hours, 
         'experience_years': s.years_experience}
        for s in StaffMember.query.filter_by(available=True).all()
    ],
    optimize_for=['skill_match', 'availability'],
    considering={
        'project_complexity': row.complexity_rating,
        'deadline': row.due_date
    },
    reasoning_to=Project.assignment_reason
)
```

---

## Integration with Deterministic Rules

Probabilistic rules work seamlessly with deterministic rules in the same logic flow.

**Natural Language:**
```text
When an item is added to an order:
1. Choose the best supplier using AI (considering cost, lead time, Suez Canal status)
2. Calculate item amount as quantity * unit_price
3. Update order total as sum of item amounts
4. Update customer balance as sum of unshipped order totals
5. Validate that customer balance does not exceed credit limit
```

**Generated Logic:**
```python
# Step 1: Probabilistic - AI chooses supplier and sets unit_price
Rule.ai_decision(
    derive=SysSupplierReq.chosen_supplier_id,
    from_candidates=lambda row: [
        {'id': ps.supplier_id, 'cost': float(ps.unit_cost), 
         'lead_time_days': ps.lead_time_days}
        for ps in row.product.ProductSupplierList
    ],
    optimize_for=['lead_time_days', 'cost'],
    considering={'world_conditions': 'Suez Canal blocked'},
    reasoning_to=SysSupplierReq.reason
)

# Steps 2-4: Deterministic - calculations cascade automatically
Rule.formula(derive=Item.amount, 
            as_expression=lambda row: row.quantity * row.unit_price)

Rule.sum(derive=Order.amount_total, as_sum_of=Item.amount)

Rule.sum(derive=Customer.balance, as_sum_of=Order.amount_total,
        where=lambda row: row.date_shipped is None)

# Step 5: Deterministic - validation (guardrail for AI decision)
Rule.constraint(validate=Customer,
               as_condition=lambda row: row.balance <= row.credit_limit,
               error_msg="Customer balance exceeds credit limit")
```

**The Flow:**
1. 🤖 **PR**: AI makes intelligent supplier choice
2. ⚡ **DR**: Calculations cascade automatically
3. 🛡️ **DR**: Constraints validate the result
4. ❌ **Rollback**: If AI choice violates credit limit, entire transaction rolls back
5. 🔄 **Retry**: System can retry with different AI parameters (e.g., "optimize for cost")

**Key Insight:** No special "AI safety code" needed - existing business rules automatically govern AI decisions!

---

## Built-in Features

### Automatic Error Handling

The rule handles all common failure modes:

```python
✅ Missing API key → Falls back to first candidate
✅ API timeout → Logs warning, falls back
✅ Invalid JSON response → Retries once, then fallback
✅ No candidates → Raises clear error
✅ Constraint violations → Normal LogicBank rollback
```

### Audit Trail for Governance

Every AI decision is automatically tracked:

```python
Rule.ai_decision(
    derive=SysSupplierReq.chosen_supplier_id,
    ...,
    reasoning_to=SysSupplierReq.reason,      # Why AI chose this
    request_to=SysSupplierReq.request        # Full prompt sent to AI
)
```

**Database stores:**
- `reason`: AI's explanation (e.g., "Suez Canal obstruction impacts Near East suppliers...")
- `request`: Complete prompt for reproducibility
- `chosen_supplier_id`: The decision
- `created_on`: When decision was made

**Benefits:**
- 📊 **Explainability**: Understand every AI decision
- 🔍 **Compliance**: Full audit trail for regulations
- 🐛 **Debugging**: See exactly what AI was considering
- 📈 **Learning**: Analyze decision patterns over time

### Graceful Fallback

If OpenAI is unavailable, system continues working:

```python
# Default behavior: select first candidate
# Custom fallback: override in rule definition
Rule.ai_decision(
    ...,
    fallback=lambda candidates: min(candidates, key=lambda c: c['cost'])
)
```

---

## Best Practices

### 1. Use the Request Pattern

Create a `SysXxxReq` table for AI requests:

```python
class SysSupplierReq(Base):
    id = Column(Integer, primary_key=True)
    item_id = Column(ForeignKey('item.id'))
    product_id = Column(ForeignKey('product.id'))
    request = Column(String(2000))           # Full prompt
    chosen_supplier_id = Column(ForeignKey('supplier.id'))
    reason = Column(String(500))             # AI reasoning
    created_on = Column(DateTime, default=datetime.utcnow)
```

**Benefits:**
- Complete audit trail
- Easy to review AI decisions
- Can replay requests for testing
- Supports governance requirements

### 2. Optimize Factor Priority

List factors in priority order:

```python
# Correct: Lead time is highest priority
optimize_for=['lead_time_days', 'cost', 'reliability']

# Wrong: Mixed priorities confuse AI
optimize_for=['cost', 'lead_time_days', 'reliability', 'cost']
```

### 3. Provide Rich Context

More context = better decisions:

```python
# Good: Specific, actionable context
considering={
    'world_conditions': 'Suez Canal blocked, expect 2-week delays',
    'customer_urgency': 'high - rush order',
    'budget_constraint': row.order.budget_limit
}

# Poor: Vague context
considering={'conditions': 'bad'}
```

### 4. Test with API Unavailable

Ensure fallback behavior is acceptable:

```python
# Unset API key to test fallback
os.environ['APILOGICSERVER_CHATGPT_APIKEY'] = ''

# Add item - should use first available supplier
# Verify system still works, just without AI optimization
```

---

## How It Works: The Rosetta Stone

When you provide natural language like:

```text
Choose the best supplier considering cost and lead time
```

Copilot uses `docs/training/logic_bank_api_probabilistic.prompt` as a translation guide - the "Rosetta Stone" that maps NL patterns to `Rule.ai_decision()` parameters.

**The training file contains:**
1. Complete API specification for `Rule.ai_decision()`
2. Pattern-matched examples (NL → Rule)
3. Common use cases (supplier, pricing, routing, staffing)
4. Integration patterns with deterministic rules
5. Error handling and fallback strategies
6. Anti-patterns (what NOT to do)

This is identical to how `docs/training/logic_bank_api.prompt` enables NL → deterministic rules translation. Now both DR and PR have their Rosetta Stones!

---

## Try It Yourself

### 1. Tell Copilot your requirement:

```text
I need to choose the best supplier for products considering:
- Unit cost
- Lead time
- Current supply chain conditions
Optimize for reliability. Store reasoning for audit.
```

### 2. Copilot generates the rule:

```python
Rule.ai_decision(
    derive=SysSupplierReq.chosen_supplier_id,
    from_candidates=lambda row: [...],
    optimize_for=['lead_time_days', 'cost'],
    considering={'supply_chain': 'current disruptions'},
    reasoning_to=SysSupplierReq.reason
)
```

### 3. Test it:

```python
# Start server
python api_logic_server_run.py

# Add an item with a product that has multiple suppliers
# Watch console - see AI reasoning in action
# Check SysSupplierReq table for audit trail
```

---

## Summary

**Probabilistic Rules = Declarative AI Value Computation**

Just as deterministic rules eliminated 40× code bloat for business logic, probabilistic rules eliminate boilerplate for AI integration:

| Before | After |
|--------|-------|
| 50+ lines of OpenAI code | 10 lines declarative rule |
| Manual error handling | Automatic fallback |
| Custom audit trail code | Built-in governance |
| Inconsistent patterns | Uniform `Rule.ai_decision()` |
| Hard to maintain | Natural language → Rule |

**The Vision:** Natural language describes both deterministic logic AND probabilistic value computation. AI translates both into executable rules. The engine executes both with automatic integration, validation, and audit trails.

**The Key:** `Rule.ai_decision()` computes values (supplier_id, price, route_id) just like `Rule.formula()` - then deterministic rules cascade from those values automatically.

**Welcome to declarative AI value computation.** 🎯

---

---

## Appendix A: Design Challenges & AI Limitations

**Meta-Note:** This feature was designed through AI-human collaboration. This appendix documents the hard problems where AI struggled - insights for "AI Designs Features" article.

### Challenge 1: Recognizing the Missing Trigger

**Initial Design Flaw:** Examples showed `Rule.ai_decision()` but never explained what **calls** it.

```python
Rule.ai_decision(derive=SysSupplierReq.chosen_supplier_id, ...)
# Looks complete, but it's orphaned logic - nothing triggers it!
```

**Human caught:** "This logic never gets called"

**The gap:** AI focused on the probabilistic computation but missed the **integration point** - the conditional formula that decides when to invoke AI vs. use default logic.

**Resolution:** Needed explicit IF/ELSE structure:
```text
5. The Item unit_price depends on the product:
   - If the product has suppliers, use AI to choose optimal supplier
   - Otherwise, copy unit_price from Product
```

**Why AI struggled:** 
- Pattern matching works for isolated rules
- Integration patterns across rule types (formula → request → AI event) requires systemic thinking
- No training example showed "conditional invocation of PR from DR"

### Challenge 2: Terminology Precision - "Decision" vs "Value Computation"

**Initial framing:** "AI Decision" 

**Human insight:** "It's computing a **value** (supplier_id, price) - just like Rule.formula computes values"

**The distinction matters:**
```python
# Both compute column values - one deterministic, one probabilistic
Rule.formula(derive=Item.amount, as_expression=lambda row: row.quantity * row.unit_price)
Rule.ai_decision(derive=SysSupplierReq.chosen_supplier_id, ...)
```

**Why it matters:**
- Clarifies integration with DR (values cascade)
- Sets proper scope (not open-ended reasoning, just value selection)
- Makes the parallel with Rule.formula obvious

**Why AI missed it:** 
- "AI decision" is common terminology in literature
- Requires understanding the architectural constraint (fits into LogicBank's value derivation model)
- Needed domain knowledge about how rules cascade

### Challenge 3: Request Object Relationship Inference

**The question:** Can AI infer `SysSupplierReq` structure from:
```text
"Choose best supplier for items considering cost and lead time"
```

**What needs inference:**
- `item_id` FK (context: which item triggered this)
- `product_id` FK (data access: to get ProductSupplierList)
- `chosen_supplier_id` FK (result: the decision)

**Why it's hard:**
- Requires domain understanding (Item → Product → Suppliers)
- Must infer data access patterns (what data does AI need?)
- Ambiguous: Why `product_id` vs just navigate through `item.product`?

**Current status:** Too ambitious for MVP. Requires explicit user specification.

**Possible future:** Hybrid - AI suggests, user confirms.

### Challenge 4: The Complete User Prompt

**Initial attempts:** Fragmented examples
- Supplier selection in isolation
- No connection to Item.unit_price
- Missing the conditional logic

**What worked:** Single coherent prompt:
```text
5. The Item unit_price depends on the product:
   - If the product has suppliers, use AI to choose the optimal supplier
     considering unit cost, lead time, and world conditions
   - Otherwise, copy the unit_price from the Product
```

**Why AI struggled:**
- Easy to generate examples in isolation
- Hard to see the **complete workflow**: trigger → condition → AI call → result usage
- Training has fragmented examples, not end-to-end flows

### Challenge 5: What Actually Exists vs. What Needs Creation

**Confusion:** Does `Rule.ai_decision()` exist or is it proposed?

**Throughout design:**
- Talked as if it exists (generating examples)
- But it's actually a **design proposal** for implementation
- Current code uses manual OpenAI integration

**The gap:** 
- Designing vs. documenting existing features requires different mindsets
- AI defaulted to "document what exists" mode
- Needed explicit "we're designing something new" framing

### Challenge 7: Missing the Target - "You Gotta Tell AI the Target!"

**Critical miss:** Didn't understand the **actual goal** until explicitly stated.

**What I thought:** Help users add PR to existing projects via Copilot chat

**Actual target:** Enable `als genai create` to generate **complete working systems** from one prompt:
```bash
als genai create --using prompt.txt
# → ChatGPT generates: schema, data, API, app, logic (DR+PR, fully wired)
# → Press F5 → working system with AI supplier selection
```

**This changes everything:**
- Not about interactive Copilot assistance
- About teaching ChatGPT to generate **complete, wired implementations**
- From schema creation → request objects → conditional logic → AI events → all relationships
- Must work **first time**, no manual wiring

**Why it matters:**
- Much higher bar: complete working system vs. code snippets
- Different Rosetta Stone content: end-to-end patterns, not isolated examples
- Integration is mandatory: can't be orphaned logic

**Lesson:** Always establish the **deployment target** upfront:
- Interactive coding assistant?
- One-shot generation?
- Incremental feature addition?

The target fundamentally shapes the solution!

### Challenge 6: Scope Creep - What Belongs in the Rule?

**Temptation:** Add lots of parameters to `Rule.ai_decision()`:
```python
Rule.ai_decision(
    derive=...,
    from_candidates=...,
    optimize_for=...,
    considering=...,
    reasoning_to=...,
    request_to=...,
    model=...,
    temperature=...,
    fallback_strategy=...,
    retry_count=...,
    timeout=...,
    # ...endless configuration
)
```

**Human guidance:** Keep it simple, focus on the business problem.

**Why AI struggled:** 
- Easy to enumerate all possible options
- Hard to judge what's "essential" vs "configuration detail"
- No sense of API aesthetics or maintainability

### What Worked Well

✅ **Pattern Recognition:** Once shown Request Pattern, immediately applied it
✅ **Parallel Structure:** Understood DR/PR symmetry when pointed out
✅ **Documentation:** Good at elaborating once architecture was clear
✅ **Iteration:** Quickly incorporated feedback and refined

### Key Takeaway

**AI excels at:** Pattern application, elaboration, documentation generation

**AI struggles with:** 
- Systemic integration (how components fit together)
- Identifying missing pieces (orphaned logic, untriggered rules)
- Architectural coherence (what's the complete user story?)
- Judging appropriate scope (essential vs. nice-to-have)

**The collaboration pattern:**
1. Human provides architectural vision & integration insights
2. AI elaborates patterns, generates examples, documents thoroughly
3. Human catches gaps in integration, scope, and completeness
4. Iterate until coherent

**Conclusion:** AI is a powerful design partner, but needs human guidance on system-level thinking and integration points. The value is in the **collaboration**, not autonomous design.

---

## Appendix B: Request Object Inference Challenge

### The Request Pattern

The current implementation uses the **Request Pattern** (see [LogicBank docs](https://apilogicserver.github.io/Docs/Logic/#rule-patterns)):

1. Create `SysXxxReq` table (e.g., `SysSupplierReq`)
2. Link to relevant entities (item_id, product_id)
3. Store audit fields (request, reason, chosen_xxx_id, created_on)
4. Use `logic_row.new_logic_row()` and `insert()` to trigger AI
5. AI event fires on insert, computes value, stores reasoning

**Benefits:**
- Complete audit trail
- Governance and explainability
- Enables replay and debugging
- Clean separation of concerns

### Automatic Inference Challenge

For deterministic rules, AI can infer missing columns:
```text
"Customer balance is sum of orders" 
→ AI creates Customer.balance column
→ AI generates Rule.sum(...)
```

**Question:** Can AI infer request objects for probabilistic rules?

```text
"Choose best supplier considering cost and lead time"
→ AI should create SysSupplierReq table?
→ With what relationships?
```

### Two Alternatives

#### **Alternative 1: Explicit Request Object (Current Approach)**

**User specifies:**
```text
Create SysSupplierReq table with:
- item_id (foreign key to Item)
- product_id (foreign key to Product)  
- request, reason, chosen_supplier_id, created_on

Then when item is added, choose best supplier considering cost and lead time.
```

**Pros:**
- User controls schema
- Clear and explicit
- No ambiguity about relationships

**Cons:**
- Requires understanding Request Pattern
- More verbose
- User must identify needed relationships

#### **Alternative 2: Inferred Request Object (Future Enhancement)**

**User just says:**
```text
When item is added, choose best supplier considering cost and lead time.
Store reasoning for audit.
```

**AI infers:**
1. Context: Item creation triggers this
2. Relationships needed:
   - `item_id` (context: which item)
   - `product_id` (to access ProductSupplierList)
   - `chosen_supplier_id` (the result)
3. Creates `SysSupplierReq` table with these FKs
4. Generates both request pattern logic AND ai_decision rule

**Pros:**
- Seamless user experience
- Parallel with DR column inference
- Minimal user effort

**Cons:**
- Complex inference (domain relationships, data access patterns)
- Potential ambiguity (which entities to link?)
- May create wrong relationships

### Current Recommendation

**Start with Alternative 1 (Explicit)** for MVP:
- Clear and predictable
- Teaches users the Request Pattern
- Lower risk of inference errors

**Evolve toward Alternative 2 (Inferred)** as we learn:
- Gather patterns from real usage
- Build inference heuristics
- Provide smart suggestions with user confirmation

### Hybrid Approach

AI could **suggest** request object structure:

```text
User: "Choose best supplier for items"

AI: "I'll create a SysSupplierReq table with these relationships:
     - item_id → Item (context)
     - product_id → Product (to access suppliers)
     - chosen_supplier_id → Supplier (result)
     Does this look right? [yes/no/modify]"
```

This combines automation with user validation.

---

## Related Documentation

- `docs/training/logic_bank_api_probabilistic.prompt` - The Rosetta Stone for PR
- `docs/training/logic_bank_api.prompt` - The Rosetta Stone for DR  
- `README.md` - Complete project overview with PR/DR demo
- `readme_ai_mcp.md` - MCP integration and AI interaction
- `.github/.copilot-instructions.md` - Full Copilot training materials
- [LogicBank Rule Patterns](https://apilogicserver.github.io/Docs/Logic/#rule-patterns) - Request Pattern documentation
