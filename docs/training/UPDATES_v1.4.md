# Training Documentation Updates v1.4 (Nov 14, 2025)

## Philosophy: Explicit Positive Instructions

Following the principle **"be explicit about what TO DO, not just error recovery"**, all training documentation has been updated to show correct patterns FIRST, with clear visual markers.

## Files Updated

1. **`docs/training/logic_bank_api_probabilistic.prompt`** (v1.3 → v1.4)
2. **`docs/training/template_probabilistic_rules.py`** (inline comments enhanced)
3. **`readme_probabilistic.md`** (Phase 1 section updated)

---

## Four Critical Patterns Added

### 1. REQUIRED PATTERN: Conditional Formula with AI

**Error Fixed:** Formula tried to use `calling=False` (invalid parameter)

**Pattern Added (lines 16-52):**
```python
# Step 1: Register early event handler (fires BEFORE formula)
Rule.early_row_event(
    on_class=models.Item,
    calling=lambda row, old_row, logic_row: ItemUnitPriceFromSupplier(row, logic_row)
)

# Step 2: Formula that preserves AI-set value or uses default
Rule.formula(
    derive=models.Item.unit_price,
    as_expression=lambda row: (
        row.product.unit_price if row.product.count_suppliers == 0
        else row.unit_price  # Preserve value set by event handler
    )
)

# Step 3: Event handler that creates request and copies AI result
def ItemUnitPriceFromSupplier(item_row: models.Item, logic_row: LogicRow):
    if not logic_row.is_inserted() or item_row.product.count_suppliers == 0:
        return
    
    # Create request using new_logic_row (pass CLASS not instance)
    supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    supplier_req = supplier_req_logic_row.row  # Get the instance AFTER creation
    
    # Set request context
    supplier_req.item_id = item_row.id
    supplier_req.product_id = item_row.product_id
    
    # Insert triggers AI handler
    supplier_req_logic_row.insert(reason="AI supplier selection request")
    
    # CRITICAL: Copy AI result to target row
    item_row.unit_price = supplier_req.chosen_unit_price
```

**Key Points:**
- ✅ Use `as_expression` with ternary for conditional logic
- ✅ Never use `calling=False` - calling must be callable or omitted
- ✅ Complete working example showing all three steps

---

### 2. REQUIRED PATTERN: Request Pattern with new_logic_row

**Error Fixed:** Passed instance instead of class to new_logic_row()

**Pattern Added (lines 54-72):**
```python
# ✅ CORRECT: Pass the MODEL CLASS to new_logic_row
request_logic_row = logic_row.new_logic_row(models.SysSupplierReq)  # Pass CLASS
request_row = request_logic_row.row  # Get instance from .row property
request_row.item_id = parent_row.id  # Set attributes on instance
request_logic_row.insert(reason="Create request")  # Insert using logic_row

# ❌ WRONG: Creating instance first
request_row = models.SysSupplierReq()  # Don't create instance yourself
request_logic_row = logic_row.new_logic_row(request_row)  # ❌ TypeError!
```

**Explanation Added:**
- new_logic_row() takes MODEL CLASS as parameter
- Returns LogicRow wrapper with .row property
- Use returned logic_row for .insert(), not plain row

---

### 3. REQUIRED PATTERN: Value Assignment After AI

**Error Fixed:** AI set chosen_unit_price but didn't copy to Item.unit_price

**Pattern Added (lines 74-96):**
```python
# ✅ CORRECT: Explicit value assignment
def event_handler(item_row: models.Item, logic_row: LogicRow):
    supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    supplier_req = supplier_req_logic_row.row
    
    # Set up request
    supplier_req.item_id = item_row.id
    supplier_req.product_id = item_row.product_id
    
    # Insert triggers AI (AI sets chosen_supplier_id and chosen_unit_price)
    supplier_req_logic_row.insert(reason="AI selection")
    
    # CRITICAL: Copy AI result to target row
    item_row.unit_price = supplier_req.chosen_unit_price
    logic_row.log(f"Set Item.unit_price = {item_row.unit_price} from AI")

# ❌ WRONG: Assuming value propagates automatically
# Item.unit_price stays None, causing formula errors downstream
```

**Why Section Added:**
- AI populates request table (SysSupplierReq.chosen_unit_price)
- Target table (Item.unit_price) is separate
- No automatic propagation between tables
- Event handler MUST copy the value explicitly

