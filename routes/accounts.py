from flask import Blueprint, jsonify, request
from services.db_service import run_query

accounts_bp = Blueprint("accounts", __name__)

@accounts_bp.route("/accounts", methods=["GET"])
def get_accounts():
    """
    Obtiene todas las cuentas de Twitter autenticadas.
    """
    query = "SELECT twitter_id, username FROM users"
    accounts = run_query(query, fetchall=True)

    if not accounts:
        
        return jsonify({"message": "No hay cuentas registradas"}), 200

    accounts_list = [{"twitter_id": acc[0], "username": acc[1]} for acc in accounts]

    return jsonify(accounts_list), 200


@accounts_bp.route("/account/<string:twitter_id>", methods=["GET"])
def get_account_details(twitter_id):
    """
    Obtiene todos los datos relacionados con una cuenta de Twitter específica,
    incluyendo la información de la tabla users, monitored_users y keywords.
    :param twitter_id: ID de Twitter de la cuenta a consultar.
    :return: JSON con los datos de la cuenta o un mensaje de error.
    """
    # Consultar datos de la cuenta en la tabla users (incluyendo language y custom_style)
    user_query = f"""
    SELECT id, username, access_token, access_token_secret, language, custom_style
    FROM users
    WHERE twitter_id = '{twitter_id}'
    """
    user_data = run_query(user_query, fetchone=True)
    
    if not user_data:
        return jsonify({"error": "Cuenta no encontrada"}), 404

    id = user_data[0]
    
    # Construir datos del usuario
    user_info = {
        "id": user_data[0],
        "username": user_data[1],
        "access_token": user_data[2],
        "access_token_secret": user_data[3],
        "language": user_data[4],  # Idioma asignado al usuario
        "custom_style": user_data[5]  # Estilo personalizado del usuario
    }

    # Consultar cuentas monitoreadas en la tabla monitored_users
    monitored_users_query = f"""
    SELECT twitter_username
    FROM monitored_users
    WHERE user_id = '{id}'
    """
    monitored_users = run_query(monitored_users_query, fetchall=True)
    monitored_users_list = [
        {"twitter_username": mu[0]}
        for mu in monitored_users
    ]

    # Consultar keywords asociadas al usuario
    keywords_query = f"""
    SELECT keyword
    FROM user_keywords
    WHERE user_id = '{id}'
    """
    keywords = run_query(keywords_query, fetchall=True)
    keywords_list = [kw[0] for kw in keywords]

    # Construir respuesta final
    response = {
        "user": user_info,
        "monitored_users": monitored_users_list,
        "keywords": keywords_list
    }
    return jsonify(response), 200

@accounts_bp.route("/account/<string:twitter_id>", methods=["PUT"])
def update_account(twitter_id):
    """
    Actualiza los datos de una cuenta de Twitter, incluyendo idioma, custom_style,
    usuarios monitoreados y keywords.
    """
    data = request.json

    # Extraer datos
    language = data.get("language")
    custom_style = data.get("custom_style")
    monitored_users = data.get("monitored_users", [])
    keywords = data.get("keywords", [])

    # Verificar si la cuenta existe
    user_query = f"SELECT id FROM users WHERE twitter_id = '{twitter_id}'"
    user_data = run_query(user_query, fetchone=True)
    
    if not user_data:
        return jsonify({"error": "Cuenta no encontrada"}), 404

    user_id = user_data[0]

    # Actualizar idioma y custom_style
    update_user_query = f"""
    UPDATE users
    SET language = '{language}', custom_style = '{custom_style}'
    WHERE twitter_id = '{twitter_id}'
    """
    run_query(update_user_query)

    # Limpiar y actualizar usuarios monitoreados
    run_query(f"DELETE FROM monitored_users WHERE user_id = {user_id}")
    for username in monitored_users:
        run_query(f"INSERT INTO monitored_users (user_id, twitter_username) VALUES ({user_id}, '{username}')")

    # Limpiar y actualizar keywords
    run_query(f"DELETE FROM user_keywords WHERE user_id = {user_id}")
    for keyword in keywords:
        run_query(f"INSERT INTO user_keywords (user_id, keyword) VALUES ({user_id}, '{keyword}')")

    return jsonify({"message": "Cuenta actualizada correctamente"}), 200


@accounts_bp.route("/account/<string:twitter_id>", methods=["DELETE"])
def delete_account(twitter_id):
    """
    Elimina una cuenta de Twitter autenticada y sus datos relacionados.
    """
    # Verificar si la cuenta existe
    user_query = f"SELECT id FROM users WHERE twitter_id = '{twitter_id}'"
    user_data = run_query(user_query, fetchone=True)

    if not user_data:
        return jsonify({"error": "Cuenta no encontrada"}), 404

    user_id = user_data[0]

    # Eliminar datos relacionados en otras tablas
    run_query(f"DELETE FROM monitored_users WHERE user_id = {user_id}")
    run_query(f"DELETE FROM user_keywords WHERE user_id = {user_id}")
    run_query(f"DELETE FROM users WHERE id = {user_id}")

    return jsonify({"message": "Cuenta eliminada correctamente"}), 200
