import asyncio
import aiohttp
from services.db_service import run_query, save_collected_tweet, log_event
from config import Config
from datetime import datetime, timezone
from services.post_tweets import post_tweet

SOCIALDATA_API_URL = "https://api.socialdata.tools/twitter/search"
TWEET_LIMIT_PER_DAY = Config.TWEET_LIMIT_PER_DAY

async def count_tweets_for_user(user_id):
    """
    Cuenta la cantidad de tweets recolectados hoy para un usuario específico.
    """
    query = f"""
    SELECT COUNT(*) FROM collected_tweets 
    WHERE user_id = {user_id}
    AND created_at >= CURRENT_DATE - INTERVAL '1 day'
    """
    result = run_query(query, fetchone=True)
    return result[0] if result else 0

async def fetch_tweets_for_user(session, user_id, username, limit, fetching_event):
    """
    Función asíncrona para buscar tweets de un usuario monitoreado.
    Se detiene si el evento fetching_event está activado.
    """
    # Verificar si el proceso debe detenerse
    if fetching_event.is_set():
        print(f"⏹️ Proceso detenido para usuario monitoreado: {username}.")
        return

    # Contar tweets recolectados hoy
    tweets_collected_today = await count_tweets_for_user(user_id)
    if tweets_collected_today >= TWEET_LIMIT_PER_DAY:
        print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_DAY} tweets hoy. Saltando usuario {username}.")
        return

    print(f"📡 Buscando tweets de usuario monitoreado: {username}")
    headers = {"Authorization": f"Bearer {Config.SOCIALDATA_API_KEY}"}
    params = {"query": f"from:{username}", "type": "Latest"}

    try:
        async with session.get(SOCIALDATA_API_URL, headers=headers, params=params) as response:
            data = await response.json()
            tweets = data.get("tweets", [])[:limit]

            for tweet in tweets:
                # Verificar nuevamente si el proceso debe detenerse
                if fetching_event.is_set():
                    print(f"⏹️ Proceso detenido mientras se procesaban tweets de {username}.")
                    break

                # Contar tweets recolectados hoy
                tweets_collected_today = await count_tweets_for_user(user_id)
                if tweets_collected_today >= TWEET_LIMIT_PER_DAY:
                    print(f"⛔ Usuario {user_id} alcanzó el límite mientras recolectaba. Deteniendo usuario {username}.")
                    break

                # Extraer datos del tweet
                tweet_id = tweet["id_str"]
                tweet_text = tweet["full_text"]
                created_at = tweet["tweet_created_at"]

                print(f"✅ Nuevo tweet de {username}: {tweet_text[:50]}...")
                save_collected_tweet(user_id, "username", username, tweet_id, tweet_text, created_at)
                print(f"💾 Tweet guardado en la base de datos: {tweet_id}")

                # Publicar el tweet
                response, status_code = post_tweet(user_id, tweet_text)
                if status_code == 201:
                    # Si el tweet fue publicado exitosamente, eliminarlo de collected_tweets
                    delete_query = f"DELETE FROM collected_tweets WHERE tweet_id = '{tweet_id}' AND user_id = '{user_id}'"
                    run_query(delete_query)
                    print(f"🗑️ Tweet {tweet_id} eliminado de la base de datos después de ser publicado.")
                else:
                    print(f"❌ No se pudo publicar el tweet de {username}: {response.get('error')}")

                # Pequeña pausa para evitar sobrecargar el sistema (opcional)
                await asyncio.sleep(0.1)

    except Exception as e:
        log_event(user_id, "ERROR", f"Error obteniendo tweets de {username}: {str(e)}")
        print(f"❌ Error con {username}: {e}")
        
async def fetch_tweets_for_keyword(session, user_id, keyword, limit, fetching_event):
    """
    Función asíncrona para buscar tweets con una palabra clave monitoreada.
    Se detiene si el evento fetching_event está activado.
    """
    # Verificar si el proceso debe detenerse
    if fetching_event.is_set():
        print(f"⏹️ Proceso detenido para keyword: {keyword}.")
        return

    # Contar tweets recolectados hoy
    tweets_collected_today = await count_tweets_for_user(user_id)
    if tweets_collected_today >= TWEET_LIMIT_PER_DAY:
        print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_DAY} tweets hoy. Saltando keyword {keyword}.")
        return

    print(f"🔍 Buscando tweets con keyword: {keyword}")
    headers = {"Authorization": f"Bearer {Config.SOCIALDATA_API_KEY}"}
    params = {"query": keyword, "type": "Latest"}

    try:
        async with session.get(SOCIALDATA_API_URL, headers=headers, params=params) as response:
            data = await response.json()
            tweets = data.get("tweets", [])[:limit]

            for tweet in tweets:
                # Verificar nuevamente si el proceso debe detenerse
                if fetching_event.is_set():
                    print(f"⏹️ Proceso detenido mientras se procesaban tweets con keyword: {keyword}.")
                    break

                # Contar tweets recolectados hoy
                tweets_collected_today = await count_tweets_for_user(user_id)
                if tweets_collected_today >= TWEET_LIMIT_PER_DAY:
                    print(f"⛔ Usuario {user_id} alcanzó el límite mientras recolectaba. Deteniendo keyword {keyword}.")
                    break

                # Extraer datos del tweet
                tweet_id = tweet["id_str"]
                tweet_text = tweet["full_text"]
                created_at = tweet["tweet_created_at"]

                print(f"✅ Nuevo tweet con keyword '{keyword}': {tweet_text[:50]}...")
                save_collected_tweet(user_id, "keyword", keyword, tweet_id, tweet_text, created_at)
                print(f"💾 Tweet guardado en la base de datos: {tweet_id}")

                # Publicar el tweet
                response, status_code = post_tweet(user_id, tweet_text)
                if status_code == 201:
                    # Si el tweet fue publicado exitosamente, eliminarlo de collected_tweets
                    delete_query = f"DELETE FROM collected_tweets WHERE tweet_id = '{tweet_id}' AND user_id = '{user_id}'"
                    run_query(delete_query)
                    print(f"🗑️ Tweet {tweet_id} eliminado de la base de datos después de ser publicado.")
                else:
                    print(f"❌ No se pudo publicar el tweet con keyword '{keyword}': {response.get('error')}")

                # Pequeña pausa para evitar sobrecargar el sistema (opcional)
                await asyncio.sleep(0.1)

    except Exception as e:
        log_event(user_id, "ERROR", f"Error obteniendo tweets con la keyword '{keyword}': {str(e)}")
        print(f"❌ Error con la keyword '{keyword}': {e}")

