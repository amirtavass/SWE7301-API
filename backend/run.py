from flask import Flask
from flask_jwt_extended import JWTManager
from app.db import engine, SessionLocal, Base

def get_app():
    app = Flask(__name__)

    # JWT Config
    app.config["JWT_SECRET_KEY"] = "super-secret-key-change-me"
    JWTManager(app)

    # Initialize DB
    Base.metadata.create_all(bind=engine)

    # Import and register routes
    import app.routes.observation as observation
    import app.routes.filtering as filtering
    import app.routes.healthApi as healthApi
    import app.models.jwtAuth as jwtAuth

    session = SessionLocal()
    observation.register(app, session)
    filtering.register(app, session)
    healthApi.register(app, session)
    jwtAuth.register(app, session)

    return app


if __name__ == "__main__":
    app = get_app()
    print("Server running on http://127.0.0.1:5000")
    app.run(debug=True)
