from dotenv import load_dotenv
load_dotenv()

import os

class BOT:
    TOKEN = os.environ.get("TOKEN", "")

class API:
    HASH = os.environ.get("API_HASH", "")
    ID = int(os.environ.get("API_ID", 0))

class OWNER:
    ID = int(os.environ.get("OWNER", 0))

class WEB:
    PORT = int(os.environ.get("PORT", 8000))

class CHATS:
    IDS = list(map(int, os.environ.get("CHATS", "").split())) if os.environ.get("CHATS") else []
