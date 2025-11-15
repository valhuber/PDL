# PDL Project - Workflow and Troubleshooting

**Scope:** Project-specific workflows, commands, and troubleshooting for the PDL (Probabilistic Decision Logic) demo application.  
**Related:** See `genai_logic_patterns.md` and `probabilistic_logic_guide.md` for pattern documentation.

---

## Project Overview

**Purpose:** Demonstration of probabilistic (AI-powered) business rules in ApiLogicServer.

**Key Use Case:** Supplier selection with AI optimization
- When Item created with Product that has suppliers
- AI selects optimal supplier based on cost, lead time, world conditions
- Creates audit trail in SysSupplierReq table
- Item.unit_price set to chosen supplier's unit_cost

**Domain Model:**
- Customer → Order → Item → Product
- Product → ProductSupplier → Supplier
- Item → SysSupplierReq (audit table for AI decisions)

---

## restart.sh Workflow

### Purpose
`restart.sh` resets the project to "clean database" state, simulating starting from an existing database before adding logic.

### What It Does
```bash
# 1. Kills running server
lsof -ti:5656 | xargs kill -9

# 2. Resets database to initial state
rm -f database/db.sqlite
sqlite3 database/db.sqlite < database/basic_demo.sql

# 3. Overwrites files from "restart" versions
cp database/models_restart.py database/models.py
cp ui/admin/admin_restart.yaml ui/admin/admin.yaml

# 4. Deletes generated logic files
rm -f logic/logic_discovery/check_credit.py
rm -f logic/logic_discovery/app_integration.py
rm -rf logic/logic_discovery/ai_requests
```

### When to Use
- Testing full workflow from scratch
- Demonstrating logic generation process
- Resetting after failed experiments
- Cleaning up before demo

### ⚠️ Important
This is **intentional design**, not a bug. It's meant to simulate the workflow:
1. Start with existing database
2. Generate deterministic rules
3. Add probabilistic rules
4. Test complete system

---

## Complete Workflow After restart.sh

### Step 1: Kill and Reset
```bash
sh restart.sh x
```

### Step 2: Generate Logic Files

**Create: logic/logic_discovery/check_credit.py**
```python
import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from logic.logic_discovery.ai_requests.supplier_selection import get_supplier_price_from_ai

def declare_logic():
    # Deterministic rules
    Rule.constraint(validate=models.Customer,
        as_condition=lambda row: row.balance <= row.credit_limit,
        error_msg="Balance exceeds credit limit")
    
    Rule.sum(derive=models.Customer.balance, as_sum_of=models.Order.amount_total,
        where=lambda row: row.date_shipped is None)
    
    Rule.sum(derive=models.Order.amount_total, as_sum_of=models.Item.amount)
    
    Rule.formula(derive=models.Item.amount, 
        as_expression=lambda row: row.quantity * row.unit_price)
    
    Rule.count(derive=models.Product.count_suppliers, 
        as_count_of=models.ProductSupplier)
    
    # Probabilistic rule
    def ItemUnitPriceFromSupplier(row: models.Item, old_row, logic_row: LogicRow):
        if row.product.count_suppliers == 0:
            return row.product.unit_price
        return get_supplier_price_from_ai(
            row=row,
            logic_row=logic_row,
            candidates='product.ProductSupplierList',
            optimize_for='fastest reliable delivery while keeping costs reasonable',
            fallback='min:unit_cost'
        )
    
    Rule.formula(derive=models.Item.unit_price, calling=ItemUnitPriceFromSupplier)
```

**Create: logic/logic_discovery/ai_requests/supplier_selection.py**
```python
import database.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule

def get_supplier_price_from_ai(row, logic_row, candidates, optimize_for, fallback):
    """Create audit record and return AI-selected price"""
    sys_supplier_req_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
    sys_supplier_req = sys_supplier_req_logic_row.row
    sys_supplier_req_logic_row.link(to_parent=logic_row)
    sys_supplier_req.product_id = row.product_id
    sys_supplier_req.item_id = row.id
    sys_supplier_req_logic_row.insert(reason="Supplier AI Request")
    return sys_supplier_req.chosen_unit_price

def supplier_id_from_ai(row: models.SysSupplierReq, old_row, logic_row: LogicRow):
    """Event handler - populates audit record with AI decision"""
    if not logic_row.is_inserted():
        return
    
    suppliers = row.product.ProductSupplierList
    if not suppliers:
        return
    
    # Simple fallback: choose min cost
    min_supplier = min(suppliers, key=lambda s: s.unit_cost)
    
    row.chosen_supplier_id = min_supplier.supplier_id
    row.chosen_unit_price = min_supplier.unit_cost
    row.reason = f"Selected supplier {min_supplier.supplier_id} with lowest cost: {min_supplier.unit_cost}"

def declare_logic():
    Rule.early_row_event(on_class=models.SysSupplierReq, calling=supplier_id_from_ai)
```

