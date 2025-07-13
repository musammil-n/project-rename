import os
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import subprocess
import ffmpeg

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# Constants
WATERMARK_FONT = "arial.ttf"  # Make sure this font file exists
TEMP_DIR = "temp_files"
MAX_COMBINE_SIZE = 500 * 1024 * 1024  # 500MB limit for combined files
SUPPORTED_COMBINE_TYPES = [".mp4", ".mp3", ".pdf"]

# Helper functions
async def clean_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)
    return cleaned[:64]  # Limit length

async def get_user_settings(user_id: int, db) -> Dict:
    """Get user settings from database"""
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        default_settings = {
            "prefix": "",
            "suffix": "",
            "auto_thumbnail": False,
            "thumbnail": None,
            "watermark_text": "",
            "watermark_position": "bottom-right",
            "watermark_opacity": 50,
            "watermark_size": 20,
            "metadata_title": "",
            "metadata_artist": "",
            "metadata_album": "",
            "last_activity": datetime.utcnow(),
            "rename_count": 0,
            "combine_mode": False,
            "combine_files": []
        }
        await db.users.insert_one({"user_id": user_id, **default_settings})
        return default_settings
    return user

async def update_user_settings(user_id: int, update_data: Dict, db):
    """Update user settings in database"""
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )

async def generate_thumbnail(file_path: str) -> Optional[BytesIO]:
    """Generate thumbnail from file"""
    try:
        if file_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            with Image.open(file_path) as img:
                img.thumbnail((320, 320))
                thumb = BytesIO()
                img.save(thumb, "JPEG")
                thumb.name = "thumbnail.jpg"
                thumb.seek(0)
                return thumb
    except Exception as e:
        print(f"Thumbnail error: {e}")
    return None

async def apply_watermark(input_path: str, output_path: str, settings: Dict) -> bool:
    """Apply watermark to file"""
    try:
        if not settings.get("watermark_text"):
            return False

        if input_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            with Image.open(input_path) as img:
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype(WATERMARK_FONT, settings["watermark_size"])
                except:
                    font = ImageFont.load_default()
                
                text = settings["watermark_text"]
                text_width, text_height = draw.textsize(text, font)
                width, height = img.size
                position = settings["watermark_position"]
                
                positions = {
                    "top-left": (10, 10),
                    "top-right": (width - text_width - 10, 10),
                    "bottom-left": (10, height - text_height - 10),
                    "bottom-right": (width - text_width - 10, height - text_height - 10),
                    "center": ((width - text_width) // 2, (height - text_height) // 2)
                }
                
                x, y = positions.get(position, positions["bottom-right"])
                overlay = Image.new('RGBA', img.size, (255,255,255,0))
                draw_overlay = ImageDraw.Draw(overlay)
                draw_overlay.text((x, y), text, font=font, 
                                fill=(255,255,255,int(255 * settings["watermark_opacity"]/100)))
                img = Image.alpha_composite(img.convert('RGBA'), overlay)
                img.save(output_path)
                return True
                
        elif input_path.lower().endswith((".mp4", ".mov", ".avi")):
            position_map = {
                "top-left": "10:10",
                "top-right": "main_w-text_w-10:10",
                "bottom-left": "10:main_h-text_h-10",
                "bottom-right": "main_w-text_w-10:main_h-text_h-10",
                "center": "(main_w-text_w)/2:(main_h-text_h)/2"
            }
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f"drawtext=text='{settings['watermark_text']}':"
                      f"fontfile={WATERMARK_FONT}:"
                      f"fontsize={settings['watermark_size']}:"
                      f"fontcolor=white@{settings['watermark_opacity']/100}:"
                      f"x={position_map[settings['watermark_position']]}",
                '-codec:a', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True)
            return True
    except Exception as e:
        print(f"Watermark error: {e}")
    return False

