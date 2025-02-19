from flask import Blueprint, jsonify, request
from services.db_service import run_query
from services.post_tweets import post_tweet  # Importamos la función para publicar tweets
import logging

# Configurar logging para registrar eventos
logging.basicConfig(level=logging.INFO)

tweets_bp = Blueprint("tweets", __name__)

@tweets_bp.route("/tweets", methods=["GET"])
def get_collected_tweets():
    """
    Obtiene los tweets recolectados de la base de datos.
    """
    query = "SELECT source_username, tweet_id, tweet_text, created_at FROM collected_tweets ORDER BY created_at DESC LIMIT 50"
    tweets = run_query(query, fetchall=True)
    if not tweets:
        return jsonify({"message": "No hay tweets recolectados"}), 404
    return jsonify([{"source_username": t[0], "tweet_id": t[1], "tweet_text": t[2], "created_at": t[3]} for t in tweets]), 200


@tweets_bp.route("/post_tweet", methods=["POST"])
def post_tweet_route():
    """
    Publica un tweet en la cuenta de Twitter asociada al usuario.
    """
    data = request.json
    user_id = data.get("user_id")
    tweet_text = data.get("tweet_text")

    # Validar que se proporcionen todos los parámetros necesarios
    if not user_id or not tweet_text:
        return jsonify({"error": "Faltan parámetros (user_id o tweet_text)"}), 400

    # Validar la longitud del tweet
    if len(tweet_text) > 280:
        return jsonify({"error": "El texto del tweet excede el límite de 280 caracteres"}), 400

    # Llamar a la función para publicar el tweet
    response, status_code = post_tweet(user_id, tweet_text)

    # Retornar la respuesta al cliente
    return jsonify(response), status_code