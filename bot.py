import os
import tempfile
import subprocess
import re
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pydub import AudioSegment
from config import *

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=API_TOKEN)

@app.on_message(filters.command("start"))
def start(client, message):
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Compress Audio 🎧", callback_data="compress_audio"),
                                    InlineKeyboardButton("Compress Video 🎥", callback_data="compress_video")]])
    message.reply_text("Choose what you want to compress:", reply_markup=markup)

@app.on_callback_query()
def callback(client, callback_query: CallbackQuery):
    callback_query.message.reply_text("Send me a file.")

@app.on_message(filters.voice | filters.audio)
def handle_audio(client, message):
    file = client.download_media(message.voice.file_id if message.chat.type == "voice" else message.audio.file_id)
    audio = AudioSegment.from_file(file).set_channels(AUDIO_CHANNELS).set_frame_rate(AUDIO_SAMPLE_RATE)
    with tempfile.NamedTemporaryFile(suffix=TEMP_FILE_SUFFIX_AUDIO, delete=False) as temp_file:
        temp_filename = temp_file.name
        audio.export(temp_filename, format=AUDIO_FORMAT, bitrate=AUDIO_BITRATE)
    message.reply_document(temp_filename)
    os.remove(file)
    os.remove(temp_filename)

def parse_time_to_seconds(time_str):
    """تبدیل زمان از فرمت HH:MM:SS.mmm به ثانیه"""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 0
    except:
        return 0

def run_ffmpeg_with_progress(cmd, message, client):
    """اجرای ffmpeg با نمایش پیشرفت"""
    # ارسال پیام اولیه
    status_msg = message.reply_text("⏳ در حال پردازش... 0%")
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    duration = None
    last_percentage = 0
    
    # خواندن خروجی stderr برای دریافت اطلاعات پیشرفت
    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            # استخراج مدت زمان ویدیو
            if duration is None:
                duration_match = re.search(r'Duration: (\d{2}:\d{2}:\d{2}\.\d{2})', line)
                if duration_match:
                    duration = parse_time_to_seconds(duration_match.group(1))
            
            # استخراج زمان فعلی
            time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
            if time_match and duration:
                current_time = parse_time_to_seconds(time_match.group(1))
                percentage = int((current_time / duration) * 100)
                
                # به‌روزرسانی فقط اگر درصد تغییر کرده باشد
                if percentage != last_percentage and percentage <= 100:
                    last_percentage = percentage
                    try:
                        progress_bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
                        status_msg.edit_text(f"⏳ در حال پردازش... {percentage}%\n{progress_bar}")
                    except:
                        pass
    
    process.wait()
    return process.returncode, status_msg

def is_video_file(filename):
    """بررسی اینکه آیا فایل یک فایل ویدیویی است"""
    video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    if filename:
        ext = os.path.splitext(filename.lower())[1]
        return ext in video_extensions
    return False

@app.on_message(filters.video | filters.animation)
def handle_media(client, message):
    print(message)
    file = client.download_media(message.video.file_id if message.video else message.animation.file_id)
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    print("temp_filename", temp_filename)
    # پردازش انیمیشن
    if message.animation:
        cmd = f'ffmpeg -i "{file}" "{temp_filename}"'
        returncode, status_msg = run_ffmpeg_with_progress(cmd, message, client)
        if returncode != 0:
            status_msg.edit_text("❌ خطا در پردازش فایل")
            os.remove(file)
            return
    
    print("step 2")
    # پردازش ویدیو با فشرده‌سازی
    cmd = f'ffmpeg -i "{file}" -filter_complex "scale={VIDEO_SCALE}" -r {VIDEO_FPS} -c:v {VIDEO_CODEC} -pix_fmt {VIDEO_PIXEL_FORMAT} -b:v {VIDEO_BITRATE} -crf {VIDEO_CRF} -preset {VIDEO_PRESET} -c:a {VIDEO_AUDIO_CODEC} -b:a {VIDEO_AUDIO_BITRATE} -ac {VIDEO_AUDIO_CHANNELS} -ar {VIDEO_AUDIO_SAMPLE_RATE} -profile:v {VIDEO_PROFILE} -map_metadata -1 "{temp_filename}"'
    returncode, status_msg = run_ffmpeg_with_progress(cmd, message, client)
    print("step 3")
    if returncode == 0:
        status_msg.edit_text("✅ پردازش کامل شد! در حال ارسال...")
        message.reply_video(temp_filename)
        status_msg.delete()
    else:
        status_msg.edit_text("❌ خطا در پردازش فایل")
    
    os.remove(file)
    os.remove(temp_filename)

@app.on_message(filters.document)
def handle_document(client, message):
    """پردازش فایل‌های document که ویدیو هستند (مثل mkv)"""
    if not message.document:
        return
    
    filename = message.document.file_name or ""
    
    # بررسی اینکه آیا فایل یک ویدیو است
    if not is_video_file(filename):
        return
    
    file = client.download_media(message.document.file_id)
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    # پردازش ویدیو با فشرده‌سازی
    cmd = f'ffmpeg -i "{file}" -filter_complex "scale={VIDEO_SCALE}" -r {VIDEO_FPS} -c:v {VIDEO_CODEC} -pix_fmt {VIDEO_PIXEL_FORMAT} -b:v {VIDEO_BITRATE} -crf {VIDEO_CRF} -preset {VIDEO_PRESET} -c:a {VIDEO_AUDIO_CODEC} -b:a {VIDEO_AUDIO_BITRATE} -ac {VIDEO_AUDIO_CHANNELS} -ar {VIDEO_AUDIO_SAMPLE_RATE} -profile:v {VIDEO_PROFILE} -map_metadata -1 "{temp_filename}"'
    returncode, status_msg = run_ffmpeg_with_progress(cmd, message, client)
    
    if returncode == 0:
        status_msg.edit_text("✅ پردازش کامل شد! در حال ارسال...")
        message.reply_video(temp_filename)
        status_msg.delete()
    else:
        status_msg.edit_text("❌ خطا در پردازش فایل")
    
    os.remove(file)
    os.remove(temp_filename)

app.run()
