import pg8000.native as pg
from flask import g
from config import Config
from openai import OpenAI

client = OpenAI(api_key=Config.OPENAI_API_KEY)

def get_db():
    """Conexión a la base de datos utilizando pg8000.native y Flask context g."""
    if 'db' not in g:
        g.db = pg.Connection(
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            database=Config.DB_NAME
        )
    return g.db

def close_db(e=None):
    """Cerrar la conexión a la base de datos al finalizar la petición."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def run_query(query, params=None, fetchone=False, fetchall=False):
    """Ejecutar una consulta SQL en PostgreSQL con pg8000."""
    db = get_db()

    if params is None:
        params = ()
    
    try:
        result = db.run(query, params)

        if fetchone:
            return result[0] if result else None
        if fetchall:
            return result

        return None
    except Exception as e:
        print(f"❌ Error en consulta SQL: {str(e)}")
        return None


# Función para registrar logs
def log_event(user_id, event_type, description):
    query = f"""
    INSERT INTO logs (user_id, event_type, event_description)
    VALUES ('{user_id}', '{event_type}', '{description}')
    """
    run_query(query)

def translate_text_with_openai(text, target_language):
    """
    :param text: Texto a traducir.
    :param target_language: Idioma al que se traducirá el texto (por ejemplo, "es", "en", "fr").
    :return: Texto traducido.
    """
    prompt = f"Translate the following text (not the usernames (@)) into only this language: {target_language}: '{text}'. Focus solely on the general message without adding irrelevant or distracting details or text. NEVER add a text that is not a translation of the original text example: 'Sure! Here’s the translation:'"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo de chat
            messages=[
                {"role": "system", "content": "Eres un traductor experto."},
                {"role": "user", "content": f"{prompt}"}
            ],
            max_tokens=100,  # Máximo número de tokens en la respuesta
            temperature=0.5  # Controla la creatividad de la respuesta
        )
        translated_text = response.choices[0].message.content.strip()
        return translated_text
    except Exception as e:
        print(f"❌ Error al traducir con OpenAI: {str(e)}")
        return None
    
def save_collected_tweet(user_id, source_type, source_value, tweet_id, tweet_text, created_at):
    """
    Guarda un tweet recolectado en la base de datos solo si no existe previamente.
    Antes de guardar, traduce el tweet al idioma asignado al usuario.
    """
    # 🔍 Verificar si el tweet ya existe en la base de datos
    check_query = f"SELECT 1 FROM collected_tweets WHERE tweet_id = '{tweet_id}' LIMIT 1"
    existing_tweet = run_query(check_query, fetchone=True)
    if existing_tweet:
        print(f"⚠ Tweet {tweet_id} ya existe. No se guardará.")
        return  # 🚫 No hacer nada si el tweet ya existe

    # Consultar el idioma asignado al usuario
    language_query = f"SELECT language FROM users WHERE id = {user_id}"
    user_language = run_query(language_query, fetchone=True)
    if not user_language:
        print(f"❌ No se encontró el idioma para el usuario {user_id}.")
        return

    target_language = user_language[0]  # Idioma asignado al usuario

    # Traducir el tweet usando OpenAI
    translated_text = translate_text_with_openai(tweet_text, target_language)
    if not translated_text:
        print(f"❌ No se pudo traducir el tweet {tweet_id}. No se guardará.")
        return

    print(f"🌐 Tweet traducido al idioma '{target_language}': {translated_text}")

    # 📝 Insertar el tweet traducido en la base de datos
    insert_query = f"""
    INSERT INTO collected_tweets (user_id, source_type, source_value, tweet_id, tweet_text, created_at)
    VALUES ({user_id if user_id is not None else 'NULL'}, 
            '{source_type}', 
            '{source_value}', 
            '{tweet_id}', 
            '{translated_text.replace("'", "''")}', 
            '{created_at}')
    """
    run_query(insert_query)
    print(f"✅ Tweet {tweet_id} guardado correctamente.")