async def edit_metadata(input_path: str, output_path: str, settings: Dict) -> bool:
    """Edit file metadata"""
    try:
        if input_path.lower().endswith((".mp3", ".flac", ".wav", ".m4a")):
            cmd = ['ffmpeg', '-i', input_path]
            
            if settings.get("metadata_title"):
                cmd.extend(['-metadata', f"title={settings['metadata_title']}"])
            if settings.get("metadata_artist"):
                cmd.extend(['-metadata', f"artist={settings['metadata_artist']}"])
            if settings.get("metadata_album"):
                cmd.extend(['-metadata', f"album={settings['metadata_album']}"])
            
            cmd.extend(['-codec', 'copy', output_path])
            subprocess.run(cmd, check=True)
            return True
            
        elif input_path.lower().endswith((".mp4", ".mov", ".avi")):
            cmd = ['ffmpeg', '-i', input_path]
            
            if settings.get("metadata_title"):
                cmd.extend(['-metadata', f"title={settings['metadata_title']}"])
            
            cmd.extend(['-codec', 'copy', output_path])
            subprocess.run(cmd, check=True)
            return True
    except Exception as e:
        print(f"Metadata error: {e}")
    return False

async def get_metadata(file_path: str) -> Dict:
    """Extract file metadata"""
    metadata = {}
    try:
        parser = createParser(file_path)
        if not parser:
            return metadata
            
        with parser:
            extracted = extractMetadata(parser)
            if not extracted:
                return metadata
                
            for line in extracted.exportPlaintext():
                if ": " in line:
                    key, val = line.split(": ", 1)
                    metadata[key.lower()] = val.strip()
    except Exception as e:
        print(f"Metadata extraction error: {e}")
    return metadata

async def combine_files(file_paths: List[str], output_path: str, file_type: str) -> bool:
    """Combine multiple files into one"""
    try:
        if file_type == ".mp4":
            # Combine videos
            with open("file_list.txt", "w") as f:
                for file in file_paths:
                    f.write(f"file '{file}'\n")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', 'file_list.txt',
                '-c', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True)
            os.remove("file_list.txt")
            return True
            
        elif file_type == ".mp3":
            # Combine audio files
            cmd = ['ffmpeg']
            for file in file_paths:
                cmd.extend(['-i', file])
            cmd.extend(['-filter_complex', f'concat=n={len(file_paths)}:v=0:a=1', output_path])
            subprocess.run(cmd, check=True)
            return True
            
        elif file_type == ".pdf":
            # Combine PDFs (requires pdftk)
            cmd = ['pdftk']
            cmd.extend(file_paths)
            cmd.extend(['cat', 'output', output_path])
            subprocess.run(cmd, check=True)
            return True
            
    except Exception as e:
        print(f"Combine error: {e}")
    return False

