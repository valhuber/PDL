#!/usr/bin/env python3


api_logic_server__version = '14.00.47'
api_logic_server_created__on = 'December 30, 2024 07:25:16'
api_logic_server__host = 'localhost'
api_logic_server__port = '5656'

start_up_message = "normal start"

import os, logging, logging.config, sys, yaml  # failure here means venv probably not set
from flask_sqlalchemy import SQLAlchemy
import json
from pathlib import Path
from config.config import Args
from config import server_setup

current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)
project_dir = str(current_path)
project_name = os.path.basename(os.path.normpath(current_path))

if server_setup.is_docker():
    sys.path.append(os.path.abspath('/home/api_logic_server'))

logic_alerts = True
""" Set False to silence startup message """
declare_logic_message = ""
declare_security_message = "ALERT:  *** Security Not Enabled ***"

os.chdir(project_dir)  # so admin app can find images, code
import api.system.api_utils as api_utils
logic_logger_activate_debug =  True
""" True prints all rules on startup """

from typing import TypedDict
import safrs  # fails without venv - see https://apilogicserver.github.io/Docs/Project-Env/
from safrs import ValidationError, SAFRSBase, SAFRSAPI as _SAFRSAPI
from logic_bank.logic_bank import LogicBank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_type.constraint import Constraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from flask import Flask, redirect, send_from_directory, send_file
from flask_cors import CORS
import ui.admin.admin_loader as AdminLoader
from security.system.authentication import configure_auth
import logging


app_logger = server_setup.logging_setup()
app_logger.setLevel(logging.DEBUG)

# ==================================
#        MAIN CODE
# ================================== 

if not os.environ.get('VERIFY_RULES') == 'True':
    app_logger.warning(f"VERIFY_RULES not set!\n"*20)
    os.environ['VERIFY_RULES'] = 'True'
    

flask_app = Flask("API Logic Server", template_folder='ui/templates')  # templates to load ui/admin/admin.yaml

args = server_setup.get_args(flask_app)                        # creation defaults

import config.config as config
flask_app.config.from_object(config.Config)
app_logger.debug(f"\nConfig args: \n{args}")                    # config file (e.g., db uri's)

args.get_cli_args(dunder_name=__name__, args=args)
app_logger.debug(f"\nCLI args: \n{args}")                       # api_logic_server_run cl args

flask_app.config.from_prefixed_env(prefix="APILOGICPROJECT")    # env overrides (e.g., docker)
app_logger.debug(f"\nENV args: \n{args}\n\n")

server_setup.validate_db_uri(flask_app)
server_setup.api_logic_server_setup(flask_app, args)

exit()