### Step 3: Add SysSupplierReq to models.py

Add to `database/models.py` (after Product class):
```python
from sqlalchemy import func

class SysSupplierReq(Base):
    __tablename__ = 'sys_supplier_req'
    __bind_key__ = 'None'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(ForeignKey('item.id'), nullable=True)
    product_id = Column(ForeignKey('product.id'), nullable=False)
    chosen_supplier_id = Column(ForeignKey('supplier.id'))
    chosen_unit_price = Column(DECIMAL)
    request = Column(String)
    reason = Column(String)
    created_on = Column(DateTime, server_default=func.now())
    
    item = relationship('Item', foreign_keys=[item_id], back_populates='SysSupplierReqList')
    product = relationship('Product', foreign_keys=[product_id], back_populates='SysSupplierReqList')
    supplier = relationship('Supplier', foreign_keys=[chosen_supplier_id], back_populates='SysSupplierReqList')

# Add to Item class:
SysSupplierReqList = relationship('SysSupplierReq', cascade='all, delete', 
    foreign_keys='[SysSupplierReq.item_id]', back_populates='item')

# Add to Product class:
SysSupplierReqList = relationship('SysSupplierReq', cascade='all, delete',
    foreign_keys='[SysSupplierReq.product_id]', back_populates='product')

# Add to Supplier class:
SysSupplierReqList = relationship('SysSupplierReq', cascade='all, delete',
    foreign_keys='[SysSupplierReq.chosen_supplier_id]', back_populates='supplier')
```

### Step 4: Create Alembic Migration

```bash
# Generate migration
alembic revision --autogenerate -m "add sys_supplier_req audit table"

# ⚠️ CRITICAL: Edit the generated migration file!
# Location: database/alembic/versions/XXXXX_add_sys_supplier_req_audit_table.py
```

**Manual editing required:**
1. Remove ALL `op.alter_column()` statements
2. Remove ALL `op.drop_column()` statements  
3. Keep ONLY `op.create_table('sys_supplier_req', ...)`
4. Simplify `downgrade()` to only `op.drop_table('sys_supplier_req')`

**Why?** Alembic autogenerate detects ALL schema differences, not just new table. This creates 40+ unwanted changes. Manual editing keeps only what you want.

**Apply migration:**
```bash
alembic upgrade head
```

### Step 5: Update Admin UI Configuration

**Update: ui/admin/admin_restart.yaml** (so it survives future restarts)

Update metadata:
```yaml
info:
  number_relationships: 10  # Was 7
  number_tables: 8          # Was 7
```

Add resource (BEFORE `settings:` section):
```yaml
resources:
  # ... existing resources ...
  
  Supplier:
    type: Supplier
    user_key: name
  
  SysSupplierReq:
    attributes:
    - name: id
    - name: item_id
    - name: product_id
    - name: chosen_supplier_id
    - name: chosen_unit_price
      type: DECIMAL
    - name: request
    - name: reason
    - name: created_on
      type: DateTime
    description: Audit table for AI supplier selection requests and results
    info_list: Audit table for AI supplier selection requests and results
    tab_groups:
    - direction: toone
      fks: [item_id]
      label: Item
      resource: Item
    - direction: toone
      fks: [product_id]
      label: Product
      resource: Product
    - direction: toone
      fks: [chosen_supplier_id]
      label: Supplier
      resource: Supplier

settings:  # ⚠️ Must come AFTER all resources
  HomeJS: /admin-app/home.js
```

**⚠️ CRITICAL - tab_groups Configuration:**
- Do NOT add `name` field to tab_groups items
- The `name` field causes admin app to request non-existent relationships
- Admin automatically determines relationship names from foreign keys
- Only use: `direction`, `fks`, `label`, and `resource`

**⚠️ YAML Structure Critical:**
- `SysSupplierReq:` must be at same indent level as other resources (Customer, Item, etc.)
- Must come BEFORE `settings:` section
- If nested inside `settings:`, admin app won't recognize it as a resource

### Step 6: Start Server and Test

```bash
# Activate venv
source /Users/val/dev/ApiLogicServer/ApiLogicServer-dev/build_and_test/ApiLogicServer/venv/bin/activate

# Start server
python api_logic_server_run.py
```

