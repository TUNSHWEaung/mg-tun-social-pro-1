import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from moviepy.video.io.VideoFileClip import VideoFileClip
import whisper

app = Flask(__name__)

# ၁။ YouTube Video ဒေါင်းလုဒ်ဆွဲခြင်း
def download_youtube_video(url, output_path="video.mp4"):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print("Video downloaded successfully!")

# ၂။ ၃ မိနစ်စာ (၁၈၀ စက္ကန့်) စီ ဗီဒီယို ခွဲထုတ်ခြင်း
def split_video(input_file, clip_length=180):
    clip = VideoFileClip(input_file)
    duration = int(clip.duration)
    
    os.makedirs("clips", exist_ok=True)
    clip_files = []
    
    for i, start in enumerate(range(0, duration, clip_length)):
        end = min(start + clip_length, duration)
        output_filename = f"clips/part_{i+1}.mp4"
        
        subclip = clip.subclip(start, end)
        subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
        clip_files.append(output_filename)
        
    clip.close()
    return clip_files

# ၃။ AI ဖြင့် စာတန်းထိုးယူခြင်း (Whisper)
def generate_subtitles(video_path):
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    return result["text"]

# 🌐 n8n မှ HTTP Request လှမ်းခေါ်သည့်အခါ အလုပ်လုပ်မည့် API Endpoint
@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.get_json()
    yt_url = data.get('url')
    
    if not yt_url:
        return jsonify({"error": "YouTube URL is missing"}), 400
    
    try:
        # Step 1: Download
        download_youtube_video(yt_url, "input_video.mp4")
        
        # Step 2: Split into 3-minute clips
        clips = split_video("input_video.mp4", clip_length=180)
        
        # Step 3: (Optional) Subtitle & TikTok upload logic တွေ ဒီမှာ ဆက်ထည့်နိုင်ပါတယ်
        
        return jsonify({
            "status": "success",
            "message": f"Video successfully processed and split into {len(clips)} clips!",
            "clips": clips
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
