# Probabilistic Rules Refactoring Summary

## Date: November 15, 2025

## Key Changes

### 1. Architecture Restructure

**Before:**
```
logic/
├── logic_discovery/
│   └── check_credit.py (173 lines - mixed concerns)
└── system/
    └── ai_value_computation.py
```

**After:**
```
logic/
├── logic_discovery/
│   ├── check_credit.py (127 lines - business logic only)
│   └── ai_requests/
│       ├── __init__.py
│       └── supplier_selection.py (95 lines - reusable AI handler)
└── system/
    └── ai_value_computation.py
```

### 2. Mental Model Shift

**Old Pattern: Early Event + Formula**
```python
# Two separate rules
Rule.early_row_event(on_class=models.Item, calling=ItemUnitPriceFromSupplier)
Rule.formula(derive=models.Item.unit_price, as_expression=lambda row: ...)

# Event handler had to manually set item.unit_price
def ItemUnitPriceFromSupplier(...):
    # ... create request ...
    item_row.unit_price = supplier_req.chosen_unit_price  # Side effect
```

**New Pattern: Formula with Callable**
```python
# Single rule - matches reference implementation
Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)

# Function returns the computed value
def ItemUnitPriceFromSupplier(...):
    return get_supplier_price_from_ai(...)  # Clean return value
```

### 3. AI as Value Computation

**Core Principle:** AI computes and returns a value; audit details stay in request table.

```python
# Business logic calls AI handler
return get_supplier_price_from_ai(
    row=row,
    logic_row=logic_row,
    candidates='product.ProductSupplierList',
    optimize_for='fastest reliable delivery...',
    fallback='min:unit_cost'
)

# AI handler encapsulates Request Pattern
def get_supplier_price_from_ai(...):
    # Create SysSupplierReq audit object
    # Trigger AI event (populates audit fields)
    # Return the computed value
    return sys_supplier_req.chosen_unit_price
```

**Audit Trail:**
- `chosen_supplier_id` - Working value (which supplier)
- `chosen_unit_price` - **Returned value** (what the caller needs)
- `reason` - Working value (why that supplier)
- `request` - Working value (full context)

### 4. Auto-Discovery Enhancement

**Fixed Bug:** Nested folders weren't discovered correctly
```python
# Before (broken for nested folders)
spec = importlib.util.spec_from_file_location("module.name", logic_path.joinpath(file))

# After (works recursively)
file_path = Path(root).joinpath(file)
spec = importlib.util.spec_from_file_location("module.name", file_path)
```

**Result:** `logic/logic_discovery/ai_requests/` now auto-discovered

### 5. Code Simplification

**check_credit.py:**
- 173 → 127 lines (27% reduction)
- Removed Request Pattern boilerplate
- Cleaner rule declarations (1-2 lines each)
- Clear separation: business logic vs AI computation

**template_probabilistic_rules.py:**
- 307 → 168 lines (45% reduction)
- Reflects new architecture
- Emphasizes patterns over implementation details

## Benefits

### Enterprise Scale
✅ **Reusability:** Other use cases (inventory, fulfillment) can call `get_supplier_price_from_ai()`  
✅ **Maintainability:** Update supplier logic once in `ai_requests/`  
✅ **Testability:** AI handlers independently testable  
✅ **Scalability:** Clear pattern for adding more AI handlers

### Code Quality
✅ **Separation of concerns:** Business logic ↔ AI handlers ↔ Framework utilities  
✅ **Clean abstraction:** Use cases don't know about Request Pattern  
✅ **Self-documenting:** Rule declarations readable without verbose comments  
✅ **Pattern consistency:** Matches reference implementation

### Developer Experience
✅ **Clearer intent:** Formula returns value (not side effects)  
✅ **Less boilerplate:** 27% reduction in use case file  
✅ **Better organization:** Logical folder structure  
✅ **Easy to extend:** Add new AI handlers to `ai_requests/`

## Migration Guide

### For Existing Code

1. **Move AI handlers to ai_requests/**
   ```bash
   mkdir logic/logic_discovery/ai_requests
   # Move reusable AI functions there
   ```

2. **Update imports**
   ```python
   from logic.logic_discovery.ai_requests.supplier_selection import get_supplier_price_from_ai
   ```

3. **Simplify use case logic**
   - Replace early_row_event + formula with single formula
   - Call AI handler function directly
   - Return the computed value

4. **Add declare_logic() to AI handlers**
   ```python
   def declare_logic():
       Rule.early_row_event(on_class=models.SysSupplierReq, calling=supplier_id_from_ai)
   ```

### For New AI Handlers

1. Create module in `logic/logic_discovery/ai_requests/`
2. Implement function that returns computed value
3. Implement event handler that populates audit fields
4. Add `declare_logic()` to register rules
5. Auto-discovery handles the rest

## File-by-File Summary

| File | Before | After | Change | Notes |
|------|--------|-------|--------|-------|
| check_credit.py | 173 | 127 | -27% | Business logic only |
| supplier_selection.py | - | 95 | NEW | Reusable AI handler |
| template_probabilistic_rules.py | 307 | 168 | -45% | Reflects new patterns |
| auto_discovery.py | - | - | Fixed | Nested folder support |

**Total code:** 173 → 222 lines (+49 lines)  
**But:** +95 lines of reusable infrastructure  
**Net use case code:** 173 → 127 (-46 lines per use case)

## Key Takeaways

1. **Formula with callable** > early event + formula (matches reference)
2. **AI returns value** > AI sets value via side effect
3. **Reusable AI handlers** > inline Request Pattern code
4. **Auto-discovery** handles nested folders
5. **Concise rules** > verbose comments (code speaks for itself)

## Next Steps

- [ ] Update other use cases to follow this pattern
- [ ] Add more AI handlers (price_optimization, route_selection)
- [ ] Update README with new architecture
- [ ] Update training docs (logic_bank_api_probabilistic.prompt)