# Command handlers
@Client.on_message(filters.command(["rename", "r"]) & filters.reply)
async def rename_file(client: Client, message: Message, db):
    user_id = message.from_user.id
    replied = message.reply_to_message
    settings = await get_user_settings(user_id, db)
    
    if not (replied.document or replied.video or replied.audio):
        await message.reply_text("Please reply to a file, video, or audio message to rename.")
        return
    
    new_name = " ".join(message.command[1:])
    if not new_name:
        await message.reply_text("Please provide a new name. Example: /rename NewFileName")
        return
    
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Apply prefix/suffix
    file_ext = os.path.splitext(replied.document.file_name if replied.document else replied.video.file_name)[1]
    new_name = await clean_filename(new_name)
    final_name = f"{settings.get('prefix', '')}{new_name}{settings.get('suffix', '')}{file_ext}"
    
    # Download file
    original_path = await client.download_media(replied, file_name=os.path.join(TEMP_DIR, f"original_{user_id}{file_ext}"))
    processed_path = os.path.join(TEMP_DIR, f"processed_{user_id}{file_ext}")
    
    try:
        # Process file (watermark + metadata)
        needs_processing = False
        os.rename(original_path, processed_path)
        
        # Apply watermark
        if settings.get("watermark_text"):
            watermark_applied = await apply_watermark(processed_path, processed_path, settings)
            needs_processing = needs_processing or watermark_applied
        
        # Apply metadata
        if any(settings.get(key) for key in ["metadata_title", "metadata_artist", "metadata_album"]):
            metadata_applied = await edit_metadata(processed_path, processed_path, settings)
            needs_processing = needs_processing or metadata_applied
        
        # If no processing, use original
        if not needs_processing:
            os.rename(processed_path, original_path)
            processed_path = original_path
        
        # Prepare thumbnail
        thumb = None
        if settings.get("thumbnail"):
            thumb = BytesIO(settings["thumbnail"])
            thumb.name = "thumbnail.jpg"
        elif settings.get("auto_thumbnail", False):
            thumb = await generate_thumbnail(processed_path)
        
        # Upload file
        caption = f"📁 Renamed by @{message.from_user.username}\n🔹 Original: `{replied.document.file_name if replied.document else replied.video.file_name}`"
        
        if replied.document:
            await client.send_document(
                chat_id=message.chat.id,
                document=processed_path,
                file_name=final_name,
                thumb=thumb,
                caption=caption,
                reply_to_message_id=replied.id
            )
        elif replied.video:
            await client.send_video(
                chat_id=message.chat.id,
                video=processed_path,
                file_name=final_name,
                thumb=thumb,
                caption=caption,
                reply_to_message_id=replied.id
            )
        elif replied.audio:
            await client.send_audio(
                chat_id=message.chat.id,
                audio=processed_path,
                file_name=final_name,
                thumb=thumb,
                caption=caption,
                reply_to_message_id=replied.id
            )
        
        # Update stats
        await update_user_settings(user_id, {
            "rename_count": settings.get("rename_count", 0) + 1,
            "last_activity": datetime.utcnow()
        }, db)
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        for path in [original_path, processed_path]:
            if path and os.path.exists(path):
                os.remove(path)

@Client.on_message(filters.command(["combine", "merge"]))
async def combine_files_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id, db)
    
    # Check if already in combine mode
    if settings.get("combine_mode"):
        await message.reply_text(
            "You're already in combine mode! Send files to combine.\n\n"
            "When done, use /finishcombine [output_name] to merge files.\n"
            "Or /cancelcombine to cancel."
        )
        return
    
    # Check if replying to a file
    if message.reply_to_message and (message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio):
        file_type = os.path.splitext(message.reply_to_message.document.file_name if message.reply_to_message.document else message.reply_to_message.video.file_name)[1]
        
        if file_type not in SUPPORTED_COMBINE_TYPES:
            await message.reply_text(
                f"File type {file_type} not supported for combining.\n"
                f"Supported types: {', '.join(SUPPORTED_COMBINE_TYPES)}"
            )
            return
        
        # Start combine mode with this file
        await update_user_settings(user_id, {
            "combine_mode": True,
            "combine_type": file_type,
            "combine_files": [message.reply_to_message],
            "last_activity": datetime.utcnow()
        }, db)
        
        await message.reply_text(
            f"🔀 Combine mode started for {file_type} files.\n"
            "Send me more files of the same type to combine.\n\n"
            "When done, use /finishcombine [output_name] to merge files.\n"
            "Or /cancelcombine to cancel."
        )
    else:
        # Show combine help
        await message.reply_text(
            "🔀 **Combine Files**\n\n"
            "To combine multiple files into one:\n"
            "1. Reply to a file with /combine\n"
            "2. Send more files of the same type\n"
            "3. Use /finishcombine [output_name] when done\n\n"
            f"Supported types: {', '.join(SUPPORTED_COMBINE_TYPES)}\n"
            f"Max combined size: {MAX_COMBINE_SIZE//(1024*1024)}MB"
        )

