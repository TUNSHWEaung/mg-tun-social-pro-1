import os
from flask import Flask, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
from moviepy.video.io.VideoFileClip import VideoFileClip

app = Flask(__name__)

# ဗီဒီယိုဖိုင်တွေ သိမ်းမယ့် နေရာ
CLIPS_DIR = "clips"
os.makedirs(CLIPS_DIR, exist_ok=True)

# ၁။ ဗီဒီယိုဖိုင်တွေကို တိုက်ရိုက်လင့်ခ်နဲ့ ထုတ်ပေးမယ့် Route
@app.route('/clips/<filename>')
def get_clip(filename):
    return send_from_directory(CLIPS_DIR, filename)

# ၂။ ဗီဒီယို ခွဲထုတ်ပေးမည့် လုပ်ဆောင်ချက်
def split_video(input_file, clip_length=180):
    clip = VideoFileClip(input_file)
    duration = int(clip.duration)
    clip_files = []
    
    for i, start in enumerate(range(0, duration, clip_length)):
        end = min(start + clip_length, duration)
        output_filename = os.path.join(CLIPS_DIR, f"part_{i+1}.mp4")
        
        subclip = clip.subclip(start, end)
        subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
        clip_files.append(output_filename)
        
    clip.close()
    return clip_files

# ၃။ Main API Endpoint (n8n က လှမ်းခေါ်မည့်နေရာ)
@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.get_json()
    yt_url = data.get('url')
    
    if not yt_url:
        return jsonify({"error": "YouTube URL is missing"}), 400
    
    try:
        # YouTube မှ ဗီဒီယို ဒေါင်းခြင်း
        ydl_opts = {'format': 'best[ext=mp4]', 'outtmpl': 'input_video.mp4'}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
            
        # ၃ မိနစ်စာ အပိုင်းခွဲခြင်း
        clips = split_video('input_video.mp4', clip_length=180)
        
        # Render ရဲ့ Public URL ကို ယူခြင်း
        base_url = request.host_url.rstrip('/')
        clip_urls = [f"{base_url}/clips/{os.path.basename(c)}" for c in clips]
        
        return jsonify({
            "status": "success",
            "clip_urls": clip_urls  # n8n ဆီသို့ .mp4 လင့်ခ်များ ပို့ပေးမည်
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