**Test Item creation:**
```bash
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
```

**Expected:**
- Item created with unit_price from AI
- amount = quantity * unit_price
- Order.amount_total updated
- Customer.balance updated
- SysSupplierReq record created

**Verify audit trail:**
```bash
curl -s http://localhost:5656/api/SysSupplierReq | python -m json.tool
```

**Check admin app:**
- Open http://localhost:5656
- Navigate to SysSupplierReq in left menu
- Should see audit records with supplier selections

---

## Common Issues and Solutions

### Issue 1: Import Error - "RuleBank has no attribute..."

**Error:**
```
AttributeError: type object 'RuleBank' has no attribute 'early_row_event'
```

**Cause:** Wrong import - using internal `RuleBank` class instead of public `Rule` API.

**Solution:**
```python
# ❌ WRONG
from logic_bank.rule_bank.rule_bank import RuleBank

# ✅ CORRECT
from logic_bank.logic_bank import Rule
```

### Issue 2: "Session is already flushing"

**Error:**
```
sqlalchemy.exc.InvalidRequestError: Session is already flushing
```

**Cause:** Using `session.add()` + `session.flush()` inside formula during flush cycle.

**Solution:** Use LogicBank triggered insert:
```python
# ❌ WRONG
audit = models.SysSupplierReq(...)
logic_row.session.add(audit)
logic_row.session.flush()

# ✅ CORRECT
audit_logic_row = logic_row.new_logic_row(models.SysSupplierReq)
audit_logic_row.insert(reason="AI")
```

### Issue 3: Alembic Generates 40+ Unwanted Changes

**Problem:** `alembic revision --autogenerate` creates ALTER statements for unrelated tables.

**Solution:** Manually edit migration file:
1. Keep only `op.create_table('sys_supplier_req', ...)`
2. Remove all `op.alter_column()` statements
3. Remove all `op.drop_column()` statements
4. Simplify `downgrade()` to `op.drop_table('sys_supplier_req')`

### Issue 4: Admin App Not Showing SysSupplierReq

**Symptoms:**
- API works: `curl http://localhost:5656/api/SysSupplierReq` returns data
- Admin UI doesn't show table in navigation

**Causes & Solutions:**

**A. Missing from admin.yaml:**
- Add SysSupplierReq to `ui/admin/admin_restart.yaml`
- Copy to `ui/admin/admin.yaml` OR run `sh restart.sh x`

**B. Wrong YAML structure:**
```yaml
# ❌ WRONG - nested inside settings
settings:
  HomeJS: /admin-app/home.js
  SysSupplierReq:
    attributes: ...

# ✅ CORRECT - at resource level
resources:
  Supplier:
    user_key: name
  SysSupplierReq:
    attributes: ...
settings:
  HomeJS: /admin-app/home.js
```

**C. Browser cache:**
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Or use incognito/private window

**Verify YAML structure:**
```bash
curl -s http://localhost:5656/ui/admin/admin.yaml | grep -E "^  [A-Z]|^settings:"
```

Should show all resources BEFORE `settings:`.

### Issue 5: Admin App Shows No Rows or "Invalid Relationship" Errors

**Symptoms:**
- Admin app shows table in navigation
- Clicking on table shows no rows or errors
- Server log shows: `Generic Error: Invalid Relationship 'ItemList'`
- API works when tested directly with curl

**Root Cause:**
The `tab_groups` configuration in admin.yaml has incorrect `name` fields that don't match actual relationship names in the model.

**Example Error:**
```yaml
# ❌ WRONG - 'name' field causes admin to request non-existent relationships
tab_groups:
- direction: toone
  fks: [item_id]
  label: Item
  name: ItemList      # ❌ This causes admin to request 'ItemList' relationship
  resource: Item
```

Admin app tries to include `ItemList` relationship, but the actual relationship name is `item` (lowercase, singular).

**Solution:**
Remove the `name` field from tab_groups. The admin app will automatically determine the correct relationship name from the foreign key.

```yaml
# ✅ CORRECT - no 'name' field
tab_groups:
- direction: toone
  fks: [item_id]
  label: Item         # Label is just for display
  resource: Item      # Resource to navigate to
- direction: toone
  fks: [product_id]
  label: Product
  resource: Product
- direction: toone
  fks: [chosen_supplier_id]
  label: Supplier
  resource: Supplier
```

