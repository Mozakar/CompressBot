import os
import tempfile
import subprocess
from datetime import datetime
from pyrogram import Client, filters
from config import API_ID, API_HASH, API_TOKEN, VIDEO_SCALE, VIDEO_FPS, VIDEO_CODEC, VIDEO_PIXEL_FORMAT, VIDEO_BITRATE, VIDEO_CRF, VIDEO_PRESET, VIDEO_AUDIO_CODEC, VIDEO_AUDIO_BITRATE, VIDEO_AUDIO_CHANNELS, VIDEO_AUDIO_SAMPLE_RATE, VIDEO_PROFILE

app = Client(
    "bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=API_TOKEN,
    workdir=tempfile.gettempdir()
)

def log(message):
    """Log messages to console with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_file_size(filepath):
    """Get file size in megabytes"""
    size = os.path.getsize(filepath)
    return round(size / (1024 * 1024), 2)

def download_progress(current, total, message_obj=None):
    """Display download progress"""
    downloaded_mb = round(current / (1024 * 1024), 2)
    total_mb = round(total / (1024 * 1024), 2)
    percentage = round((current / total) * 100, 1) if total > 0 else 0
    # Log every 5% or every 10 MB
    if percentage % 5 == 0 or current % (10 * 1024 * 1024) < (1024 * 1024):
        log(f"⬇️  Downloading: {downloaded_mb} MB / {total_mb} MB ({percentage}%)")

def download_media_safe(client, file_id, message, max_retries=3):
    """Download file with error handling and retry"""
    for attempt in range(1, max_retries + 1):
        try:
            log(f"Download attempt {attempt}/{max_retries}...")
            downloaded_file = client.download_media(
                file_id,
                progress=download_progress,
                progress_args=(message,)
            )
            return downloaded_file
        except Exception as e:
            log(f"❌ Download error (attempt {attempt}): {str(e)}")
            if attempt < max_retries:
                import time
                wait_time = attempt * 5  # 5, 10, 15 seconds
                log(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                raise

@app.on_message(filters.command("start"))
def start(client, message):
    log(f"Received /start command from user: {message.from_user.id}")
    message.reply_text("🎥 ربات کاهش حجم ویدیو\n\nویدیو خود را ارسال کنید تا حجم آن کاهش یابد.")

@app.on_message(filters.video | filters.animation)
def handle_video(client, message):
    log("=" * 60)
    log("Starting new video processing")
    log(f"User: {message.from_user.id} (@{message.from_user.username or 'N/A'})")
    log(f"Chat ID: {message.chat.id}")
    
    try:
        # Get file information
        video = message.video if message.video else message.animation
        file_id = video.file_id
        original_size = video.file_size / (1024 * 1024) if video.file_size else 0
        
        log(f"📥 Received video - File ID: {file_id}")
        log(f"📊 Original size: {round(original_size, 2)} MB")
        
        # Download file
        log("⬇️  Starting file download...")
        try:
            downloaded_file = download_media_safe(client, file_id, message)
            log(f"✅ Download completed: {downloaded_file}")
            log(f"📊 Downloaded file size: {get_file_size(downloaded_file)} MB")
        except Exception as download_error:
            log(f"❌ Download error after all attempts: {str(download_error)}")
            message.reply_text("❌ خطا در دانلود فایل. لطفا دوباره تلاش کنید.")
            raise
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_file = temp_file.name
        
        log(f"📁 Output file: {output_file}")
        
        # Build ffmpeg command
        cmd = (
            f'ffmpeg -i "{downloaded_file}" '
            f'-filter_complex "scale={VIDEO_SCALE}" '
            f'-r {VIDEO_FPS} '
            f'-c:v {VIDEO_CODEC} '
            f'-pix_fmt {VIDEO_PIXEL_FORMAT} '
            f'-b:v {VIDEO_BITRATE} '
            f'-crf {VIDEO_CRF} '
            f'-preset {VIDEO_PRESET} '
            f'-c:a {VIDEO_AUDIO_CODEC} '
            f'-b:a {VIDEO_AUDIO_BITRATE} '
            f'-ac {VIDEO_AUDIO_CHANNELS} '
            f'-ar {VIDEO_AUDIO_SAMPLE_RATE} '
            f'-profile:v {VIDEO_PROFILE} '
            f'-map_metadata -1 '
            f'"{output_file}"'
        )
        
        log("🎬 Starting video compression...")
        log(f"FFmpeg command: {cmd}")
        
        # Execute ffmpeg
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            log(f"❌ Compression error!")
            log(f"FFmpeg error: {process.stderr}")
            message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
            os.remove(downloaded_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            return
        
        log("✅ Compression completed")
        
        # Check output file size
        compressed_size = get_file_size(output_file)
        reduction = round(((original_size - compressed_size) / original_size) * 100, 2) if original_size > 0 else 0
        
        log(f"📊 Compressed file size: {compressed_size} MB")
        log(f"📉 Size reduction: {reduction}%")
        log(f"💾 Space saved: {round(original_size - compressed_size, 2)} MB")
        
        # Send compressed file
        log("📤 Starting to send compressed file...")
        message.reply_video(
            output_file,
            caption=f"✅ ویدیو فشرده شد!\n\n"
                   f"📊 حجم اصلی: {round(original_size, 2)} MB\n"
                   f"📊 حجم جدید: {compressed_size} MB\n"
                   f"📉 کاهش: {reduction}%"
        )
        log("✅ File sent successfully")
        
        # Clean up temporary files
        log("🧹 Cleaning up temporary files...")
        os.remove(downloaded_file)
        os.remove(output_file)
        log("✅ Temporary files cleaned up")
        
        log("=" * 60)
        log("Processing completed successfully\n")
        
    except Exception as e:
        log(f"❌ Unexpected error: {str(e)}")
        log(f"Error type: {type(e).__name__}")
        import traceback
        log(f"Error details:\n{traceback.format_exc()}")
        message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
        log("=" * 60)

@app.on_message(filters.document)
def handle_document_video(client, message):
    """Process document files that are videos (like mkv)"""
    if not message.document:
        return
    
    filename = message.document.file_name or ""
    video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    if not filename:
        return
    
    ext = os.path.splitext(filename.lower())[1]
    if ext not in video_extensions:
        return
    
    log("=" * 60)
    log("Starting video processing from document")
    log(f"User: {message.from_user.id} (@{message.from_user.username or 'N/A'})")
    log(f"Filename: {filename}")
    
    try:
        file_id = message.document.file_id
        original_size = message.document.file_size / (1024 * 1024) if message.document.file_size else 0
        
        log(f"📥 Received video - File ID: {file_id}")
        log(f"📊 Original size: {round(original_size, 2)} MB")
        
        # Download file
        log("⬇️  Starting file download...")
        try:
            downloaded_file = download_media_safe(client, file_id, message)
            log(f"✅ Download completed: {downloaded_file}")
            log(f"📊 Downloaded file size: {get_file_size(downloaded_file)} MB")
        except Exception as download_error:
            log(f"❌ Download error after all attempts: {str(download_error)}")
            message.reply_text("❌ خطا در دانلود فایل. لطفا دوباره تلاش کنید.")
            raise
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_file = temp_file.name
        
        log(f"📁 Output file: {output_file}")
        
        # Build ffmpeg command
        cmd = (
            f'ffmpeg -i "{downloaded_file}" '
            f'-filter_complex "scale={VIDEO_SCALE}" '
            f'-r {VIDEO_FPS} '
            f'-c:v {VIDEO_CODEC} '
            f'-pix_fmt {VIDEO_PIXEL_FORMAT} '
            f'-b:v {VIDEO_BITRATE} '
            f'-crf {VIDEO_CRF} '
            f'-preset {VIDEO_PRESET} '
            f'-c:a {VIDEO_AUDIO_CODEC} '
            f'-b:a {VIDEO_AUDIO_BITRATE} '
            f'-ac {VIDEO_AUDIO_CHANNELS} '
            f'-ar {VIDEO_AUDIO_SAMPLE_RATE} '
            f'-profile:v {VIDEO_PROFILE} '
            f'-map_metadata -1 '
            f'"{output_file}"'
        )
        
        log("🎬 Starting video compression...")
        log(f"FFmpeg command: {cmd}")
        
        # Execute ffmpeg
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            log(f"❌ Compression error!")
            log(f"FFmpeg error: {process.stderr}")
            message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
            os.remove(downloaded_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            return
        
        log("✅ Compression completed")
        
        # Check output file size
        compressed_size = get_file_size(output_file)
        reduction = round(((original_size - compressed_size) / original_size) * 100, 2) if original_size > 0 else 0
        
        log(f"📊 Compressed file size: {compressed_size} MB")
        log(f"📉 Size reduction: {reduction}%")
        log(f"💾 Space saved: {round(original_size - compressed_size, 2)} MB")
        
        # Send compressed file
        log("📤 Starting to send compressed file...")
        message.reply_video(
            output_file,
            caption=f"✅ ویدیو فشرده شد!\n\n"
                   f"📊 حجم اصلی: {round(original_size, 2)} MB\n"
                   f"📊 حجم جدید: {compressed_size} MB\n"
                   f"📉 کاهش: {reduction}%"
        )
        log("✅ File sent successfully")
        
        # Clean up temporary files
        log("🧹 Cleaning up temporary files...")
        os.remove(downloaded_file)
        os.remove(output_file)
        log("✅ Temporary files cleaned up")
        
        log("=" * 60)
        log("Processing completed successfully\n")
        
    except Exception as e:
        log(f"❌ Unexpected error: {str(e)}")
        log(f"Error type: {type(e).__name__}")
        import traceback
        log(f"Error details:\n{traceback.format_exc()}")
        message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
        log("=" * 60)

if __name__ == "__main__":
    log("🚀 Starting bot2...")
    log("✅ Bot is ready to receive videos")
    app.run()

