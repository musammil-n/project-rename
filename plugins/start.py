from pyrogram import Client 
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER  # Your Telegram user ID


# Text and buttons
class TEXT:
    START = """
<b>I’m a powerful Terabox downloader!</b>

📥 Send me a Terabox link to download.
⚠️ Only videos under 200MB are supported.
📢 Don’t forget to join our update channel.
🗑  Before these things you need to add set up dumb chat (bot only send files in dumb chat).

<b>How to set up the dumb channel: </b>
1. Create a new channel. 
2. Make the bot an admin with all permissions. 
3. Send the command: /setchat followed by your channel ID.

"""
    DEVELOPER = "👨‍💻 Developer"
    UPDATES_CHANNEL = "📢 Updates Channel"
    SOURCE_CODE = "💬 Support Group"

class INLINE:
    START_BTN = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TEXT.DEVELOPER, url="https://t.me/mn_movies_bot")],
            [
                InlineKeyboardButton(TEXT.UPDATES_CHANNEL, url="https://t.me/MNBots"),
                InlineKeyboardButton(TEXT.SOURCE_CODE, url="https://t.me/MNBots_support"),
            ],
        ]
    )

@Client.on_message(filters.command("start"))
async def start(client: MN_Bot, message: Message):
    user = message.from_user
    mention = user.mention
    await message.reply_text(
        TEXT.START,
        disable_web_page_preview=True,
        reply_markup=INLINE.START_BTN,
    )

    # Notify owner
    try:
        await client.send_message(
            chat_id=OWNER,
            text=f"👤 User [{mention}](tg://user?id={user.id}) started the bot.\n🆔 User ID: <code>{user.id}</code>",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"[Owner Notification Error] {e}")
