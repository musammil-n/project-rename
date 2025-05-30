import os
import asyncio
import urllib.request
from pyrogram import Client, filters
import ffmpeg
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

# --- Configuration for Watermarks ---
# Default image watermark URL (Your provided photo URL)
DEFAULT_IMAGE_WATERMARK_URL = "https://i.ibb.co/xW7NS5d/image.jpg"
# Default text watermark (Your provided text)
DEFAULT_TEXT_WATERMARK = "join @mnbots in telegram"

# Path for the downloaded default image watermark
DEFAULT_IMAGE_WATERMARK_PATH = "./downloads/default_watermark_image.png"

# Ensure downloads directory exists
os.makedirs("./downloads", exist_ok=True)

# --- Function to download default watermarks on startup/first use ---
async def ensure_default_watermarks():
    """
    Downloads the default image watermark if it doesn't already exist.
    This prevents repeated downloads and ensures the file is available.
    """
    if not os.path.exists(DEFAULT_IMAGE_WATERMARK_PATH):
        try:
            logger.info(f"Downloading default image watermark from {DEFAULT_IMAGE_WATERMARK_URL}...")
            urllib.request.urlretrieve(DEFAULT_IMAGE_WATERMARK_URL, DEFAULT_IMAGE_WATERMARK_PATH)
            logger.info(f"Default image watermark downloaded to {DEFAULT_IMAGE_WATERMARK_PATH}")
        except Exception as e:
            logger.error(f"Failed to download default image watermark from {DEFAULT_IMAGE_WATERMARK_URL}. Error: {e}")
            # If download fails, the image watermark simply won't be applied,
            # but the bot will continue attempting to process the video with text watermark.
            pass


