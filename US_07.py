from flask import request, jsonify

# In-memory data store for this module
items = {
    1: {"id": 1, "name": "Initial Item"}
}
current_id = 2

def register(app, session=None):
    """
    Registers the full RESTful suite for integration.
    Fulfills Story: Support GET, POST, PUT, PATCH, and DELETE.
    """

    # --- GET: Read All (Fulfills GET) ---
    @app.route("/api/items", methods=["GET"])
    def get_items():
        return jsonify({"items": list(items.values())}), 200

    # --- GET: Read Single (Fulfills GET) ---
    @app.route("/api/items/<int:item_id>", methods=["GET"])
    def get_item(item_id):
        item = items.get(item_id)
        if not item:
            return jsonify({"error": "Resource not found"}), 404
        return jsonify(item), 200

    # --- POST: Create (Fulfills POST) ---
    @app.route("/api/items", methods=["POST"])
    def create_item():
        global current_id
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Bad Request: 'name' is required"}), 400
        
        new_item = {"id": current_id, "name": data["name"]}
        items[current_id] = new_item
        current_id += 1
        return jsonify(new_item), 201

    # --- PUT: Full Update (Fulfills PUT) ---
    @app.route("/api/items/<int:item_id>", methods=["PUT"])
    def update_item(item_id):
        if item_id not in items:
            return jsonify({"error": "Resource not found"}), 404
        
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Bad Request: 'name' is required"}), 400
            
        items[item_id]["name"] = data["name"]
        return jsonify(items[item_id]), 200

    # --- PATCH: Partial Update (Fulfills PATCH) ---
    @app.route("/api/items/<int:item_id>", methods=["PATCH"])
    def patch_item(item_id):
        if item_id not in items:
            return jsonify({"error": "Resource not found"}), 404
        
        data = request.get_json()
        if "name" in data:
            items[item_id]["name"] = data["name"]
        return jsonify(items[item_id]), 200

    # --- DELETE: Remove (Fulfills DELETE) ---
    @app.route("/api/items/<int:item_id>", methods=["DELETE"])
    def delete_item(item_id):
        if item_id not in items:
            return jsonify({"error": "Resource not found"}), 404
        
        del items[item_id]
        return "", 204