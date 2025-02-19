from flask import Blueprint, jsonify, request
from services.db_service import run_query

logs_bp = Blueprint("logs", __name__)

@logs_bp.route("/logs", methods=["GET"])
def get_logs():
    logs_query = "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50"
    logs = run_query(logs_query, fetchall=True)

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