# --- Main media handling for videos ---
@Client.on_message(filters.video & filters.private)
async def handle_video_with_watermarks(client, message):
    """
    Handles incoming video messages in private chats, applies a photo watermark
    to the top-left and a text watermark to the bottom-center, then uploads
    the processed video.
    """
    user_id = message.from_user.id
    logger.info(f"Received video from user {user_id} for watermarking.")

    # Ensure default watermarks are downloaded before processing
    await ensure_default_watermarks()

    input_file_path = None
    output_file_path = None
    status_message = None # Initialize status_message for cleanup in finally block

    try:
        # Send initial status message
        status_message = await message.reply_text("Downloading video...")
        
        # Download the input video
        input_file_path = await message.download(file_name="./downloads/")
        if not input_file_path:
            logger.error(f"Failed to download input video from user {user_id}. Download returned None.")
            await status_message.edit_text("Failed to download the video.")
            return

        logger.info(f"Video downloaded: {input_file_path}")
        await status_message.edit_text("Downloaded. Applying watermarks...")

        # Determine output file path
        base_name = os.path.basename(input_file_path).rsplit('.', 1)[0]
        output_file_path = f"./downloads/watermarked_{base_name}.mp4"

        # --- FFmpeg Command Construction ---
        main_video_input = ffmpeg.input(input_file_path)
        video_stream = main_video_input.video
        audio_stream = main_video_input.audio # Get audio stream if it exists

        # 1. Image Watermark (Top Left)
        image_watermark_exists = os.path.exists(DEFAULT_IMAGE_WATERMARK_PATH)
        if image_watermark_exists:
            image_watermark_input = ffmpeg.input(DEFAULT_IMAGE_WATERMARK_PATH)
            
            # Apply opacity (70%) and then overlay the image.
            # x='10', y='10' places it 10 pixels from the left and 10 pixels from the top.
            image_watermark_stream_filtered = image_watermark_input.video.filter('format', 'rgba').filter('colorchannelmixer', aa=0.7)
            video_stream = ffmpeg.filter([video_stream, image_watermark_stream_filtered], 'overlay',
                                         x='10', y='10') 
            logger.info("Image watermark configured for top-left position.")
        else:
            logger.warning("Default image watermark file not found. Skipping image watermark.")

        # 2. Text Watermark (Bottom Center)
        text_watermark_content = DEFAULT_TEXT_WATERMARK
        text_opacity = 0.8 # 80% opacity for text
        
        # FFmpeg drawtext filter command string
        # fontfile: Path to a font on the system (DejaVuSans.ttf is common on Debian)
        # text: The actual text content
        # fontcolor: Color of the text (white@0.8 means white with 80% opacity)
        # fontsize: Size of the text
        # x=(w-text_w)/2: Centers the text horizontally
        # y=H-text_h-10: Places text 10 pixels from the bottom edge
        drawtext_cmd = (
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{text_watermark_content}':"
            f"fontcolor=white@{text_opacity}:fontsize=24:x=(w-text_w)/2:y=H-text_h-10"
        )
        # Apply the drawtext filter directly with the command string
        video_stream = video_stream.filter('drawtext', drawtext_cmd)
        logger.info("Text watermark configured for bottom-center position.")

        # Combine processed video stream with original audio stream
        # Re-encode video because filters are applied. Copy audio.
        final_output = ffmpeg.output(
            video_stream,
            audio_stream, # Map audio from original input (if exists)
            output_file_path,
            vcodec='libx264',    # Video codec for re-encoding
            acodec='copy',       # Copy audio codec (no re-encoding)
            preset='medium',     # Encoding speed vs. compression efficiency (ultrafast, superfast, medium, slow, etc.)
            crf=26,              # Constant Rate Factor for video quality (lower is better quality, larger file size)
            pix_fmt='yuv420p',   # Pixel format for compatibility (especially with older players)
            movflags='faststart' # Optimize for web streaming (metadata at beginning)
        )

        logger.info(f"Starting FFmpeg execution for {input_file_path}...")
        try:
            # Run the FFmpeg command.
            # overwrite_output=True: Allows FFmpeg to overwrite output file if it exists.
            # quiet=True: Suppresses FFmpeg's verbose output to stdout/stderr.
            final_output.run(overwrite_output=True, quiet=True)
            logger.info(f"Watermarks applied successfully. Output: {output_file_path}")
        except ffmpeg.Error as e:
            error_message = f"FFmpeg execution failed for {input_file_path}. Stderr: {e.stderr.decode() if e.stderr else 'N/A'}. Error: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text(f"Error applying watermarks: {error_message}")
            return

        await status_message.edit_text("Watermarks applied. Uploading...")
        logger.info(f"Uploading processed video: {output_file_path}...")

        # Get metadata of the output video for Pyrogram upload parameters
        try:
            probe = ffmpeg.probe(output_file_path)
            output_video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            output_duration = int(float(probe['format']['duration'])) if 'duration' in probe['format'] else 0
            output_width = output_video_stream['width'] if output_video_stream else 0
            output_height = output_video_stream['height'] if output_video_stream else 0
        except Exception as e:
            logger.warning(f"Could not probe output video for upload metadata. Error: {e}. Using default values.")
            output_duration, output_width, output_height = 0, 0, 0 # Fallback values

        # Upload the watermarked video to Telegram
        await message.reply_video(
            video=output_file_path,
            caption=f"Watermarked by {DEFAULT_TEXT_WATERMARK} - {base_name}",
            duration=output_duration,
            width=output_width,
            height=output_height,
            supports_streaming=True
        )

        logger.info(f"Watermarked video uploaded successfully for user {user_id}.")
        await status_message.edit_text("Watermarked video uploaded successfully!")

    except Exception as e:
        # Catch any unexpected errors during the entire process
        logger.exception(f"An unhandled error occurred during video processing for user {user_id}. Error: {e}")
        if status_message:
            await status_message.edit_text(f"An unexpected error occurred: {e}")
        else:
            await message.reply_text(f"An unexpected error occurred: {e}")
    finally:
        # Ensure all temporary files are cleaned up
        files_to_clean = [input_file_path, output_file_path]
        for path in files_to_clean:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up temporary file: {path}")
                except OSError as e:
                    logger.error(f"Error cleaning up file {path}: {e}")

# Register the handler with the Pyrogram client
def register(app: Client):
    """
    Registers the handle_video_with_watermarks function as a message handler
    for the Pyrogram client.
    """
    app.add_handler(handle_video_with_watermarks)
