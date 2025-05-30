import os
import asyncio
import urllib.request
from pyrogram import Client, filters
import ffmpeg
import logging

# Configure logging (already done, just including for context)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thumbnail URL
THUMBNAIL_URL = "https://i.ibb.co/MDwd1f3D/6087047735061627461.jpg"

# Ensure downloads directory exists
os.makedirs("./downloads", exist_ok=True)

# Handler for media messages in private chats
@Client.on_message(filters.private & filters.media)
async def handle_media(client, message):
    logger.info(f"Received media message from user {message.from_user.id}")

    if not message.video:
        logger.warning(f"User {message.from_user.id} sent non-video media.")
        await message.reply_text("Please send a video file to process.")
        return

    video_file = None
    thumbnail_path = None
    output_path = None

    try:
        status_message = await message.reply_text("Downloading video...")
        logger.info(f"Attempting to download video from {message.from_user.id}...")
        video_file = await message.download(file_name="./downloads/")
        if not video_file:
            logger.error(f"Failed to download video from {message.from_user.id}. download() returned None.")
            await status_message.edit_text("Failed to download the video.")
            return

        logger.info(f"Video downloaded to {video_file}. Downloading thumbnail...")
        await status_message.edit_text("Video downloaded. Downloading thumbnail...")

        thumbnail_path = "./downloads/thumbnail.jpg"
        try:
            urllib.request.urlretrieve(THUMBNAIL_URL, thumbnail_path)
        except Exception as e:
            logger.error(f"Failed to download thumbnail from URL: {THUMBNAIL_URL}. Error: {e}")
            await status_message.edit_text("Failed to download the thumbnail.")
            return

        if not os.path.exists(thumbnail_path):
            logger.error(f"Thumbnail not found at {thumbnail_path} after download attempt.")
            await status_message.edit_text("Failed to download the thumbnail.")
            return

        logger.info(f"Thumbnail downloaded to {thumbnail_path}. Processing video...")
        await status_message.edit_text("Thumbnail downloaded. Processing video...")

        try:
            probe = ffmpeg.probe(video_file)
        except ffmpeg.Error as e:
            logger.error(f"FFprobe failed to probe video file {video_file}. Stderr: {e.stderr.decode()}")
            await status_message.edit_text(f"Failed to get video metadata: {e.stderr.decode()}")
            return
        except Exception as e:
            logger.error(f"An unexpected error occurred during FFprobe for {video_file}. Error: {e}")
            await status_message.edit_text(f"An unexpected error occurred during video metadata extraction: {e}")
            return

        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            logger.error(f"No video stream found in file: {video_file}")
            await status_message.edit_text("No video stream found in the file.")
            return

        duration = int(float(probe['format']['duration']))
        width = video_stream['width']
        height = video_stream['height']
        video_title = os.path.basename(video_file).rsplit('.', 1)[0]

        output_path = f"./downloads/edited_{video_title}.mp4"
        logger.info(f"Output path set to: {output_path}")

        metadata = {
            'title': f"@mnbots in telegram {video_title}",
            'comment': f"@mnbots in telegram - Edited by MN Bots"
        }

        main_video_input = ffmpeg.input(video_file)
        thumbnail_input = ffmpeg.input(thumbnail_path)

        logger.info(f"Starting FFmpeg processing for {video_file}...")
        try:
            # We'll pass the inputs as a list to ffmpeg.output() and specify the mapping more directly
            (
                ffmpeg
                .output(
                    main_video_input, # First input stream (index 0)
                    thumbnail_input,  # Second input stream (index 1)
                    output_path,
                    vcodec='copy',
                    acodec='copy',
                    movflags='faststart',
                    # Explicitly map video and audio from the first input (main_video_input)
                    # And map the video from the second input (thumbnail_input) as an attached picture
                    # The 'map' option takes a list of stream specifiers.
                    map=['0:v:0', '0:a:0?', '1:v:0'], # Using specific indices for clarity
                    **{'disposition:v:1': 'attached_pic', 'metadata:s:v:1': '@mnbots in telegram Thumbnail'},
                    **{f'metadata:{k}': v for k, v in metadata.items()},
                    **{'metadata:s:v:0': '@mnbots in telegram Video'},
                )
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"FFmpeg processing complete for {video_file}.")
        except ffmpeg.Error as e:
            error_message = f"FFmpeg execution failed for {video_file}. Stderr: {e.stderr.decode() if e.stderr else 'N/A'}. Error: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text(f"Error processing video: {error_message}")
            return

        await status_message.edit_text("Video processing complete. Uploading...")
        logger.info(f"Uploading processed video: {output_path}...")

        await message.reply_video(
            video=output_path,
            caption=f"@mnbots in telegram {video_title}",
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True
        )

        logger.info(f"Video uploaded successfully for {message.from_user.id}.")
        await status_message.edit_text("Video uploaded successfully!")

    except Exception as e:
        logger.exception(f"An unhandled error occurred during video processing for user {message.from_user.id}. Error: {e}")
        await message.reply_text(f"An unexpected error occurred: {e}")
    finally:
        files_to_clean = [video_file, thumbnail_path, output_path]
        for path in files_to_clean:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up: {path}")
                except OSError as e:
                    logger.error(f"Error cleaning up file {path}: {e}")

# Register the handler
def register(app: Client):
    app.add_handler(handle_media)
