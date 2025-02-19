from flask import Blueprint, redirect, request, session, url_for
from requests_oauthlib import OAuth1Session
from services.db_service import run_query
from config import Config

auth_bp = Blueprint("auth", __name__)

REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZATION_URL = "https://api.twitter.com/oauth/authenticate"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
CALLBACK_URL = "http://localhost:5000/auth/callback"  # 🔹 Asegúrate de que coincida con la de Twitter

@auth_bp.route("/login")
def login():
    """
    Redirige al usuario a Twitter/X para autenticación OAuth 1.0a.
    """
    session.clear()  # 🔹 Limpiar sesión anterior para evitar tokens inválidos

    twitter = OAuth1Session(
        Config.TWITTER_CLIENT_ID,
        Config.TWITTER_CLIENT_SECRET,
        callback_uri=CALLBACK_URL
    )

    try:
        response = twitter.fetch_request_token(REQUEST_TOKEN_URL)

        if "oauth_token" not in response:
            print(f"❌ Error: No se recibió un oauth_token válido. Respuesta: {response}")
            return "Error al obtener request token", 500

        session["request_token"] = response["oauth_token"]
        session["request_token_secret"] = response["oauth_token_secret"]

        print(f"✅ Nuevo Request token obtenido: {response['oauth_token']}")

        auth_url = f"{AUTHORIZATION_URL}?oauth_token={response['oauth_token']}"
        print(f"🌐 Redirigiendo a la URL de autorización: {auth_url}")
        return redirect(auth_url)

    except Exception as e:
        print(f"❌ Error en OAuth: {e}")
        return "Error en autenticación con Twitter", 500

@auth_bp.route("/callback")
def callback():
    """
    Procesa la respuesta de Twitter y guarda el usuario en la base de datos.
    """
    print(f"🔹 Parámetros recibidos en /callbacak: {request.args}")

    oauth_token = request.args.get("oauth_token")
    oauth_verifier = request.args.get("oauth_verifier")

    if not oauth_token or not oauth_verifier:
        print("❌ Error: No se recibió oauth_token o oauth_verifier")
        return "Error en autenticación.", 400

    if "request_token" not in session or "request_token_secret" not in session:
        print(f"❌ Error: No se encontró request_token en la sesión. request_token recibido: {oauth_token}")
        return "Error de sesión.", 400

    print(f"✅ Request token esperado en sesión: {session['request_token']}, recibido: {oauth_token}")

    if session["request_token"] != oauth_token:
        print("❌ Error: El oauth_token recibido no coincide con el que se almacenó en sesión.")
        return "Error en autenticación.", 400

    twitter = OAuth1Session(
        Config.TWITTER_CLIENT_ID,
        Config.TWITTER_CLIENT_SECRET,
        session.pop("request_token"),
        session.pop("request_token_secret")
    )

    try:
        # Aquí se pasa el `oauth_verifier` que Twitter X nos dio
        tokens = twitter.fetch_access_token(ACCESS_TOKEN_URL, verifier=oauth_verifier)

        twitter_id = tokens["user_id"]
        username = tokens["screen_name"]
        access_token = tokens["oauth_token"]
        access_token_secret = tokens["oauth_token_secret"]

        print(f"✅ Usuario autenticado: {username} ({twitter_id})")

        # Guardar usuario en la base de datos
        query = f"""
        INSERT INTO users (twitter_id, username, access_token, access_token_secret)
        VALUES ('{twitter_id}', '{username}', '{access_token}', '{access_token_secret}')
        ON CONFLICT (twitter_id) DO UPDATE
        SET access_token = '{access_token}', access_token_secret = '{access_token_secret}'
        RETURNING id;
        """

        user_id = run_query(query, fetchone=True)

        if user_id:
            session["user_id"] = user_id[0]
            print(f"✅ Usuario guardado en DB con ID {session['user_id']}")
        else:
            print("❌ Error al guardar el usuario en la base de datos")
            return "Error al guardar el usuario en la base de datos", 500

        return redirect("http://localhost:3000")

    except Exception as e:
        print(f"❌ Error en callback: {e}")
        return "Error en autenticación con Twitter", 500

@auth_bp.route("/logout")
def logout():
    """
    Cierra la sesión del usuario.
    """
    session.clear()
    return redirect("http://localhost:3000"), 200
