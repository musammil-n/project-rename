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

    video_file = None  # Initialize video_file outside the try block
    thumbnail_path = None # Initialize thumbnail_path outside the try block
    output_path = None # Initialize output_path outside the try block

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
            return

        # Extract video metadata
        probe = ffmpeg.probe(video_file)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            await message.reply_text("No video stream found in the file.")
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

        # Embed metadata and thumbnail using FFmpeg
        # First pass: Process video and audio streams, add metadata
        stream = ffmpeg.input(video_file)
        thumb_stream = ffmpeg.input(thumbnail_path)

        # Build the FFmpeg command
        # This part requires careful construction. We're essentially trying to combine
        # the main video, add metadata, and also attach the thumbnail as a cover art.
        # The `ffmpeg-python` library simplifies this, but it's important to understand
        # how FFmpeg handles multiple inputs and output options.

        # The following command aims to copy video and audio, apply metadata,
        # and then map the thumbnail as an attached picture.
        # This is a common way to achieve what you're looking for with ffmpeg-python.
        # We need to explicitly tell ffmpeg to map the video and audio from the first input
        # and then map the thumbnail from the second input as an attached picture.

        # Input streams: video_file (0) and thumbnail_path (1)
        # Output mapping:
        # - Map all streams from input 0 (video_file)
        # - Map the video stream from input 1 (thumbnail_path) as an attached picture
        
        # This single ffmpeg.output call should handle both metadata and thumbnail embedding
        ffmpeg_output_args = {
            'c:v': 'copy',  # Copy video stream
            'c:a': 'copy',  # Copy audio stream if present
            'movflags': 'faststart', # Optimize for streaming
            'overwrite_output': True,
        }

        # Add metadata arguments
        for k, v in metadata.items():
            ffmpeg_output_args[f'metadata:{k}'] = v

        # Add specific metadata for video stream
        ffmpeg_output_args['metadata:s:v:0'] = "@mnbots in telegram Video"

        # Construct the complex filter for attaching the thumbnail
        # We'll use the `-i` option for multiple inputs and then map them
        # ffmpeg-python handles the `-i` for us with multiple input streams.
        # We need to explicitly map streams.
        # map 0:v will map video from first input (main video)
        # map 0:a? will map audio from first input (main video), if present
        # map 1:v will map video from second input (thumbnail)
        # disposition:v:1 attached_pic will mark the thumbnail as an attached picture

        (
            ffmpeg
            .output(
                stream, # Main video input
                thumb_stream, # Thumbnail input
                output_path,
                **ffmpeg_output_args,
                map=['0:v', '0:a?'], # Map video and optional audio from main input
                map_metadata='0', # Preserve original metadata from main input
                **{'disposition:v:1': 'attached_pic', 'metadata:s:v:1': "@mnbots in telegram Thumbnail"} # Map thumbnail as attached pic with metadata
            )
            .run(overwrite_output=True)
        )

        # Send video with embedded metadata and thumbnail
        await message.reply_video(
            video=output_path,
            caption=f"@mnbots in telegram {video_title}",
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True
        )

        await message.reply_text("Video processed with embedded thumbnail and metadata, optimized for mobile players!")

    except Exception as e:
        await message.reply_text(f"Error processing video: {e}")
    finally:
        # Clean up files in all cases (success or error)
        for path in [video_file, thumbnail_path, output_path]:
            if path and os.path.exists(path):
                os.remove(path)

