import os
import asyncio
import urllib.request
from pyrogram import Client, filters
import ffmpeg

# Thumbnail URL
THUMBNAIL_URL = "https://i.ibb.co/MDwd1f3D/6087047735061627461.jpg"

# Ensure downloads directory exists
os.makedirs("./downloads", exist_ok=True)

# Handler for media messages in private chats
@Client.on_message(filters.private & filters.media)
async def handle_media(client, message):
    # Check if the media is a video
    if not message.video:
        await message.reply_text("Please send a video file to process.")
        return

    video_file = None
    thumbnail_path = None
    output_path = None

    try:
        status_message = await message.reply_text("Downloading video...")
        video_file = await message.download(file_name="./downloads/")
        if not video_file:
            await status_message.edit_text("Failed to download the video.")
            return

        await status_message.edit_text("Video downloaded. Downloading thumbnail...")
        thumbnail_path = "./downloads/thumbnail.jpg"
        urllib.request.urlretrieve(THUMBNAIL_URL, thumbnail_path)
        if not os.path.exists(thumbnail_path):
            await status_message.edit_text("Failed to download the thumbnail.")
            return

        await status_message.edit_text("Thumbnail downloaded. Processing video...")

        probe = ffmpeg.probe(video_file)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            await status_message.edit_text("No video stream found in the file.")
            return

        duration = int(float(probe['format']['duration']))
        width = video_stream['width']
        height = video_stream['height']
        video_title = os.path.basename(video_file).rsplit('.', 1)[0]

        output_path = f"./downloads/edited_{video_title}.mp4"

        metadata = {
            'title': f"@mnbots in telegram {video_title}",
            'comment': f"@mnbots in telegram - Edited by MN Bots"
        }

        main_video_input = ffmpeg.input(video_file)
        thumbnail_input = ffmpeg.input(thumbnail_path)

        # Construct FFmpeg output stream
        # The 'overwrite_output' and 'quiet' parameters should be passed to .run()
        # not directly in the .output() chain as FFmpeg options.
        (
            ffmpeg
            .output(
                main_video_input,
                thumbnail_input,
                output_path,
                vcodec='copy',
                acodec='copy',
                movflags='faststart',
                map=['0:v', '0:a?', '1:v'],
                **{'disposition:v:1': 'attached_pic', 'metadata:s:v:1': '@mnbots in telegram Thumbnail'},
                **{f'metadata:{k}': v for k, v in metadata.items()},
                **{'metadata:s:v:0': '@mnbots in telegram Video'},
            )
            .run(overwrite_output=True, quiet=True) # <-- Corrected: Pass overwrite_output here
        )

        await status_message.edit_text("Video processing complete. Uploading...")

        await message.reply_video(
            video=output_path,
            caption=f"@mnbots in telegram {video_title}",
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True
        )

        await status_message.edit_text("Video uploaded successfully!")

    except ffmpeg.Error as e:
        error_message = f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
        await message.reply_text(f"Error processing video: {error_message}")
        print(f"FFmpeg Error Details: {error_message}")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")
        print(f"Unexpected Error: {e}")
    finally:
        files_to_clean = [video_file, thumbnail_path, output_path]
        for path in files_to_clean:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Cleaned up: {path}")
                except OSError as e:
                    print(f"Error cleaning up {path}: {e}")

# Register the handler (assuming this is in a plugin file like 'meta.py')
def register(app: Client):
    app.add_handler(handle_media)

# Note: Your main bot starting code should be in a separate file, e.g., bot.py,
# and it should import and register this handler.
# Example:
# from pyrogram import Client
# import os
# from plugins.meta import register as register_meta_plugin # assuming your code is in plugins/meta.py

# API_ID = os.environ.get("API_ID")
# API_HASH = os.environ.get("API_HASH")
# BOT_TOKEN = os.environ.get("BOT_TOKEN")

# app = Client(
#     "my_bot_session",
#     api_id=int(API_ID),
#     api_hash=API_HASH,
#     bot_token=BOT_TOKEN
# )

# @app.on_message(filters.command("start") & filters.private)
# async def start_command(client, message):
#     await message.reply_text("Hello! Send me a video and I will process it.")

# register_meta_plugin(app) # Register the media handler

# if __name__ == "__main__":
#     print("Bot starting...")
#     app.run()
#     print("Bot stopped.")
