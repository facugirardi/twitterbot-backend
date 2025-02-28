import asyncio
import aiohttp
from services.db_service import run_query, save_collected_tweet, log_event
from config import Config
from datetime import datetime, timezone
from services.post_tweets import post_tweet

SOCIALDATA_API_URL = "https://api.socialdata.tools/twitter/search"
TWEET_LIMIT_PER_HOUR = 10

async def get_tweet_limit_per_hour():
    """
    Obtiene el límite de tweets por hora desde la base de datos.
    """
    query = "SELECT rate_limit FROM configuration WHERE id = 1"
    result = run_query(query, fetchone=True)
    return result[0] if result else 10  # Valor por defecto en caso de error

async def count_tweets_for_user(user_id):
    query = f"""
    SELECT COUNT(*) FROM collected_tweets 
    WHERE user_id = {user_id}
    AND created_at >= NOW() - INTERVAL '1 hour'
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
    if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
        print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_HOUR} tweets hoy. Saltando usuario {username}.")
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
                if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
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
                if status_code == 200:
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
    if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
        print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_HOUR} tweets hoy. Saltando keyword {keyword}.")
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
                if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
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


async def fetch_tweets_for_monitored_users_with_keywords(session, user_id, monitored_users, keywords, limit, fetching_event):
    """
    Función asíncrona para buscar tweets de usuarios monitoreados que contengan palabras clave específicas.
    Se detiene si el evento fetching_event está activado.
    """
    try:
        # Verificar si el proceso debe detenerse
        if fetching_event.is_set():
            print(f"⏹️ Proceso detenido para usuario ID: {user_id}.")
            return
        
        TWEET_LIMIT_PER_HOUR = await get_tweet_limit_per_hour()

        # Contar tweets recolectados hoy
        tweets_collected_today = await count_tweets_for_user(user_id)
        if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
            print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_HOUR} tweets. Saltando completamente la búsqueda.")
            return

        print(f"🔍 Buscando tweets para usuario ID: {user_id} con palabras clave específicas...")

        # Construir la consulta combinada
        query_parts = []
        for username in monitored_users:
            keyword_query = " OR ".join(keywords)  # Combinar palabras clave con OR
            query_parts.append(f"(from:{username} ({keyword_query}))")
        full_query = " OR ".join(query_parts)  # Combinar todas las consultas con OR

        headers = {"Authorization": f"Bearer {Config.SOCIALDATA_API_KEY}"}
        params = {"query": full_query, "type": "Latest"}

        async with session.get(SOCIALDATA_API_URL, headers=headers, params=params) as response:
            data = await response.json()
            tweets = data.get("tweets", [])[:limit]

            for tweet in tweets:
                # Verificar nuevamente si el proceso debe detenerse
                if fetching_event.is_set():
                    print(f"⏹️ Proceso detenido mientras se procesaban tweets.")
                    break

                # Contar tweets recolectados hoy
                tweets_collected_today = await count_tweets_for_user(user_id)
                if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
                    print(f"⛔ Usuario {user_id} alcanzó el límite mientras recolectaba. Deteniendo la búsqueda.")
                    break

                # Extraer datos del tweet
                tweet_id = tweet["id_str"]
                tweet_text = tweet["full_text"]
                created_at = tweet["tweet_created_at"]

                print(f"✅ Nuevo tweet encontrado: {tweet_text[:50]}...")
                save_collected_tweet(user_id, "combined", None, tweet_id, tweet_text, created_at)
                print(f"💾 Tweet guardado en la base de datos: {tweet_id}")

                query = f"""
                SELECT tweet_text FROM collected_tweets WHERE tweet_id = '{tweet_id}' AND user_id = '{user_id}'                
                """
                result = run_query(query, fetchone=True)

                if result != 'None':
                    response, status_code = post_tweet(user_id, result)
                
                if status_code == 200:
                    delete_query = f"DELETE FROM collected_tweets WHERE tweet_id = '{tweet_id}' AND user_id = '{user_id}'"
                    run_query(delete_query)
                    print(f"🗑️ Tweet {tweet_id} eliminado de la base de datos después de ser publicado.")
                else:
                    print(f"❌ No se pudo publicar el tweet {result}: {response.get('error')}")

                await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        print(f"⏹️ Tarea cancelada para usuario ID: {user_id}.")
        raise 
    except Exception as e:
        log_event(user_id, "ERROR", f"Error obteniendo tweets: {str(e)}")
        print(f"❌ Error al buscar tweets: {e}")
        
# async def fetch_tweets_for_single_user(user_id, fetching_event):
#     """
#     Función asíncrona para buscar tweets para un solo usuario.
#     Se detiene si el evento fetching_event está activado.
#     """
#     print(f"🔍 Iniciando búsqueda de tweets para usuario ID: {user_id}...")

