import requests
from requests_oauthlib import OAuth1Session
from services.db_service import run_query, log_event
from config import Config
import logging

# Configurar logging para registrar eventos
logging.basicConfig(level=logging.INFO)

def post_tweet(user_id, tweet_text):
    """
    Publica un tweet en la cuenta de Twitter asociada al usuario usando la API v2.
    
    :param user_id: ID del usuario en la base de datos.
    :param tweet_text: Texto del tweet a publicar.
    :return: Tupla (respuesta, código de estado HTTP).
    """
    # Obtener las credenciales OAuth del usuario desde la base de datos
    query = f"SELECT access_token, access_token_secret FROM users WHERE id = {user_id}"
    result = run_query(query, fetchone=True)

    if not result:
        error_message = f"❌ Usuario {user_id} no encontrado en la base de datos."
        logging.error(error_message)
        log_event(user_id, "ERROR", error_message)
        return {"error": "Usuario no encontrado"}, 404
    
    access_token, access_token_secret = result

    # Crear una sesión OAuth1
    oauth = OAuth1Session(
        Config.TWITTER_CLIENT_ID,
        client_secret=Config.TWITTER_CLIENT_SECRET,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret
    )

    # Endpoint para publicar tweets en la API v2
    url = "https://api.twitter.com/2/tweets"

    # Parámetros del tweet (JSON en lugar de form-data)
    payload = {"text": tweet_text}

    try:
        # Enviar la solicitud POST con el cuerpo JSON
        response = oauth.post(url, json=payload)

        # Verificar la respuesta
        if response.status_code == 201:  # Código 201 significa éxito en la creación del tweet
            success_message = f"✅ Tweet publicado exitosamente: {tweet_text[:50]}..."
            logging.info(success_message)
            log_event(user_id, "INFO", success_message)
            return {"message": "Tweet publicado exitosamente"}, 201
        else:
            # Extraer mensaje de error de la respuesta JSON
            error_data = response.json()
            error_message = error_data.get("detail", "Error desconocido")
            full_error_message = f"❌ Error al publicar el tweet: {error_message}"
            logging.error(full_error_message)
            log_event(user_id, "ERROR", full_error_message)
            return {"error": error_message}, response.status_code

    except Exception as e:
        error_message = f"❌ Error inesperado al publicar el tweet: {str(e)}"
        logging.error(error_message)
        log_event(user_id, "ERROR", error_message)
        return {"error": str(e)}, 500