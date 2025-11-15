import datetime
import json
import logging
import os
import sys
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from werkzeug.utils import secure_filename
import database.models as models
from database.models import *

app_logger = logging.getLogger(__name__)
declare_logic_message = "ALERT:  *** No Rules Yet ***"  # printed in api_logic_server.py


def declare_logic():
    ''' Declarative multi-table derivations and constraints, extensible with Python.
 
    Brief background: see readme_declare_logic.md
    
    Your Code Goes Here - Use code completion (Rule.) to declare rules
    '''
    from logic_bank.exec_row_logic.logic_row import LogicRow
    import api.system.opt_locking.opt_locking as opt_locking
    from logic_bank.extensions.rule_extensions import RuleExtension
    from logic_bank.logic_bank import DeclareRule, Rule, LogicBank
    from logic_bank.rule_bank.rule_bank import Singleton, RuleBank
    from security.system.authorization import Grant, Security
    from logic.load_verify_rules import load_verify_rules

    if os.environ.get("WG_PROJECT"):
        # Inside WG: Load rules from json export
        load_verify_rules()
    else:
        # Outside WG: load declare_logic function
        from logic.logic_discovery.auto_discovery import discover_logic
        discover_logic()

    app_logger.debug("..logic/declare_logic.py (logic == rules + code)")

