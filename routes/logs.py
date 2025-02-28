from flask import Blueprint, jsonify, request
from services.db_service import run_query
import logging

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/logs", methods=["GET"])
def get_logs():
    logs_query = "SELECT * FROM logs ORDER BY timestamp DESC"
    logs = run_query(logs_query, fetchall=True)

    print(logs)

    log_list = [
        {
            "id": log[0],
            "user_id": log[1],
            "event_type": log[2],
            "event_description": log[3],
            "timestamp": log[4]
        }
        for log in logs
    ]

    return jsonify(log_list)


@logs_bp.route("/update_rate_limit", methods=["POST"])
def update_rate_limit():
    data = request.json
    new_rate_limit = data.get("rate_limit")

    if not isinstance(new_rate_limit, int) or new_rate_limit <= 0:
        return jsonify({"error": "rate_limit must be an INT."}), 400

    try:
        query = f"UPDATE configuration SET rate_limit = {new_rate_limit} WHERE id = 1"
        run_query(query)
        return jsonify({"message": f"Rate limit updated to {new_rate_limit}"}), 200
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": "Error"}), 500
    
    
@logs_bp.route("/get_rate_limit", methods=["GET"])
def get_rate_limit():

    try:
        query = "SELECT rate_limit FROM configuration WHERE id = 1"
        result = run_query(query, fetchone=True)
        rate_limit = result[0]
        
        return jsonify({"rate_limit": rate_limit}), 200
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": "Error"}), 500