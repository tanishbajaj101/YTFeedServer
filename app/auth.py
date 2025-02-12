import requests
from flask import Blueprint, redirect, url_for, session, jsonify, request, make_response
from authlib.integrations.flask_client import OAuth
from .config import Config

auth_bp = Blueprint("auth", __name__)

oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth and register Google as a provider."""
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        access_token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        userinfo_endpoint="https://www.googleapis.com/oauth2/v1/userinfo",
        client_kwargs={
            "scope": "openid email profile",
            "redirect_uri": "http://https://ytfeedserver.onrender.com/auth/google_auth",  # Ensure this matches your Google OAuth redirect URI
        },
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",  # Fetch metadata, including jwks_uri
    )

@auth_bp.route("/login")
def login():
    """Redirect user to Google for authentication."""
    return oauth.google.authorize_redirect(url_for("auth.google_auth", _external=True))


@auth_bp.route("/google_auth")
def google_auth():
    """Handle Google OAuth callback and store ID Token in a persistent cookie."""
    token = oauth.google.authorize_access_token()
    id_token = token.get("id_token")  # Get Google ID Token

    if not id_token:
        return jsonify({"error": "Authentication failed"}), 401

    # Store ID Token in an HTTP-only cookie for persistence
    response = make_response(jsonify({"message": "Login successful"}))
    response.set_cookie("google_id_token", id_token, httponly=True, max_age=30 * 24 * 60 * 60)  # 30 days
    return response


@auth_bp.route("/user")
def get_user():
    """Return user info if Google ID Token is valid."""
    id_token = request.cookies.get("google_id_token")

    if not id_token:
        return jsonify({"error": "Unauthorized"}), 401

    # Verify ID Token with Google
    response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
    if response.status_code != 200:
        return jsonify({"error": "Invalid or expired token"}), 401

    user_data = response.json()
    return jsonify({"user": user_data})


@auth_bp.route("/logout")
def logout():
    """Logout the user by clearing the ID Token cookie."""
    response = make_response(jsonify({"message": "Logout successful"}))
    response.set_cookie("google_id_token", "", expires=0)  # Delete cookie
    return response
