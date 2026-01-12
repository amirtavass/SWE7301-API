from flask import request, jsonify

# Mock Database for this module (In-memory)
items = {
    1: {"id": 1, "name": "Standard Laptop"}
}
current_id = 2

def register(app, session=None):
    """
    Registers the Bulk Operations endpoint.
    Fulfills Story: Support bulk operations for efficiency.
    """

    @app.route("/api/items/bulk", methods=["POST"])
    def bulk_items():
        global current_id
        data = request.get_json()

        # AC: Check if multiple records are submitted in a single request
        if not isinstance(data, list):
            return jsonify({
                "error": "Bad Request",
                "message": "Payload must be a JSON list of records."
            }), 400

        results = {
            "success_count": 0,
            "failure_count": 0,
            "details": []
        }

        for index, record in enumerate(data):
            try:
                # Validation: Ensure each record has a name
                if not record or 'name' not in record:
                    raise ValueError("Missing 'name' field")

                item_id = record.get("id")

                # DoD: Create or Update (Upsert) logic
                if item_id and item_id in items:
                    # Update existing record
                    items[item_id]["name"] = record["name"]
                    action = "updated"
                    final_id = item_id
                else:
                    # Create new record
                    final_id = item_id if item_id else current_id
                    items[final_id] = {"id": final_id, "name": record["name"]}
                    if not item_id:
                        current_id += 1
                    action = "created"

                results["details"].append({
                    "index": index,
                    "status": "success",
                    "action": action,
                    "id": final_id
                })
                results["success_count"] += 1

            except Exception as e:
                # Partial failure handling: Record the error and continue
                results["details"].append({
                    "index": index,
                    "status": "error",
                    "message": str(e)
                })
                results["failure_count"] += 1

        # Return 207 Multi-Status if there's a mix of success and failure
        status_code = 201 if results["failure_count"] == 0 else 207
        return jsonify(results), status_code