---

### 4. REQUIRED PATTERN: Type Handling for Database Fields

**Error Fixed:** Decimal type used for foreign key ID fields (SQLite doesn't support)

**Pattern Added (lines 129-152):**
```python
✅ Foreign Key (ID) fields:
- MUST be Python int type for SQLite
- AI returns numeric values as correct type
- chosen_supplier_id, chosen_product_id, etc. → int

✅ Monetary fields:
- Should be Decimal type for precision
- unit_price, unit_cost, amount, total → Decimal
- Utility converts: Decimal(str(value))

✅ The compute_ai_value() utility does this automatically:
if '_id' in field_name or field_name.endswith('_id'):
    value = int(value)  # Foreign keys as int
elif '_price' in field_name or '_cost' in field_name or '_amount' in field_name:
    value = Decimal(str(value))  # Monetary as Decimal
```

**Key Message:**
- compute_ai_value() handles this automatically
- User doesn't need manual type conversion
- Utility introspects column types

---

## Visual Improvements

### Before (Error Recovery Style)
```
❌ WRONG: LogicRow.get_logic_row(row)  # This method does NOT exist!
✅ RIGHT: def handler(row, old_row, logic_row: LogicRow)
```

### After (Positive Pattern Style)
```
=============================================================================
REQUIRED PATTERN: Request Pattern with new_logic_row
=============================================================================

ALWAYS use this pattern to create request objects:

# ✅ CORRECT: Pass the MODEL CLASS to new_logic_row
request_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
request_row = request_logic_row.row
request_logic_row.insert(reason="Create request")

# ❌ WRONG: Creating instance first
request_row = models.SysSupplierReq()
request_logic_row = logic_row.new_logic_row(request_row)  # TypeError!
```

**Changes:**
- ✅ Section headers with clear delimiters
- ✅ "REQUIRED PATTERN" emphasizes mandatory approach
- ✅ Correct example shown FIRST (not as correction)
- ✅ Complete code snippets (not fragments)
- ✅ Explanation of WHY pattern works

---

## Template File Updates

**File:** `docs/training/template_probabilistic_rules.py`

### ItemUnitPriceFromSupplier Function
Added three CRITICAL PATTERNS inline:

1. **Event handler signature pattern**
2. **Creating request objects pattern** (with ✅/❌ examples)
3. **Copying AI results pattern**

### supplier_id_from_ai Function
Added three CRITICAL PATTERNS inline:

1. **Event handler signature** (all three parameters required)
2. **Use introspection utility** (not manual OpenAI code)
3. **Type handling** (automatic via utility)

---

## Readme Updates

**File:** `readme_probabilistic.md`

Replaced "Critical Fixes Required During Generation" section with:

**"Errors Fixed & Training Documentation Updated (v1.4)"**

Each error now documents:
- ❌ **Error**: What went wrong
- ✅ **Fix**: How it was corrected
- 📚 **Training**: Which pattern section was added

Plus new section:
**"Key Documentation Philosophy Applied"**
- ✅ Be explicit about what TO DO
- ✅ Show complete working examples
- ✅ Use visual markers for clarity
- ✅ Explain WHY patterns work
- ✅ Place patterns BEFORE sections that use them

---

## Result

All four errors that occurred during testing now have:
1. **Clear positive instructions** showing correct approach FIRST
2. **Complete working examples** (not fragments)
3. **Visual markers** (✅ CORRECT, ❌ WRONG) for quick scanning
4. **Explanation of WHY** the pattern works
5. **Placement BEFORE** sections that use the pattern

This follows the philosophy: **"Tell them what TO DO, not just what went wrong."**

---

## Files Changed Summary

| File | Lines Added | Purpose |
|------|-------------|---------|
| `logic_bank_api_probabilistic.prompt` | ~150 | Four REQUIRED PATTERN sections |
| `template_probabilistic_rules.py` | ~40 | Inline CRITICAL PATTERNS comments |
| `readme_probabilistic.md` | ~50 | Error documentation with training references |
| `UPDATES_v1.4.md` (this file) | ~250 | Complete change documentation |

**Total:** ~490 lines of explicit positive instruction documentation

---

## Version Control

- Previous: v1.3 (Nov 14, 2025) - Introspection-based utilities
- Current: **v1.4 (Nov 14, 2025)** - Explicit positive patterns
- Next: v1.5 - User testing and refinement based on feedback
