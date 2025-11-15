#!/bin/bash


# sh restart.sh x

if [ $# -eq 0 ]
  then
    echo " "
    # echo "shell: $SHELL"
    echo "Cleanup to repeat logic creation\n"
    echo " "
    echo "   > sh restart.sh x"
    echo " "
    exit 0
  else
    ls
    echo " "
    read -p "Confirm restart (delete files, replace DB, etc)> "
fi

# cp database/db_restart.sqlite database/db.sqlite
rm -f database/db.sqlite;     
sqlite3 database/db.sqlite < database/basic_demo.sql
cp database/models_restart.py database/models.py
cp ui/admin/admin_restart.yaml ui/admin/admin.yaml

rm logic/logic_discovery/check_credit.py
rm logic/logic_discovery/app_integration.py