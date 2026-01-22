"""
US-13: Authentication and Protected Routes
US-16: JWT Token Management via Website
"""
from flask import request, jsonify, g
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
from app.routes.observation import User, get_db

def register(app):
    """
    Registers authentication routes with JWT token management.
    Includes login, signup, token refresh, and token validation endpoints.
    """

    @app.route('/signup', methods=['POST'])
    def signup():
        """
        US-16: User registration endpoint
        Creates new user account and stores in database
        """
        try:
            db = get_db()
            data = request.json
            password = data.get("password")
            email = data.get("email")
            first_name = data.get("first_name")
            last_name = data.get("last_name")

            # Validate required fields
            if not all([password, email, first_name, last_name]):
                return jsonify({"msg": "All fields are required"}), 400

            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return jsonify({"msg": "User with this email already exists"}), 409

            # Store new user
            new_user = User(
                email=email,
                password=password, # In prod, hash this!
                first_name=first_name,
                last_name=last_name,
                is_2fa_enabled=0
            )
            db.add(new_user)
            db.commit()

            return jsonify({
                "msg": "User created successfully",
                "email": email
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
            db = get_db()
            # Changed from username to email
            email = request.json.get("email") or request.json.get("username") 
            password = request.json.get("password")
            
            # Validate credentials
            user = db.query(User).filter(User.email == email).first()
            
            if not user or user.password != password:
                return jsonify({"msg": "Bad email or password"}), 401

            # Check if 2FA is required
            if user.is_2fa_enabled:
                return jsonify({
                    "msg": "2FA required",
                    "two_step_required": True,
                    "email": email
                }), 200

            # Create tokens with custom expiration
            access_token = create_access_token(
                identity=email,
                expires_delta=timedelta(hours=1)  # 1 hour expiry
            )
            refresh_token = create_refresh_token(
                identity=email,
                expires_delta=timedelta(days=30)  # 30 day expiry
            )

            # Return user info along with tokens
            user_info = user.to_dict()

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
            current_user_email = get_jwt_identity()
            new_access_token = create_access_token(
                identity=current_user_email,
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
        """
        try:
            current_user_email = get_jwt_identity()
            jwt_data = get_jwt()
            
            return jsonify({
                "valid": True,
                "user": current_user_email,
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
            current_user_email = get_jwt_identity()
            return jsonify({
                "msg": "Given valid token, when used, then data returned.",
                "user": current_user_email,
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
            db = get_db()
            email = get_jwt_identity()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return jsonify({"msg": "User not found"}), 404
            
            secret = pyotp.random_base32()
            user.otp_secret = secret
            db.commit()
            
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(name=email, issuer_name="GeoScope")
            
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
            db = get_db()
            data = request.json
            email = data.get("email") or data.get("username")
            otp_code = data.get("otp_code")
            setup_mode = data.get("setup_mode", False)
            
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return jsonify({"msg": "User not found"}), 404
            
            secret = user.otp_secret
            if not secret:
                return jsonify({"msg": "2FA not set up"}), 400
            
            totp = pyotp.TOTP(secret)
            if totp.verify(otp_code):
                if setup_mode:
                    user.is_2fa_enabled = 1
                    db.commit()
                
                # Create tokens
                access_token = create_access_token(identity=email, expires_delta=timedelta(hours=1))
                refresh_token = create_refresh_token(identity=email, expires_delta=timedelta(days=30))
                
                return jsonify({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": user.to_dict()
                }), 200
            else:
                return jsonify({"msg": "Invalid OTP code"}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # OAuth Setup
    from authlib.integrations.flask_client import OAuth
    import os

    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'openid email profile'},
    )

    @app.route('/google-login', methods=['GET', 'POST'])
    def google_login():
        """
        Initiates Google OAuth flow.
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return jsonify({"msg": "Google Client ID or Secret is not configured."}), 500
            
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/google-callback")
        return google.authorize_redirect(redirect_uri)

    @app.route('/google-callback', methods=['GET'])
    def google_callback():
        """
        Handles Google OAuth callback.
        """
        try:
            db = get_db()
            token = google.authorize_access_token()
            user_info = google.userinfo()
            
            email = user_info.get('email')
            name = user_info.get('name', 'Google User')
            
            # Find or create user
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                # Create a new user from Google info
                parts = name.split(' ')
                first_name = parts[0]
                last_name = parts[-1] if len(parts) > 1 else ''
                
                user = User(
                    email=email,
                    password="", # No password for OAuth users
                    first_name=first_name,
                    last_name=last_name,
                    is_2fa_enabled=0
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # Generate JWTs
            access_token = create_access_token(identity=user.email, expires_delta=timedelta(hours=1))
            refresh_token = create_refresh_token(identity=user.email, expires_delta=timedelta(days=30))

            # Redirect to Frontend
            frontend_callback = os.getenv("FRONTEND_CALLBACK_URL", "http://127.0.0.1:8001/auth/google/callback")
            
            from flask import redirect
            return redirect(f"{frontend_callback}?access_token={access_token}&refresh_token={refresh_token}&email={user.email}&is_2fa_enabled={user.is_2fa_enabled}&first_name={user.first_name}")
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
