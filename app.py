from flask import Flask, jsonify
from flask_cors import CORS
from routes.auth import auth_bp
from routes.logs import logs_bp
from routes.accounts import accounts_bp
from routes.monitored_users import monitored_bp
from config import Config
import threading
import asyncio
from services.fetch_tweets import fetch_tweets_for_all_users

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["http://localhost:3000"])

# Variables globales para el hilo y el evento
fetcher_thread = None
fetching_event = threading.Event()

# Registrar blueprints
app.register_blueprint(accounts_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(logs_bp, url_prefix="/logs")
app.register_blueprint(monitored_bp, url_prefix="/api")

@app.route("/")
def home():
    return {"message": "Bienvenido a la API de Twitter Bot"}

def start_tweet_fetcher():
    """
    Función que inicia el servicio de recolección de tweets.
    Esta función ahora usa un contexto de aplicación Flask para evitar errores.
    """
    print('🚀 Iniciando el servicio de recolección de tweets...')

    async def fetch_loop():
        # Crear un contexto de aplicación Flask
        with app.app_context():
            while not fetching_event.is_set():
                try:
                    # Ejecutar fetch_tweets_for_all_users como una tarea cancelable
                    task = asyncio.create_task(fetch_tweets_for_all_users(fetching_event))
                    await task  # Esperar a que la tarea termine
                    if fetching_event.is_set():
                        break  # Salir si el evento está activado
                    print("⏳ Esperando 10 minutos antes de la próxima búsqueda...")
                    await asyncio.sleep(600)  # Esperar 10 minutos sin bloquear el hilo
                except asyncio.CancelledError:
                    print("⏹️ Tarea cancelada por solicitud de detención.")
                    break
                except Exception as e:
                    print(f"❌ Error en fetch_loop: {e}")
                    break

        print("⏹️ Servicio de recolección detenido.")

    # Ejecutar el bucle asíncrono
    asyncio.run(fetch_loop())
    
@app.route("/start-fetch", methods=["POST"])
def start_fetch():
    """
    Endpoint para iniciar el proceso de recolección de tweets.
    """
    global fetcher_thread

    if fetcher_thread is None or not fetcher_thread.is_alive():
        fetching_event.clear()  # Aseguramos que el evento está limpio
        fetcher_thread = threading.Thread(target=start_tweet_fetcher, daemon=True)
        fetcher_thread.start()  # Inicia el hilo
        return jsonify({"status": "started"}), 200
    else:
        return jsonify({"status": "already running"}), 400

@app.route("/stop-fetch", methods=["POST"])
def stop_fetch():
    """
    Endpoint para detener el proceso de recolección de tweets.
    """
    global fetcher_thread

    if fetcher_thread is not None and fetcher_thread.is_alive():
        fetching_event.set()  # Detener el evento
        fetcher_thread.join(timeout=5)  # Esperar a que el hilo termine
        return jsonify({"status": "stopped"}), 200
    else:
        return jsonify({"status": "not running", "message": "El proceso de recolección no está en ejecución."}), 400

@app.route("/status-fetch", methods=["GET"])
def status_fetch():
    """
    Endpoint para verificar el estado del proceso de recolección.
    """
    global fetcher_thread

    if fetcher_thread is not None and fetcher_thread.is_alive():
        return jsonify({"status": "running"}), 200
    else:
        return jsonify({"status": "stopped"}), 200

if __name__ == "__main__":
    # Usamos `app.run()` con threaded=True para manejar múltiples solicitudes
    app.run(debug=True, threaded=True)