#!/bin/bash

# ====================================================================
# restart.sh - Reset PDL Demo to Clean State
# ====================================================================
# 
# PURPOSE:
# Simulates starting with an EXISTING customer database (no logic, no alembic).
# This demonstrates the workflow of adding deterministic + probabilistic logic
# to an existing database that has no API Logic Server artifacts.
#
# WHAT IT DOES:
# 1. Stops running server
# 2. Creates BRAND NEW database from basic_demo.sql (vanilla customer DB)
# 3. Resets models.py and admin.yaml to base versions (no audit tables)
# 4. Deletes all generated logic files (simulates "before adding logic")
#
# AFTER RUNNING THIS:
# - Database has NO sys_supplier_req table (vanilla state)
# - Database has NO alembic_version table (no migration history)
# - Models.py has NO SysSupplierReq class
# - Admin.yaml has NO SysSupplierReq resource
# - Logic files deleted (check_credit.py, ai_requests/)
#
# AFTER RUNNING restart.sh, ASK COPILOT TO:
# 1. Add SysSupplierReq class to database/models_restart.py (with relationships)
# 2. Update ui/admin/admin_restart.yaml with SysSupplierReq resource
# 3. Create logic/logic_discovery/check_credit.py (deterministic + conditional AI)
# 4. Create logic/logic_discovery/ai_requests/supplier_selection.py (Request Pattern)
# 5. Create sys_supplier_req table in database (via SQL)
#
# THEN:
# 6. Start server: python api_logic_server_run.py
# 7. Test: curl -X POST http://localhost:5656/api/Item ...
# 8. Verify audit: curl http://localhost:5656/api/SysSupplierReq
#
# See readme_probabilistic.md for complete instructions.
#
# USAGE: sh restart.sh x
# ====================================================================


# Stop any running server to avoid file locking issues
lsof -ti:5656 | xargs kill -9 2>/dev/null
sleep 2

# Create BRAND NEW database from basic_demo.sql
# This simulates a vanilla customer database with NO logic, NO alembic
rm -f database/db.sqlite
sqlite3 database/db.sqlite < database/basic_demo.sql

# Reset models.py and admin.yaml to base versions (no audit tables)
cp database/models_restart.py database/models.py
cp ui/admin/admin_restart.yaml ui/admin/admin.yaml

# Delete generated logic files (simulates "before adding logic")
rm -f logic/logic_discovery/check_credit.py
rm -f logic/logic_discovery/app_integration.py
rm -rf logic/logic_discovery/ai_requests

echo "\nRestart complete. Database and code reset to clean state.\n"