#     # Verificar si el proceso debe detenerse
#     if fetching_event.is_set():
#         print(f"⏹️ Proceso detenido para usuario ID: {user_id}.")
#         return

#     # Contar tweets recolectados hoy
#     tweets_collected_today = await count_tweets_for_user(user_id)
#     print(tweets_collected_today)

#     if tweets_collected_today >= TWEET_LIMIT_PER_HOUR:
#         print(f"⛔ Usuario {user_id} alcanzó el límite de {TWEET_LIMIT_PER_HOUR} tweets hoy. Saltando completamente la búsqueda.")
#         return

#     # Crear una sesión HTTP
#     async with aiohttp.ClientSession() as session:
#         # Consultar usuarios monitoreados
#         query_users = f"SELECT DISTINCT twitter_username FROM monitored_users WHERE user_id = '{user_id}'"
#         monitored_users = run_query(query_users, fetchall=True) or []
#         print(monitored_users)

#         # Consultar keywords monitoreadas
#         query_keywords = f"SELECT DISTINCT keyword FROM user_keywords WHERE user_id = '{user_id}'"
#         monitored_keywords = run_query(query_keywords, fetchall=True) or []
#         print(monitored_keywords)

#         # Si no hay usuarios ni keywords monitoreadas, salir
#         if not monitored_users and not monitored_keywords:
#             print(f"⚠ Usuario {user_id} no tiene usuarios o keywords monitoreadas.")
#             return

#         # Calcular límites
#         user_limit = 11 if len(monitored_users) > 3 else TWEET_LIMIT_PER_HOUR
#         keyword_limit = 11 if len(monitored_keywords) > 3 else TWEET_LIMIT_PER_HOUR

#         # Crear tareas para buscar tweets
#         user_tasks = [
#             fetch_tweets_for_user(session, user_id, username[0], user_limit, fetching_event)
#             for username in monitored_users
#         ]
#         keyword_tasks = [
#             fetch_tweets_for_keyword(session, user_id, keyword[0], keyword_limit, fetching_event)
#             for keyword in monitored_keywords
#         ]

#         # Ejecutar todas las tareas
#         try:
#             await asyncio.gather(*user_tasks, *keyword_tasks)
#         except asyncio.CancelledError:
#             print(f"⏹️ Tareas canceladas para usuario ID: {user_id}.")

#     print(f"✅ Búsqueda de tweets completada para usuario ID: {user_id}.")


async def fetch_tweets_for_single_user(user_id, fetching_event):
    print(f"🔍 Iniciando búsqueda de tweets para usuario ID: {user_id}...")

    if fetching_event.is_set():
        print(f"⏹️ Proceso detenido para usuario ID: {user_id}.")
        return

    query_users = f"SELECT DISTINCT twitter_username FROM monitored_users WHERE user_id = '{user_id}'"
    monitored_users = run_query(query_users, fetchall=True) or []

    query_keywords = f"SELECT DISTINCT keyword FROM user_keywords WHERE user_id = '{user_id}'"
    monitored_keywords = run_query(query_keywords, fetchall=True) or []

    if not monitored_users or not monitored_keywords:
        print(f"⚠ Usuario {user_id} no tiene usuarios o palabras clave monitoreadas.")
        return

    limit = 11 if len(monitored_users) > 3 else TWEET_LIMIT_PER_HOUR

    async with aiohttp.ClientSession() as session:
        await fetch_tweets_for_monitored_users_with_keywords(
            session,
            user_id,
            [user[0] for user in monitored_users],
            [keyword[0] for keyword in monitored_keywords],
            limit,
            fetching_event
        )

    print(f"✅ Búsqueda de tweets completada para usuario ID: {user_id}.")
    
    
async def fetch_tweets_for_all_users(fetching_event):
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


