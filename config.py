import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    
    # TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
    # TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
    # TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    # TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    # TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SOCIALDATA_API_KEY = os.getenv("SOCIALDATA_API_KEY")
