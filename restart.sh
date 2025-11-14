#!/bin/bash


# normally true, use false for skipping long clone during testing 
clonedocs=true

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

cp database/db_restart.sqlite database/db.sqlite
rm logic/logic_discovery/check_credit.py
rm logic/logic_discovery/app_integration.py