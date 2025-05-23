from pyrogram import Client 
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER  # OWNER.ID is used

# Text and buttons
class TEXT:
    START = """
<b>👋 Hi! I'm your personal Admin Assistant Bot.</b>

💬 When users message me, their messages are instantly forwarded to my admin.

📨 If the admin replies, I’ll send that reply back to the original user — all privately.

<b>Simple. Private. Effective.</b>

No commands needed — just start chatting!
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
async def start(client: Client, message: Message):
    user = message.from_user
    mention = user.first_name or "User"
    await message.reply_text(
        TEXT.START,
        disable_web_page_preview=True,
        reply_markup=INLINE.START_BTN,
    )

    # Notify owner
    try:
        await client.send_message(
            chat_id=OWNER.ID,
            text=f"👤 User <a href='tg://user?id={user.id}'>{mention}</a> started the bot.\n🆔 User ID: <code>{user.id}</code>",
            disable_web_page_preview=True,
            parse_mode="html"
        )
    except Exception as e:
        print(f"[Owner Notification Error] {e}")