@Client.on_message(filters.command(["finishcombine", "mergefinish"]))
async def finish_combine_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id, db)
    
    if not settings.get("combine_mode"):
        await message.reply_text("You're not in combine mode. Use /combine to start.")
        return
    
    files = settings.get("combine_files", [])
    if len(files) < 2:
        await message.reply_text("You need at least 2 files to combine. Send more files or /cancelcombine.")
        return
    
    output_name = " ".join(message.command[1:])
    if not output_name:
        output_name = f"combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    file_type = settings.get("combine_type", "")
    output_name = await clean_filename(output_name) + file_type
    
    # Check total size
    total_size = sum(f.document.file_size if f.document else f.video.file_size for f in files)
    if total_size > MAX_COMBINE_SIZE:
        await message.reply_text(
            f"Total size ({total_size//(1024*1024)}MB) exceeds limit ({MAX_COMBINE_SIZE//(1024*1024)}MB).\n"
            "Please try with fewer/smaller files."
        )
        return
    
    # Download files
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_files = []
    
    try:
        processing_msg = await message.reply_text("⏳ Downloading and processing files...")
        
        for i, file_msg in enumerate(files):
            file_path = await client.download_media(
                file_msg,
                file_name=os.path.join(TEMP_DIR, f"combine_{user_id}_{i}{file_type}")
            )
            temp_files.append(file_path)
        
        # Combine files
        output_path = os.path.join(TEMP_DIR, output_name)
        await processing_msg.edit_text("🔄 Combining files...")
        
        if await combine_files(temp_files, output_path, file_type):
            # Get final size
            final_size = os.path.getsize(output_path)
            
            # Send combined file
            await processing_msg.edit_text("📤 Uploading combined file...")
            
            if file_type == ".mp4":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=output_path,
                    file_name=output_name,
                    caption=f"🔀 Combined {len(files)} files\n"
                          f"📦 Size: {final_size//1024}KB"
                )
            elif file_type == ".mp3":
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=output_path,
                    file_name=output_name,
                    caption=f"🔀 Combined {len(files)} files\n"
                          f"📦 Size: {final_size//1024}KB"
                )
            elif file_type == ".pdf":
                await client.send_document(
                    chat_id=message.chat.id,
                    document=output_path,
                    file_name=output_name,
                    caption=f"🔀 Combined {len(files)} files\n"
                          f"📦 Size: {final_size//1024}KB"
                )
            
            await processing_msg.delete()
        else:
            await message.reply_text("❌ Failed to combine files.")
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup and reset combine mode
        for file_path in temp_files + [output_path]:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        
        await update_user_settings(user_id, {
            "combine_mode": False,
            "combine_type": "",
            "combine_files": [],
            "last_activity": datetime.utcnow()
        }, db)

@Client.on_message(filters.command(["cancelcombine", "mergecancel"]))
async def cancel_combine_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id, db)
    
    if settings.get("combine_mode"):
        await update_user_settings(user_id, {
            "combine_mode": False,
            "combine_type": "",
            "combine_files": [],
            "last_activity": datetime.utcnow()
        }, db)
        await message.reply_text("✅ Combine mode canceled.")
    else:
        await message.reply_text("You're not in combine mode.")

@Client.on_message(filters.command(["setwatermark", "wm"]))
async def set_watermark_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    text = " ".join(message.command[1:])
    
    if not text:
        await message.reply_text(
            "Please provide watermark text. Example: /setwatermark MyWatermark\n\n"
            "Options:\n"
            "position=top-left|top-right|bottom-left|bottom-right|center\n"
            "opacity=0-100\n"
            "size=10-50\n\n"
            "Example: /setwatermark @MyChannel position=center opacity=70 size=30"
        )
        return
    
    # Parse options
    position = "bottom-right"
    opacity = 50
    size = 20
    
    if "position=" in text:
        parts = text.split()
        text_parts = []
        for part in parts:
            if part.startswith("position="):
                position = part.split("=")[1]
            elif part.startswith("opacity="):
                opacity = int(part.split("=")[1])
            elif part.startswith("size="):
                size = int(part.split("=")[1])
            else:
                text_parts.append(part)
        text = " ".join(text_parts)
    
    await update_user_settings(user_id, {
        "watermark_text": text,
        "watermark_position": position,
        "watermark_opacity": opacity,
        "watermark_size": size,
        "last_activity": datetime.utcnow()
    }, db)
    
    await message.reply_text(
        f"✅ Watermark settings updated:\n"
        f"Text: `{text}`\n"
        f"Position: `{position}`\n"
        f"Opacity: `{opacity}%`\n"
        f"Size: `{size}`"
    )