async def fetch_tweets_for_single_user(user_id, fetching_event):
    """
    Función asíncrona para buscar tweets para un solo usuario.
    Se detiene si el evento fetching_event está activado.
    """
    print(f"🔍 Iniciando búsqueda de tweets para usuario ID: {user_id}...")

    # Verificar si el proceso debe detenerse
    if fetching_event.is_set():
        print(f"⏹️ Proceso detenido para usuario ID: {user_id}.")
        return

    # Contar tweets recolectados hoy
    tweets_collected_today = await count_tweets_for_user(user_id)
    print(tweets_collected_today)

    if tweets_collected_today >= TWEET_LIMIT_PER_DAY:
        print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_DAY} tweets hoy. Saltando completamente la búsqueda.")
        return

    # Crear una sesión HTTP
    async with aiohttp.ClientSession() as session:
        # Consultar usuarios monitoreados
        query_users = f"SELECT DISTINCT twitter_username FROM monitored_users WHERE user_id = '{user_id}'"
        monitored_users = run_query(query_users, fetchall=True) or []
        print(monitored_users)

        # Consultar keywords monitoreadas
        query_keywords = f"SELECT DISTINCT keyword FROM user_keywords WHERE user_id = '{user_id}'"
        monitored_keywords = run_query(query_keywords, fetchall=True) or []
        print(monitored_keywords)

        # Si no hay usuarios ni keywords monitoreadas, salir
        if not monitored_users and not monitored_keywords:
            print(f"⚠ Usuario {user_id} no tiene usuarios o keywords monitoreadas.")
            return

        # Calcular límites
        user_limit = 11 if len(monitored_users) > 3 else TWEET_LIMIT_PER_DAY
        keyword_limit = 11 if len(monitored_keywords) > 3 else TWEET_LIMIT_PER_DAY

        # Crear tareas para buscar tweets
        user_tasks = [
            fetch_tweets_for_user(session, user_id, username[0], user_limit, fetching_event)
            for username in monitored_users
        ]
        keyword_tasks = [
            fetch_tweets_for_keyword(session, user_id, keyword[0], keyword_limit, fetching_event)
            for keyword in monitored_keywords
        ]

        # Ejecutar todas las tareas
        try:
            await asyncio.gather(*user_tasks, *keyword_tasks)
        except asyncio.CancelledError:
            print(f"⏹️ Tareas canceladas para usuario ID: {user_id}.")

    print(f"✅ Búsqueda de tweets completada para usuario ID: {user_id}.")
    
async def fetch_tweets_for_all_users(fetching_event):
    """
    Función asíncrona para buscar tweets para todos los usuarios registrados.
    Se detiene si el evento fetching_event está activado.
    """
    print("🔍 Buscando tweets para cada usuario registrado (etapa 1)...")

    # Consultar usuarios registrados en la base de datos
    query = "SELECT DISTINCT id FROM users"
    users = run_query(query, fetchall=True)
    print(users)

    if not users:
        print("⚠ No hay usuarios registrados en la base de datos.")
        return

    # Crear tareas para buscar tweets para cada usuario
    tasks = []
    for user_id in users:
        if fetching_event.is_set():
            print("⏹️ Proceso detenido por solicitud de usuario.")
            return

        print(f"👤 Iniciando búsqueda de tweets para usuario ID: {user_id[0]}")
        task = asyncio.create_task(fetch_tweets_for_single_user(user_id[0], fetching_event))
        tasks.append(task)

        # Pequeña pausa para evitar sobrecargar el sistema (opcional)
        await asyncio.sleep(0.1)

    # Esperar a que todas las tareas terminen o se cancelen
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("⏹️ Tareas canceladas por solicitud de detención.")

    print("✅ Búsqueda de tweets completada.")

def auto_post_tweet():
    """
    Publica un tweet automáticamente para un usuario específico.
    """
    user_id = 1 
    tweet_text = "¡Este es un tweet de prueba!"

    # Llamar a la función post_tweet
    response, status_code = post_tweet(user_id, tweet_text)

    if status_code == 200:
        print("✅ Tweet automático publicado exitosamente.")
    else:
        print(f"❌ Error al publicar el tweet automático: {response.get('error')}")


async def start_tweet_fetcher():
    print('🚀 Iniciando el servicio de recolección de tweets...')
    # while True:
    #     await fetch_tweets_for_all_users()
    
    #     print("⏳ Esperando 5 minutos antes de la próxima búsqueda...")
    #     await asyncio.sleep(300)  


