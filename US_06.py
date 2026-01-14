"""
US-06: API Status and Swagger Integration
"""
from flask import jsonify

def register(app, session):
    """
    Registers the status routes for US-06.
    """
    
    @app.route('/', endpoint='us06_index')
    def index():
        return "API is running on swagger"

    @app.route('/status')
    def status():
        return jsonify({"message": "System is online"})
    
    @app.route('/health')
    def health():
        return jsonify({"status": "ok"})