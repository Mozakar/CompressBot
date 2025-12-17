import os
import tempfile
import subprocess
from datetime import datetime
from pyrogram import Client, filters
from config import API_ID, API_HASH, API_TOKEN, VIDEO_SCALE, VIDEO_FPS, VIDEO_CODEC, VIDEO_PIXEL_FORMAT, VIDEO_BITRATE, VIDEO_CRF, VIDEO_PRESET, VIDEO_AUDIO_CODEC, VIDEO_AUDIO_BITRATE, VIDEO_AUDIO_CHANNELS, VIDEO_AUDIO_SAMPLE_RATE, VIDEO_PROFILE

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=API_TOKEN)

def log(message):
    """لاگ کردن پیام‌ها در کنسول با زمان"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_file_size(filepath):
    """دریافت حجم فایل به مگابایت"""
    size = os.path.getsize(filepath)
    return round(size / (1024 * 1024), 2)

@app.on_message(filters.command("start"))
def start(client, message):
    log(f"دریافت دستور /start از کاربر: {message.from_user.id}")
    message.reply_text("🎥 ربات کاهش حجم ویدیو\n\nویدیو خود را ارسال کنید تا حجم آن کاهش یابد.")

@app.on_message(filters.video | filters.animation)
def handle_video(client, message):
    log("=" * 60)
    log("شروع پردازش ویدیو جدید")
    log(f"کاربر: {message.from_user.id} (@{message.from_user.username or 'N/A'})")
    log(f"Chat ID: {message.chat.id}")
    
    try:
        # دریافت اطلاعات فایل
        video = message.video if message.video else message.animation
        file_id = video.file_id
        original_size = video.file_size / (1024 * 1024) if video.file_size else 0
        
        log(f"📥 دریافت ویدیو - File ID: {file_id}")
        log(f"📊 حجم اصلی: {round(original_size, 2)} MB")
        
        # دانلود فایل
        log("⬇️  شروع دانلود فایل...")
        downloaded_file = client.download_media(file_id)
        log(f"✅ دانلود کامل شد: {downloaded_file}")
        log(f"📊 حجم فایل دانلود شده: {get_file_size(downloaded_file)} MB")
        
        # ایجاد فایل موقت برای خروجی
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_file = temp_file.name
        
        log(f"📁 فایل خروجی: {output_file}")
        
        # ساخت دستور ffmpeg
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
        
        log("🎬 شروع فشرده‌سازی ویدیو...")
        log(f"دستور ffmpeg: {cmd}")
        
        # اجرای ffmpeg
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            log(f"❌ خطا در فشرده‌سازی!")
            log(f"خطای ffmpeg: {process.stderr}")
            message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
            os.remove(downloaded_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            return
        
        log("✅ فشرده‌سازی کامل شد")
        
        # بررسی حجم فایل خروجی
        compressed_size = get_file_size(output_file)
        reduction = round(((original_size - compressed_size) / original_size) * 100, 2) if original_size > 0 else 0
        
        log(f"📊 حجم فایل فشرده شده: {compressed_size} MB")
        log(f"📉 کاهش حجم: {reduction}%")
        log(f"💾 صرفه‌جویی: {round(original_size - compressed_size, 2)} MB")
        
        # ارسال فایل فشرده شده
        log("📤 شروع ارسال فایل فشرده شده...")
        message.reply_video(
            output_file,
            caption=f"✅ ویدیو فشرده شد!\n\n"
                   f"📊 حجم اصلی: {round(original_size, 2)} MB\n"
                   f"📊 حجم جدید: {compressed_size} MB\n"
                   f"📉 کاهش: {reduction}%"
        )
        log("✅ فایل با موفقیت ارسال شد")
        
        # پاک کردن فایل‌های موقت
        log("🧹 پاک کردن فایل‌های موقت...")
        os.remove(downloaded_file)
        os.remove(output_file)
        log("✅ فایل‌های موقت پاک شدند")
        
        log("=" * 60)
        log("پردازش با موفقیت به پایان رسید\n")
        
    except Exception as e:
        log(f"❌ خطای غیرمنتظره: {str(e)}")
        log(f"نوع خطا: {type(e).__name__}")
        import traceback
        log(f"جزئیات خطا:\n{traceback.format_exc()}")
        message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
        log("=" * 60)

@app.on_message(filters.document)
def handle_document_video(client, message):
    """پردازش فایل‌های document که ویدیو هستند (مثل mkv)"""
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
    log("شروع پردازش ویدیو از document")
    log(f"کاربر: {message.from_user.id} (@{message.from_user.username or 'N/A'})")
    log(f"نام فایل: {filename}")
    
    try:
        file_id = message.document.file_id
        original_size = message.document.file_size / (1024 * 1024) if message.document.file_size else 0
        
        log(f"📥 دریافت ویدیو - File ID: {file_id}")
        log(f"📊 حجم اصلی: {round(original_size, 2)} MB")
        
        # دانلود فایل
        log("⬇️  شروع دانلود فایل...")
        downloaded_file = client.download_media(file_id)
        log(f"✅ دانلود کامل شد: {downloaded_file}")
        log(f"📊 حجم فایل دانلود شده: {get_file_size(downloaded_file)} MB")
        
        # ایجاد فایل موقت برای خروجی
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_file = temp_file.name
        
        log(f"📁 فایل خروجی: {output_file}")
        
        # ساخت دستور ffmpeg
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
        
        log("🎬 شروع فشرده‌سازی ویدیو...")
        log(f"دستور ffmpeg: {cmd}")
        
        # اجرای ffmpeg
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            log(f"❌ خطا در فشرده‌سازی!")
            log(f"خطای ffmpeg: {process.stderr}")
            message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
            os.remove(downloaded_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            return
        
        log("✅ فشرده‌سازی کامل شد")
        
        # بررسی حجم فایل خروجی
        compressed_size = get_file_size(output_file)
        reduction = round(((original_size - compressed_size) / original_size) * 100, 2) if original_size > 0 else 0
        
        log(f"📊 حجم فایل فشرده شده: {compressed_size} MB")
        log(f"📉 کاهش حجم: {reduction}%")
        log(f"💾 صرفه‌جویی: {round(original_size - compressed_size, 2)} MB")
        
        # ارسال فایل فشرده شده
        log("📤 شروع ارسال فایل فشرده شده...")
        message.reply_video(
            output_file,
            caption=f"✅ ویدیو فشرده شد!\n\n"
                   f"📊 حجم اصلی: {round(original_size, 2)} MB\n"
                   f"📊 حجم جدید: {compressed_size} MB\n"
                   f"📉 کاهش: {reduction}%"
        )
        log("✅ فایل با موفقیت ارسال شد")
        
        # پاک کردن فایل‌های موقت
        log("🧹 پاک کردن فایل‌های موقت...")
        os.remove(downloaded_file)
        os.remove(output_file)
        log("✅ فایل‌های موقت پاک شدند")
        
        log("=" * 60)
        log("پردازش با موفقیت به پایان رسید\n")
        
    except Exception as e:
        log(f"❌ خطای غیرمنتظره: {str(e)}")
        log(f"نوع خطا: {type(e).__name__}")
        import traceback
        log(f"جزئیات خطا:\n{traceback.format_exc()}")
        message.reply_text("❌ خطا در پردازش ویدیو. لطفا دوباره تلاش کنید.")
        log("=" * 60)

if __name__ == "__main__":
    log("🚀 راه‌اندازی ربات bot2...")
    log("✅ ربات آماده دریافت ویدیو است")
    app.run()

