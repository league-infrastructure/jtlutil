import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import sqlitedict
from dotenv import dotenv_values
from flask import Flask, current_app, session, g
from flask_login import LoginManager, UserMixin
from flask_session import Session
from jtlutil.config import get_config, get_config_tree


class User(UserMixin):
    """Represents a user with attributes fetched from Google OAuth."""
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = user_data['id']
        self.primary_email = user_data['primaryEmail']
        self.groups = user_data.get('groups', [])
        self.org_unit = user_data.get('orgUnitPath', '')
        self._is_admin = user_data.get('isAdmin', False)

    @property
    def is_league(self):
        """Return true if the user is a League user."""
        return self.primary_email.endswith('@jointheleague.org')

    @property
    def is_student(self):
        """Return true if the user is a student."""
        return self.primary_email.endswith('@students.jointheleague.org')

    @property
    def is_admin(self):
        return self._is_admin and self.is_league

    @property
    def is_staff(self):
        return self.is_league and 'staff@jointheleague.org' in self.groups
        
    @property
    def role(self):
        if self.is_admin:
            return "admin"
        elif self.is_staff:
            return "staff"
        elif self.is_student:
            return "student"
        elif self.is_league:
            return "league"
        else:
            return "Public"
        
    @property
    def is_public(self):
        return not self.is_league
        
    def get_full_user_info(self):
        return self.user_data



def is_running_under_gunicorn():
    """Return true if the app is running under Gunicorn, 
    which implies it is in production"""
    
    return "gunicorn" in os.environ.get(
        "SERVER_SOFTWARE", ""
    ) or "gunicorn" in os.environ.get("GUNICORN_CMD_ARGS", "")


def get_payload(request) -> dict:
    """Get the payload from the request, either from the form or json"""
        
    if request.content_type == "application/json":
        payload = request.get_json()
    else:
        payload = request.form.to_dict()

    # add date/time in iso format
    payload["_created"] = datetime.now().isoformat()

    return payload


def init_logger(app):
    """Initialize the logger for the app, either production or debug"""
    if is_running_under_gunicorn():
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
        app.logger.info("Logger initialized for gunicorn")
    else:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info("Logger initialized for flask")


def configure_config(app):
        # Determine if we're running in production or development
    if is_running_under_gunicorn():
        config_file_name = "prod.env"
    else:
        config_file_name = "devel.env"
    
        # Bypass the HTTPS requirement, because we are either running in development, 
        # or behind a proxy than handles https. May be better to set the X-Forwarded-Proto, 
        # but that looks really complicated. 
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 

    # Load configuration
    config = get_config(config_file_name)
    
    # Set the Flask secret key
    app.secret_key = config["SECRET_KEY"]
    
    # Resolve the path to the secrets file
    if 'SECRETS_FILE_NAME' in config:
        config["SECRETS_FILE"] = (Path(config['__CONFIG_PATH']).parent / config['SECRETS_FILE_NAME']).resolve()

    # Store 
    
    app.app_config = config
    
    return config


def configure_config_tree(app):
        # Determine if we're running in production or development
    if is_running_under_gunicorn():
        deploy = "prod"
        config_dir = '/app'
    else:
        deploy = "devel"
        config_dir = Path().cwd()
    
        # Bypass the HTTPS requirement, because we are either running in development, 
        # or behind a proxy than handles https. May be better to set the X-Forwarded-Proto, 
        # but that looks really complicated. 
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 

    config = get_config_tree(config_dir, deploy_name='devel')

    # Set the Flask secret key
    app.secret_key = config["SECRET_KEY"]
    
    # Resolve the path to the secrets file
    if 'SECRETS_FILE_NAME' in config:
        config["SECRETS_FILE"] = (Path(config['__CONFIG_PATH']).parent / config['SECRETS_FILE_NAME']).resolve()

    # Store 
    
    app.app_config = config
    
    return config


def configure_app_dir(app):
    
      # Configure the appdir

    app.app_config.app_dir = app_dir = Path(app.app_config.APP_DIR)
    
    if not app_dir.exists():
        app_dir.mkdir(parents=True)
        
    app.app_config.db_dir = db_dir = app_dir / "db"
    if not db_dir.exists():
        db_dir.mkdir()
        
    return app_dir, db_dir

def setup_sqlite_sessions(app, session_expire_time=60*60*24*1): 
        # Setup sessions
        
    
    db_path = app.app_config.db_dir / "sessions.db"
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    Session(app) # Initialize the session
    
    # Set session expiration time
    #app.config['PERMANENT_SESSION_LIFETIME'] = session_expire_time
    app.config['SESSION_CLEANUP_N_REQUESTS'] = 100
    app.config['SESSION_SERIALIZATION_FORMAT'] = 'json'
    app.config['SESSION_COOKIE_SECURE'] = True
    
    
def insert_query_arg(url, key, value):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params[key] = value
    new_query_string = urlencode(query_params, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query_string))


