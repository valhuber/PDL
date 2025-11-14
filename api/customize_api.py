import logging
import api.system.api_utils as api_utils
import safrs
from flask import request, jsonify, send_from_directory
from safrs import jsonapi_rpc
from database import models
from api.landing_page import add_landing_page

app_logger = logging.getLogger(__name__)


def expose_services(app, api, project_dir, swagger_host: str, PORT: str):
    """ Customize API - new end points for services 
    
        Brief background: see readme_customize_api.md

        Your Code Goes Here
    
    """
    
    from api.api_discovery.auto_discovery import discover_services
    discover_services(app, api, project_dir, swagger_host, PORT)
    add_landing_page(app, api)
    
