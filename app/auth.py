import requests
from flask import Blueprint, redirect, url_for, session, jsonify, request, make_response
from authlib.integrations.flask_client import OAuth
from .config import Config
from .models import db, User  # Import User model and db instance

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
        },
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    )

@auth_bp.route("/login")
def login():
    """Redirect user to Google for authentication."""
    return oauth.google.authorize_redirect(url_for("auth.google_auth", _external=True))

@auth_bp.route("/google_auth")
def google_auth():
    """Handle Google OAuth callback and store user in database."""
    token = oauth.google.authorize_access_token()
    id_token = token.get("id_token")  # Get Google ID Token

    if not id_token:
        return jsonify({"error": "Authentication failed"}), 401

    # Get user info from Google
    response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
    if response.status_code != 200:
        return jsonify({"error": "Invalid token"}), 401

    user_info = response.json()
    google_id = user_info["sub"]  # Unique Google user ID
    email = user_info["email"]
    first_name = user_info.get("given_name", "Unknown")

    # Check if user exists in the database
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, first_name=first_name)
        db.session.add(user)
        db.session.commit()

    # Store ID Token in an HTTP-only cookie for persistence
    response = make_response(jsonify({"message": "Login successful"}))
    response.set_cookie("google_id_token", id_token, httponly=True, max_age=30 * 24 * 60 * 60)  # 30 days
    session["google_id"] = google_id  # Store user in session

    return response

@auth_bp.route("/user")
def get_user():
    """Return user info if Google ID Token is valid."""
    google_id = session.get("google_id")  # Check session

    if not google_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "google_id": user.google_id,
        "email": user.email,
        "first_name": user.first_name
    })

@auth_bp.route("/logout")
def logout():
    """Logout the user by clearing the ID Token cookie and session."""
    response = make_response(jsonify({"message": "Logout successful"}))
    response.set_cookie("google_id_token", "", expires=0)  # Delete cookie
    session.pop("google_id", None)  # Remove from session
    return response
