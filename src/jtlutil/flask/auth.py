import uuid

import requests
from flask import (current_app, flash, get_flashed_messages, 
                   redirect, render_template, request, session, url_for, g)
from flask import Blueprint
from flask_login import (current_user, login_user as fl_login_user, logout_user, LoginManager)
from jtlutil.flask.flaskapp import insert_query_arg
from jtlutil.jwtencode import decrypt_token, encrypt_token
import logging
from .flaskapp import User

auth_bp = Blueprint("auth", __name__)

logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.init_app(auth_bp)
login_manager.login_view = 'auth.login'
login_manager = auth_bp.login_manager = login_manager

@auth_bp.login_manager.user_loader
def load_lm_user(user_id):
    current_app.logger.info(f"Request to load  user from login manager with ID: {user_id}")

    if "user" in session:
        current_app.logger.info(f"User data already in session")
        user_data = session["user"]
        return User(user_data)

    return None


def get_session_user(app,session_id):
    """Get user data from the auth server, for a session id."""
    enc_key = bytes.fromhex(current_app.app_config['ENCRYPTION_KEY'])
    
    t = encrypt_token(session_id, enc_key)
    
    auth_server_url = current_app.app_config["AUTH_SERVER_URL"]
    user_endpoint = f"{auth_server_url}/user"
    params = {"ssoid": t}
    
    response = requests.get(user_endpoint, params=params)
    
    if response.status_code == 200:
        user_data = response.json()
        
        return user_data
    else:
        current_app.logger.error(f"Failed to fetch user data: {response.status_code} {response.text}")
        return None

def login_user(user):
    
    fl_login_user(user)
    session["user"] = user.user_data
    return True

def load_user(app):
    """When the authentication server redirects back to the app here, it will include a query
    parameter `ssoid` which is the encrypted session ID. This function decrypts
    the session ID and loads the user data into the session. We can look up this
    session id in the cache and load the user data into the session.
    """

    ssoid = request.args.get("ssoid")
    
    if ssoid:
        current_app.logger.info(f"Loading user with ssoid: {ssoid}")
        # Decrypt it
        session_id = decrypt_token(
            ssoid, bytes.fromhex(app.app_config["ENCRYPTION_KEY"])
        )
        
        user_data = get_session_user(app, session_id)

        login_user(User(user_data))
        
        

@auth_bp.route("/auth/ga_login")
def jtl_ga_auth_login():

    next = request.args.get("next", url_for("index", _external=True))
    
    login_url = insert_query_arg(
        current_app.app_config["AUTH_SERVER_URL"] + "/login",
        "redirect", next,
    )
    current_app.logger.info(f"Redirecting to login server at {login_url}")

    get_flashed_messages()

    return redirect(login_url)




@auth_bp.route("/auth/logout")
def jtl_auth_logout():

    next = request.args.get("next", url_for("index", _external=True))

    if current_user.is_authenticated:
        current_app.logger.info(f"User {current_user.id} logging out")

    #uncache_user(session["session_id"])
    session.clear()
    logout_user()
    current_app.logger.info(f"ser logged out")

    flash("You have been logged out.", "info")
    return redirect(next)

