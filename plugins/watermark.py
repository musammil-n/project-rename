import os
import asyncio
import urllib.request
from pyrogram import Client, filters
import ffmpeg
import logging

logger = logging.getLogger(__name__)

# Ensure downloads directory exists
os.makedirs("./downloads", exist_ok=True)

# --- Configuration for Watermarks ---
# Default image watermark URL (Your provided photo URL)
DEFAULT_IMAGE_WATERMARK_URL = "https://i.ibb.co/xW7NS5d/image.jpg" # <--- YOUR PHOTO URL SET HERE
# Default text watermark (Your provided text)
DEFAULT_TEXT_WATERMARK = "join @mnbots in telegram" # <--- YOUR TEXT SET HERE

# Path for the downloaded default image watermark
DEFAULT_IMAGE_WATERMARK_PATH = "./downloads/default_watermark_image.png"

# --- Function to download default watermarks on startup/first use ---
async def ensure_default_watermarks():
    if not os.path.exists(DEFAULT_IMAGE_WATERMARK_PATH):
        try:
            logger.info(f"Downloading default image watermark from {DEFAULT_IMAGE_WATERMARK_URL}...")
            urllib.request.urlretrieve(DEFAULT_IMAGE_WATERMARK_URL, DEFAULT_IMAGE_WATERMARK_PATH)
            logger.info(f"Default image watermark downloaded to {DEFAULT_IMAGE_WATERMARK_PATH}")
        except Exception as e:
            logger.error(f"Failed to download default image watermark: {e}")
            # If download fails, the image watermark simply won't be applied
            pass


# --- Main media handling (only for videos) ---

@Client.on_message(filters.video & filters.private)
async def handle_video_with_watermarks(client, message):
    user_id = message.from_user.id
    logger.info(f"Received video from user {user_id} for watermarking.")

    # Ensure default watermarks are available
    await ensure_default_watermarks()

    input_file_path = None
    output_file_path = None

    try:
        status_message = await message.reply_text("Downloading video...")
        input_file_path = await message.download(file_name="./downloads/")
        if not input_file_path:
            await status_message.edit_text("Failed to download the video.")
            logger.error(f"Failed to download input video for user {user_id}.")
            return

        logger.info(f"Video downloaded: {input_file_path}")
        await status_message.edit_text("Downloaded. Applying watermarks...")

        base_name = os.path.basename(input_file_path).rsplit('.', 1)[0]
        output_file_path = f"./downloads/watermarked_{base_name}.mp4"

        # --- FFmpeg Command Construction ---
        main_video_input = ffmpeg.input(input_file_path)
        video_stream = main_video_input.video
        audio_stream = main_video_input.audio # Get audio stream if exists

        # 1. Image Watermark (Top Left)
        image_watermark_exists = os.path.exists(DEFAULT_IMAGE_WATERMARK_PATH)
        if image_watermark_exists:
            image_watermark_input = ffmpeg.input(DEFAULT_IMAGE_WATERMARK_PATH)
            
            # Overlay image at top left (x=10, y=10 for 10px padding from top and left)
            # Opacity set to 70%
            image_watermark_stream_filtered = image_watermark_input.video.filter('format', 'rgba').filter('colorchannelmixer', aa=0.7)
            video_stream = ffmpeg.filter([video_stream, image_watermark_stream_filtered], 'overlay',
                                         x='10', y='10') 

        # 2. Text Watermark (Bottom Center)
        text_watermark_content = DEFAULT_TEXT_WATERMARK
        text_opacity = 0.8 # 80% opacity for text
        # Positioning for text: x=(W-text_w)/2 for center, y=H-text_h-10 for bottom with padding
        drawtext_cmd = (
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{text_watermark_content}':"
            f"fontcolor=white@{text_opacity}:fontsize=24:x=(w-text_w)/2:y=H-text_h-10"
        )
        video_stream = video_stream.filter('drawtext', **{'drawtext': drawtext_cmd})

        # Combine processed video stream with original audio stream
        final_output = ffmpeg.output(
            video_stream,
            audio_stream, # Map audio from original input
            output_file_path,
            vcodec='libx264', # Re-encode video as we've applied filters
            acodec='copy',    # Copy audio to avoid re-encoding loss/time
            preset='medium',  # Faster than slow, good balance
            crf=26,           # Good quality, adjust 18 (lossless-ish) to 28 (more lossy)
            pix_fmt='yuv420p', # Ensure compatible pixel format
            movflags='faststart' # Optimize for streaming
        )

        logger.info(f"Starting FFmpeg processing for {input_file_path}...")
        try:
            final_output.run(overwrite_output=True, quiet=True)
            logger.info(f"Watermarks applied to {input_file_path}. Output: {output_file_path}")
        except ffmpeg.Error as e:
            error_message = f"FFmpeg execution failed for {input_file_path}. Stderr: {e.stderr.decode() if e.stderr else 'N/A'}. Error: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text(f"Error applying watermarks: {error_message}")
            return

        await status_message.edit_text("Watermarks applied. Uploading...")
        logger.info(f"Uploading processed video: {output_file_path}...")

        # Get video metadata for Pyrogram upload
        try:
            probe = ffmpeg.probe(output_file_path)
            output_video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if output_video_stream:
                output_duration = int(float(probe['format']['duration']))
                output_width = output_video_stream['width']
                output_height = output_video_stream['height']
            else:
                output_duration, output_width, output_height = 0, 0, 0 # Fallback
        except Exception as e:
            logger.warning(f"Could not probe output video for upload metadata: {e}")
            output_duration, output_width, output_height = 0, 0, 0


        await message.reply_video(
            video=output_file_path,
            caption=f"Watermarked by @mnbots - {base_name}",
            duration=output_duration,
            width=output_width,
            height=output_height,
            supports_streaming=True
        )

        logger.info(f"Watermarked video uploaded successfully for {user_id}.")
        await status_message.edit_text("Watermarked video uploaded successfully!")

    except Exception as e:
        logger.exception(f"An unhandled error occurred for user {user_id}: {e}")
        await message.reply_text(f"An unexpected error occurred: {e}")
    finally:
        # Cleanup temporary files
        files_to_clean = [input_file_path, output_file_path]
        for path in files_to_clean:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up: {path}")
                except OSError as e:
                    logger.error(f"Error cleaning up {path}: {e}")

# Register the handler
def register(app: Client):
    app.add_handler(handle_video_with_watermarks)
