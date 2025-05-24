from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserIsBlocked, PeerIdInvalid, FloodWait
from pymongo import MongoClient
import asyncio
import logging
import os

# === Logging ===
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# === Config ===
OWNER_ID = 123456789  # Change this to your Telegram ID
BATCH_SIZE = 20
BATCH_DELAY = 2

# === MongoDB via Koyeb ===
MONGO_URL = os.environ.get("MONGO_URL")
mongo = MongoClient(MONGO_URL)
db = mongo["mybot"]
users_collection = db["users"]

# === Reply Markup ===
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("Bot Updates", url="https://t.me/mnbots")],
    [
        InlineKeyboardButton("Add to Group", url="https://t.me/All_Request_Accept_Bot?startgroup=AdBots&admin=invite_users+manage_chat"),
        InlineKeyboardButton("Add to Channel", url="https://t.me/All_Request_Accept_Bot?startchannel=AdBots&admin=invite_users+manage_chat")
    ]
])

# === Handle Chat Join Request ===
@Client.on_chat_join_request()
async def handle_join_request(client, r):
    user_id = r.from_user.id
    name = r.from_user.first_name or r.from_user.username or "Unknown"

    # Save user
    users_collection.update_one({"_id": user_id}, {"$set": {"name": name}}, upsert=True)

    try:
        await client.send_message(
            user_id,
            "👋 Hi! Your join request was received. Please wait for approval.",
            reply_markup=reply_markup
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await client.send_message(user_id, "👋 Hi! Your join request was received. Please wait for approval.", reply_markup=reply_markup)
        except Exception as e2:
            logger.warning(f"Retry failed: {e2}")
    except UserIsBlocked:
        logger.warning(f"User blocked the bot: {user_id}")
    except PeerIdInvalid:
        logger.warning(f"Invalid peer ID: {user_id}")
    except Exception as e:
        logger.error(f"Error sending message to {user_id}: {e}")

# === Broadcast Handler ===
@Client.on_message(filters.command("broadcast") & filters.reply)
async def broadcast_handler(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("🚫 You are not authorized to use this command.")

    reply_msg = message.reply_to_message
    users = list(users_collection.find())
    total = len(users)
    sent = failed = 0
    progress = await message.reply(f"📢 Broadcast started...\n✅ Sent: {sent}\n❌ Failed: {failed}\n⏳ Total: {total}")

    for i in range(0, total, BATCH_SIZE):
        batch = users[i:i+BATCH_SIZE]
        tasks = [send_copy(client, reply_msg, user["_id"]) for user in batch]
        results = await asyncio.gather(*tasks)

        sent += results.count(True)
        failed += results.count(False)

        try:
            await progress.edit_text(
                f"📢 Broadcasting...\n✅ Sent: {sent}\n❌ Failed: {failed}\n📦 Batch: {i + BATCH_SIZE}/{total}"
            )
        except:
            pass

        await asyncio.sleep(BATCH_DELAY)

    await progress.edit_text(f"✅ Broadcast complete!\n\n📬 Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {total}")

# === Safe Copy Sender ===
async def send_copy(client, msg, user_id):
    try:
        await msg.copy(user_id)
        return True
    except (UserIsBlocked, PeerIdInvalid):
        users_collection.delete_one({"_id": user_id})
        return False
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await msg.copy(user_id)
            return True
        except:
            return False
    except:
        return False
