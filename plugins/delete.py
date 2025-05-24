from pyrogram import Client, filters
import asyncio
from config import CHATS

@Client.on_message(filters.group)
async def auto_delete_handler(client, message):
    if message.chat.id not in CHATS.IDS:
        return
    if message.text and message.text.startswith("/"):
        return
    await asyncio.sleep(CHATS.DELETE_DELAY)
    try:
        await message.delete()
    except Exception as e:
        print(f"Failed to delete message: {e}")
