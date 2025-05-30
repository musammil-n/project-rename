import os
import asyncio
import urllib.request from pyrogram import Client, filters
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

    try:
        # Download the sent video
        video_file = await message.download(file_name="./downloads/")
        if not video_file:
            await message.reply_text("Failed to download the video.")
            return

        # Download thumbnail
        thumbnail_path = "./downloads/thumbnail.jpg"
        urllib.request.urlretrieve(THUMBNAIL_URL, thumbnail_path)
        if not os.path.exists(thumbnail_path):
            await message.reply_text("Failed to download the thumbnail.")
            if os.path.exists(video_file):
                os.remove(video_file)
            return

        # Extract video metadata
        probe = ffmpeg.probe(video_file)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            await message.reply_text("No video stream found in the file.")
            if os.path.exists(video_file):
                os.remove(video_file)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            return
        duration = int(float(probe['format']['duration']))
        width = video_stream['width']
        height = video_stream['height']
        video_title = os.path.basename(video_file).rsplit('.', 1)[0]

        # Output file path
        output_path = f"./downloads/edited_{video_title}.mp4"

        # Add metadata with "@mnbots in telegram" prefix
        metadata = {
            'title': f"@mnbots in telegram {video_title}",
            'comment': f"@mnbots in telegram - Edited by MN Bots"
        }

        # Embed thumbnail and metadata using FFmpeg
        stream = ffmpeg.input(video_file)
        stream = ffmpeg.output(
            stream,
            output_path,
            **{'c:v': 'copy', 'c:a': 'copy'},  # Copy streams to avoid re-encoding
            **{'metadata': [f"{k}={v}" for k, v in metadata.items()]},
            **{'metadata:s:v:0': f"title=@mnbots in telegram Video"},
            map='0:v',  # Map video stream
            map='0:a?',  # Map audio stream if present
            map_metadata='0',  # Preserve original metadata
            f='mp4'  # Force MP4 format
        )

        # Add thumbnail as a cover image
        thumb_stream = ffmpeg.input(thumbnail_path)
        stream = ffmpeg.output(
            stream,
            thumb_stream,
            output_path,
            **{'c:v:1': 'copy', 'c:a': 'copy'},
            map='1:v',  # Map thumbnail as second video stream
            **{'disposition:v:1': 'attached_pic'},  # Mark as cover image
            **{'metadata:s:v:1': f"title=@mnbots in telegram Thumbnail"},
            movflags='faststart',  # Optimize for streaming and mobile
            overwrite_output=True
        )

        ffmpeg.run(stream)

        # Send video with embedded metadata and thumbnail
        await message.reply_video(
            video=output_path,
            caption=f"@mnbots in telegram {video_title}",
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True
        )

        # Clean up files
        for path in [video_file, thumbnail_path, output_path]:
            if os.path.exists(path):
                os.remove(path)

        await message.reply_text("Video processed with embedded thumbnail and metadata, optimized for mobile players!")

    except Exception as e:
        await message.reply_text(f"Error processing video: {e}")
        # Clean up files in case of error
        for path in [video_file, thumbnail_path, output_path]:
            if os.path.exists(path):
                os.remove(path)

# Register the handler
def register(app: Client):
    app.add_handler(handle_media)