**Fix both files:**
1. Edit `ui/admin/admin.yaml` - remove `name` fields from SysSupplierReq tab_groups
2. Edit `ui/admin/admin_restart.yaml` - same fix (so it persists after restart.sh)
3. Restart server

**Verification:**
```bash
# Should show data without errors
curl http://localhost:5656/api/SysSupplierReq

# Check server log - should have no "Invalid Relationship" errors
tail -50 server.log | grep -i error
```

### Issue 6: Logic Files Not Loading

**Symptom:** Server starts but rules don't fire.

**Check files exist:**
```bash
ls -la logic/logic_discovery/
ls -la logic/logic_discovery/ai_requests/
```

**If missing:** Regenerate files (see Step 2 above).

**Check for syntax errors:**
```bash
python -m py_compile logic/logic_discovery/check_credit.py
python -m py_compile logic/logic_discovery/ai_requests/supplier_selection.py
```

### Issue 7: restart.sh Deleted My Changes

**This is intentional!** `restart.sh` resets to clean state.

**To preserve changes:**
- Edit `database/models_restart.py` (not models.py)
- Edit `ui/admin/admin_restart.yaml` (not admin.yaml)
- Logic files WILL be deleted - regenerate after restart

**Workflow:**
1. Make changes to `_restart` versions
2. Run `sh restart.sh x`
3. Regenerate logic files
4. Run alembic migration
5. Test

---

## Project-Specific Files

### Source Files (Survive restart.sh)
- `database/models_restart.py` → copied to `database/models.py`
- `database/basic_demo.sql` → loaded into `database/db.sqlite`
- `ui/admin/admin_restart.yaml` → copied to `ui/admin/admin.yaml`

### Generated Files (Deleted by restart.sh)
- `logic/logic_discovery/check_credit.py`
- `logic/logic_discovery/app_integration.py`
- `logic/logic_discovery/ai_requests/` (entire folder)

### Runtime Files
- `database/db.sqlite` - SQLite database
- `ui/admin/admin.yaml` - Admin UI configuration (served)
- `database/models.py` - SQLAlchemy models (runtime)

---

## Testing Checklist

After completing workflow:

- [ ] Server starts without errors
- [ ] Logic log shows rules loaded (check console)
- [ ] No "Invalid Relationship" errors in server log
- [ ] API endpoints respond:
  - `curl http://localhost:5656/api/Customer`
  - `curl http://localhost:5656/api/Product`
  - `curl http://localhost:5656/api/Supplier`
  - `curl http://localhost:5656/api/SysSupplierReq`
- [ ] Item creation works (POST to /api/Item)
- [ ] unit_price computed correctly
- [ ] amount = quantity * unit_price
- [ ] Order.amount_total updated
- [ ] Customer.balance updated
- [ ] SysSupplierReq audit record created
- [ ] Admin app shows all tables including SysSupplierReq
- [ ] Can navigate to SysSupplierReq in admin UI
- [ ] SysSupplierReq table shows rows (not empty)
- [ ] Can see audit records with supplier selections
- [ ] Can click on related Item, Product, Supplier in tab groups

---

## Quick Commands Reference

```bash
# Reset project
sh restart.sh x

# Check files
ls -la logic/logic_discovery/
ls -la logic/logic_discovery/ai_requests/

# Database operations
sqlite3 database/db.sqlite ".schema sys_supplier_req"
sqlite3 database/db.sqlite "SELECT * FROM sys_supplier_req;"

# Alembic
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic current
alembic history

# Server
python api_logic_server_run.py
lsof -ti:5656 | xargs kill -9  # Kill server

# Test API
curl http://localhost:5656/api/SysSupplierReq
curl -X POST http://localhost:5656/api/Item -H "Content-Type: application/vnd.api+json" -d '{...}'

# Verify admin YAML
curl -s http://localhost:5656/ui/admin/admin.yaml | grep -E "^  [A-Z]|^settings:"
```

---

## Summary

**This Project (PDL):**
- restart.sh resets to clean state (intentional)
- Must regenerate logic files after restart
- Must update models_restart.py and admin_restart.yaml (not runtime versions)
- Must manually edit alembic migrations (remove unwanted ALTER statements)
- Must maintain correct YAML structure in admin config

**Key Difference from Standard Projects:**
- Standard: Logic files persist, edit in place
- PDL: Logic files regenerated, demonstrates workflow

**Workflow Pattern:**
1. Edit source files (_restart versions)
2. Run restart.sh
3. Regenerate logic
4. Migrate database
5. Test complete system

This simulates the real-world scenario of adding probabilistic rules to an existing database.
