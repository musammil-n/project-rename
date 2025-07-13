from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command(["start", "help"]))
async def help_command(client: Client, message: Message):
    help_text = """
🤖 **Advanced File Rename Bot**  
*With Watermarking, Metadata Editing & File Combining*

🔹 **Main Features:**
- ✏️ Rename files with custom prefix/suffix
- 🖼️ Custom thumbnails & auto-thumbnail generation
- 💧 Add watermarks to images/videos
- 🎵 Edit audio/video metadata
- 🔀 Combine multiple files (videos/audio/PDFs)

📌 **Basic Commands:**
/start - Show this help message  
/help - Show detailed help  
/settings - View your current settings  

🔄 **File Renaming:**
/rename [new_name] - Rename a file (reply to file)  
/r [new_name] - Shortcut for /rename  

🎨 **Thumbnail Options:**
/setthumb - Set custom thumbnail (reply to image)  
/removethumb - Remove custom thumbnail  
/autothumb [on/off] - Toggle auto-thumbnail  

💧 **Watermarking:**
/setwatermark [text] - Set watermark text  
/wm [text] - Shortcut for /setwatermark  
*Options:* position=, opacity=, size=  
*Example:* `/setwatermark @Channel position=center opacity=70 size=30`

📝 **Metadata Editing:**
/setmetadata - Set file metadata  
/meta - Shortcut for /setmetadata  
*Example:* `/setmetadata title="My Song" artist="Artist"`  
/showmetadata - View file metadata (reply to file)  

🔀 **File Combining:**
/combine - Start combine mode (reply to first file)  
/merge - Alias for /combine  
/finishcombine [name] - Finish combining files  
/cancelcombine - Cancel combine operation  

⚙️ **Prefix/Suffix:**
/setprefix [text] - Set filename prefix  
/setsuffix [text] - Set filename suffix  

📊 **Current Limitations:**
- Max combined file size: 500MB  
- Supported combine types: MP4, MP3, PDF  
- Watermark font: Arial (default)  

🔧 **Need Help?**  
Contact @YourSupportChannel for assistance
"""

    # Create inline keyboard with quick access buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Rename Help", callback_data="help_rename"),
            InlineKeyboardButton("Watermark Help", callback_data="help_watermark")
        ],
        [
            InlineKeyboardButton("Metadata Help", callback_data="help_metadata"),
            InlineKeyboardButton("Combine Help", callback_data="help_combine")
        ],
        [
            InlineKeyboardButton("Close Help", callback_data="close_help")
        ]
    ])

    await message.reply_text(
        help_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback_query):
    data = callback_query.data
    
    if data == "help_rename":
        text = """
📌 **File Renaming Help**

To rename a file:
1. Reply to a file with `/rename NewName`
2. The bot will apply your prefix/suffix settings
3. Optional: Thumbnail will be preserved or generated

🔹 **Examples:**
- `/rename MyFile` → "PrefixMyFileSuffix.ext"
- `/r Shortcut` → Works like /rename

⚙️ **Related Commands:**
/setprefix - Set filename prefix  
/setsuffix - Set filename suffix  
/setthumb - Set custom thumbnail  
/autothumb - Toggle auto-thumbnail
"""
    elif data == "help_watermark":
        text = """
💧 **Watermarking Help**

Add text watermarks to images/videos:

🔹 **Basic Usage:**
`/setwatermark YourText`

⚙️ **Advanced Options:**
- `position=` - top-left, top-right, bottom-left, bottom-right, center  
- `opacity=` - 0-100 (transparency)  
- `size=` - Font size (10-50)  

🔹 **Example:**
`/setwatermark @Channel position=center opacity=70 size=30`

📝 **Notes:**
- Works on images (JPG/PNG) and videos (MP4)
- Watermark is applied during /rename
- Use /setwatermark with no text to remove
"""
    elif data == "help_metadata":
        text = """
📝 **Metadata Editing Help**

Edit file metadata (for supported files):

🔹 **Supported Formats:**
- Audio: MP3, FLAC, WAV, M4A  
- Video: MP4, MOV, AVI  

🔹 **Usage:**
`/setmetadata title="Title" artist="Artist" album="Album"`

🔹 **Example:**
`/meta title="My Song" artist="Best Artist"`

🔍 **View Metadata:**
Reply to a file with `/showmetadata`

📌 **Note:**  
Metadata editing works when using /rename command
"""
    elif data == "help_combine":
        text = """
🔀 **File Combining Help**

Combine multiple files into one:

🔹 **Supported Types:**
- Videos (.mp4)
- Audio (.mp3)
- PDFs (.pdf)

🔹 **How to Combine:**
1. Reply to first file with `/combine`
2. Send more files of same type
3. Use `/finishcombine OutputName` when done

⚙️ **Options:**
- Max combined size: 500MB  
- Use `/cancelcombine` to abort  

🔹 **Example:**
1. Reply to video1.mp4 with `/combine`
2. Send video2.mp4, video3.mp4
3. `/finishcombine MyCombinedVideo`
"""
    else:
        text = "ℹ️ Select a help topic from the buttons"

    await callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Main Help", callback_data="back_to_main")]
        ])
    )

@Client.on_callback_query(filters.regex("^back_to_main$"))
async def back_to_main(client: Client, callback_query):
    # Resend the original help message
    await help_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("^close_help$"))
async def close_help(client: Client, callback_query):
    await callback_query.message.delete()
