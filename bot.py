import logging
import threading
import time
import os
from flask import Flask
from pyrogram import Client, filters
from pyrogram import utils as pyroutils
from pyrogram.types import Message, InputFile
from config import BOT, API, OWNER

# ✅ Peer ID Fix
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -10099999999999

# 📝 Logging Setup (logs to file & console)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs-@mnbots.txt"),
        logging.StreamHandler()
    ]
)

# ✅ Flask Health Check App
app = Flask(__name__)

@app.route('/')
def home():
    return "MN Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8000)

# 🤖 MN Bot Class
class MN_Bot(Client):
    def __init__(self):
        super().__init__(
            "MN-Bot",
            api_id=API.ID,
            api_hash=API.HASH,
            bot_token=BOT.TOKEN,
            plugins=dict(root="plugins"),
            workers=16,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        BOT.USERNAME = f"@{me.username}"
        self.mention = me.mention
        self.username = me.username
        await self.send_message(chat_id=OWNER.ID,
                                text=f"✅ {me.first_name} BOT started successfully!")
        logging.info(f"✅ {me.first_name} BOT started successfully")

    async def stop(self, *args):
        await super().stop()
        logging.info("🛑 Bot stopped.")

# ➕ /log command to send log file to owner
@MN_Bot.on_message(filters.command("log") & filters.user(OWNER.ID))
async def send_log(client: MN_Bot, message: Message):
    log_path = "logs-@mnbots.txt"
    if os.path.exists(log_path):
        await message.reply_document(document=InputFile(log_path), caption="Here is the log file.")
    else:
        await message.reply("❌ Log file not found.")

# 🚀 Entry Point
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    while True:
        try:
            MN_Bot().run()
        except Exception as e:
            logging.error(f"❌ Bot crashed with error: {e}")
            time.sleep(5)  # Wait before restarting