@Client.on_message(filters.command(["setmetadata", "meta"]))
async def set_metadata_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    args = " ".join(message.command[1:])
    
    if not args:
        await message.reply_text(
            "Please provide metadata to set. Example:\n"
            "/setmetadata title=\"My Title\" artist=\"My Artist\" album=\"My Album\""
        )
        return
    
    # Parse metadata
    metadata = {}
    for part in args.split('"'):
        if '=' in part:
            key, val = part.split('=', 1)
            metadata[key.strip()] = val.strip(' "')
    
    if not metadata:
        await message.reply_text("Invalid format. Use: /setmetadata title=\"My Title\" artist=\"Name\"")
        return
    
    update_data = {"last_activity": datetime.utcnow()}
    if "title" in metadata:
        update_data["metadata_title"] = metadata["title"]
    if "artist" in metadata:
        update_data["metadata_artist"] = metadata["artist"]
    if "album" in metadata:
        update_data["metadata_album"] = metadata["album"]
    
    await update_user_settings(user_id, update_data, db)
    await message.reply_text("✅ Metadata settings updated.")

@Client.on_message(filters.command(["showmetadata", "fileinfo"]))
async def show_metadata_handler(client: Client, message: Message, db):
    if not message.reply_to_message or not (message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio):
        await message.reply_text("Please reply to a file to show its metadata.")
        return
    
    # Download file
    file_path = await client.download_media(message.reply_to_message)
    metadata = await get_metadata(file_path)
    
    if not metadata:
        await message.reply_text("No metadata found or could not extract metadata.")
    else:
        metadata_text = "📋 **File Metadata**\n\n"
        for key, value in metadata.items():
            metadata_text += f"🔹 {key.capitalize()}: `{value}`\n"
        
        await message.reply_text(metadata_text)
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

@Client.on_message(filters.command(["settings", "myoptions"]))
async def settings_handler(client: Client, message: Message, db):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id, db)
    
    text = (
        "⚙️ **Your Settings**\n\n"
        f"🔹 Prefix: `{settings.get('prefix', 'None')}`\n"
        f"🔹 Suffix: `{settings.get('suffix', 'None')}`\n"
        f"🔹 Thumbnail: {'✅' if settings.get('thumbnail') else '❌'}\n"
        f"🔹 Auto-thumbnail: {'✅' if settings.get('auto_thumbnail', False) else '❌'}\n"
        f"🔹 Watermark: `{settings.get('watermark_text', 'None')}`\n"
        f"  - Position: `{settings.get('watermark_position', 'bottom-right')}`\n"
        f"  - Opacity: `{settings.get('watermark_opacity', 50)}%`\n"
        f"  - Size: `{settings.get('watermark_size', 20)}`\n"
        f"🔹 Metadata:\n"
        f"  - Title: `{settings.get('metadata_title', 'None')}`\n"
        f"  - Artist: `{settings.get('metadata_artist', 'None')}`\n"
        f"  - Album: `{settings.get('metadata_album', 'None')}`\n"
        f"🔹 Combine Mode: {'✅' if settings.get('combine_mode', False) else '❌'}\n"
        f"  - Files: {len(settings.get('combine_files', []))}\n"
        f"  - Type: `{settings.get('combine_type', 'None')}`\n"
        f"🔹 Total Renames: {settings.get('rename_count', 0)}"
    )
    
    await message.reply_text(text)
