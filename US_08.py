from flask import request, jsonify

def register(app, session=None):
    """
    Registers standard JSON response patterns.
    Fulfills Story: All API responses in JSON.
    """

    # --- 1. Successful JSON Response Example ---
    @app.route("/api/status", methods=["GET"])
    def get_status():
        return jsonify({
            "status": "online",
            "format": "JSON",
            "message": "System is conforming to standards"
        }), 200

    # --- 2. Custom Error Handlers (DoD: Errors are valid JSON) ---
    
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "error": "Bad Request",
            "message": "The browser (or proxy) sent a request that this server could not understand.",
            "code": 400
        }), 400

    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({
            "error": "Not Found",
            "message": "The requested URL was not found on the server.",
            "code": 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "error": "Method Not Allowed",
            "message": "The method is not allowed for the requested URL.",
            "code": 405
        }), 405

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server.",
            "code": 500
        }), 500