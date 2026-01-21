"""
US-13: Authentication and Protected Routes
US-16: JWT Token Management via Website
"""
from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from datetime import timedelta
import pyotp
import qrcode
import io
import base64

# In-memory user storage (replace with database in production)
USERS = {
    "admin": {
        "password": "password",
        "email": "admin@geoscope.com",
        "first_name": "Admin",
        "last_name": "User",
        "otp_secret": None,
        "is_2fa_enabled": False
    },
    "full_user": {
        "password": "password",
        "email": "full@geoscope.com",
        "first_name": "Full",
        "last_name": "Access",
        "otp_secret": None,
        "is_2fa_enabled": False
    },
    "none_user": {
        "password": "password",
        "email": "none@geoscope.com",
        "first_name": "No",
        "last_name": "Access",
        "otp_secret": None,
        "is_2fa_enabled": False
    },
    "partial_user": {
        "password": "password",
        "email": "partial@geoscope.com",
        "first_name": "Partial",
        "last_name": "Access",
        "otp_secret": None,
        "is_2fa_enabled": False
    }
}

def register(app):
    """
    Registers authentication routes with JWT token management.
    Includes login, signup, token refresh, and token validation endpoints.
    """

    @app.route('/signup', methods=['POST'])
    def signup():
        """
        US-16: User registration endpoint
        Creates new user account and stores in memory
        """
        try:
            data = request.json
            username = data.get("username")
            password = data.get("password")
            email = data.get("email")
            first_name = data.get("first_name")
            last_name = data.get("last_name")

            # Validate required fields
            if not all([username, password, email, first_name, last_name]):
                return jsonify({"msg": "All fields are required"}), 400

            # Check if user already exists
            if username in USERS:
                return jsonify({"msg": "Username already exists"}), 409

            # Store new user
            USERS[username] = {
                "password": password,
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }

            return jsonify({
                "msg": "User created successfully",
                "username": username
            }), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/login', methods=['POST'])
    def login():
        """
        US-16: Enhanced login with access and refresh tokens
        Returns both tokens with configurable expiration times
        """
        try:
            username = request.json.get("username")
            password = request.json.get("password")
            
            # Validate credentials
            if username not in USERS or USERS[username]["password"] != password:
                return jsonify({"msg": "Bad username or password"}), 401

            # Check if 2FA is required
            if USERS[username].get("is_2fa_enabled"):
                return jsonify({
                    "msg": "2FA required",
                    "two_step_required": True,
                    "username": username
                }), 200

            # Create tokens with custom expiration
            access_token = create_access_token(
                identity=username,
                expires_delta=timedelta(hours=1)  # 1 hour expiry
            )
            refresh_token = create_refresh_token(
                identity=username,
                expires_delta=timedelta(days=30)  # 30 day expiry
            )

            # Return user info along with tokens
            user_info = {
                "username": username,
                "email": USERS[username]["email"],
                "first_name": USERS[username]["first_name"],
                "last_name": USERS[username]["last_name"]
            }

            return jsonify({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user_info
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """
        US-16: Token refresh endpoint
        Accepts refresh token and returns new access token
        """
        try:
            current_user = get_jwt_identity()
            new_access_token = create_access_token(
                identity=current_user,
                expires_delta=timedelta(hours=1)
            )
            return jsonify({
                "access_token": new_access_token
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/token/validate', methods=['POST'])
    @jwt_required()
    def validate_token():
        """
        US-16: Token validation endpoint
        Checks if current token is valid and returns expiration info
        """
        try:
            current_user = get_jwt_identity()
            jwt_data = get_jwt()
            
            return jsonify({
                "valid": True,
                "user": current_user,
                "exp": jwt_data.get("exp"),
                "iat": jwt_data.get("iat")
            }), 200
        except Exception as e:
            return jsonify({
                "valid": False,
                "msg": str(e)
            }), 401

    @app.route('/protected', methods=['GET'])
    @jwt_required()
    def protected():
        """
        US-13: Protected endpoint requiring valid JWT
        """
        try:
            current_user = get_jwt_identity()
            return jsonify({
                "msg": "Given valid token, when used, then data returned.",
                "user": current_user,
                "data": "Top Secret Info"
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/2fa/setup', methods=['POST'])
    @jwt_required()
    def setup_2fa():
        """
        Generate a TOTP secret and QR code for the user.
        """
        try:
            username = get_jwt_identity()
            if username not in USERS:
                return jsonify({"msg": "User not found"}), 404
            
            secret = pyotp.random_base32()
            USERS[username]["otp_secret"] = secret
            
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(name=USERS[username]["email"], issuer_name="GeoScope")
            
            img = qrcode.make(provisioning_uri)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return jsonify({
                "secret": secret,
                "qr_code": f"data:image/png;base64,{img_str}"
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/2fa/verify', methods=['POST'])
    def verify_2fa():
        """
        Verify the TOTP code and return tokens if valid.
        """
        try:
            data = request.json
            username = data.get("username")
            otp_code = data.get("otp_code")
            setup_mode = data.get("setup_mode", False)
            
            if username not in USERS:
                return jsonify({"msg": "User not found"}), 404
            
            secret = USERS[username].get("otp_secret")
            if not secret:
                return jsonify({"msg": "2FA not set up"}), 400
            
            totp = pyotp.TOTP(secret)
            if totp.verify(otp_code):
                if setup_mode:
                    USERS[username]["is_2fa_enabled"] = True
                
                # Create tokens
                access_token = create_access_token(identity=username, expires_delta=timedelta(hours=1))
                refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=30))
                
                return jsonify({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "username": username,
                        "email": USERS[username]["email"],
                        "first_name": USERS[username]["first_name"],
                        "last_name": USERS[username]["last_name"]
                    }
                }), 200
            else:
                return jsonify({"msg": "Invalid OTP code"}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/google-login', methods=['POST'])
    def google_login():
        """
        Mock Google Login endpoint. 
        In a real app, this would redirect to Google's OAuth consent screen.
        """
        try:
            # For demonstration, we'll just simulate a successful login as 'full_user'
            # In real implementation, this would use google-auth-oauthlib
            username = "full_user"
            
            # Create tokens
            access_token = create_access_token(identity=username, expires_delta=timedelta(hours=1))
            refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=30))
            
            return jsonify({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "username": username,
                    "email": USERS[username]["email"],
                    "first_name": USERS[username]["first_name"],
                    "last_name": USERS[username]["last_name"]
                }
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
