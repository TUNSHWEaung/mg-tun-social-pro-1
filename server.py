
import os
import uuid
import shutil
from pathlib import Path
from urllib.parse import urlparse

import gdown
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from moviepy.video.io.VideoFileClip import VideoFileClip

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

BASE_DIR = Path(__file__).resolve().parent
CLIPS_DIR = BASE_DIR / "clips"
TEMP_DIR = BASE_DIR / "temp"
CLIPS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

MAX_VIDEO_MB = 500


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "MG TUN Video Splitter",
        "clip_length_seconds": 180
    })


@app.route("/clips/<job_id>/<filename>")
def get_clip(job_id, filename):
    # ဖိုင်အမည်ဖြင့် အခြားဖိုင်များကို ဝင်မဖတ်နိုင်အောင် စစ်ဆေးခြင်း
    if not job_id.isalnum():
        return jsonify({"error": "Invalid job ID"}), 400

    if Path(filename).name != filename:
        return jsonify({"error": "Invalid filename"}), 400

    folder = CLIPS_DIR / job_id

    if not folder.is_dir():
        return jsonify({"error": "Video not found"}), 404

    return send_from_directory(folder, filename, as_attachment=False)


def download_authorized_drive_video(url, output_file):
    """Public Google Drive share link မှ ဗီဒီယိုရယူခြင်း။"""

    parsed = urlparse(url)

    if parsed.scheme != "https" or parsed.hostname not in (
        "drive.google.com",
        "docs.google.com"
    ):
        raise ValueError(
            "HTTPS Google Drive share link ကိုသာ အသုံးပြုပါ။"
        )

    result = gdown.download(
        url=url,
        output=str(output_file),
        quiet=False,
        fuzzy=True
    )

    if not result or not output_file.is_file():
        raise ValueError(
            "ဗီဒီယိုကို ရယူမရပါ။ Google Drive sharing ကို "
            "'Anyone with the link' ဖြင့် ခွင့်ပြုထားကြောင်း စစ်ပါ။"
        )

    size_mb = output_file.stat().st_size / (1024 * 1024)

    if size_mb > MAX_VIDEO_MB:
        output_file.unlink(missing_ok=True)
        raise ValueError(
            f"ဗီဒီယိုအရွယ်အစား {MAX_VIDEO_MB} MB ထက်ကျော်နေပါတယ်။"
        )

    if size_mb < 0.01:
        raise ValueError("ရရှိလာသောဖိုင်သည် ဗီဒီယိုဖိုင် မဟုတ်နိုင်ပါ။")


def split_video(input_file, output_folder, clip_length=180):
    """MoviePy 1.x နှင့် 2.x နှစ်မျိုးလုံးအတွက် ၃ မိနစ်စီခွဲခြင်း။"""

    clip_files = []
    video = None

    try:
        video = VideoFileClip(str(input_file))
        duration = video.duration

        if not duration or duration <= 0:
            raise ValueError("ဗီဒီယိုကြာချိန်ကို ဖတ်မရပါ။")

        total_parts = int((duration + clip_length - 1) // clip_length)

        for i in range(total_parts):
            start = i * clip_length
            end = min(start + clip_length, duration)

            output_file = output_folder / f"part_{i + 1}.mp4"

            # MoviePy 2.x မှာ subclipped၊ 1.x မှာ subclip
            if hasattr(video, "subclipped"):
                part = video.subclipped(start, end)
            else:
                part = video.subclip(start, end)

            try:
                part.write_videofile(
                    str(output_file),
                    codec="libx264",
                    audio_codec="aac",
                    logger=None,
                    threads=2
                )
            finally:
                part.close()

            clip_files.append(output_file)

        return clip_files

    finally:
        if video is not None:
            video.close()


@app.route("/process-video", methods=["POST"])
def process_video():
    data = request.get_json(silent=True) or {}
    video_url = data.get("url", "").strip()

    if not video_url:
        return jsonify({
            "status": "error",
            "message": "Google Drive video URL is missing"
        }), 400

    job_id = uuid.uuid4().hex
    work_folder = TEMP_DIR / job_id
    output_folder = CLIPS_DIR / job_id

    work_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    input_file = work_folder / "input_video"

    try:
        download_authorized_drive_video(video_url, input_file)

        clip_files = split_video(
            input_file,
            output_folder,
            clip_length=180
        )

        base_url = request.url_root.rstrip("/")

        clip_urls = [
            f"{base_url}/clips/{job_id}/{file.name}"
            for file in clip_files
        ]

        return jsonify({
            "status": "success",
            "job_id": job_id,
            "total_parts": len(clip_urls),
            "clip_length_seconds": 180,
            "clip_urls": clip_urls,
            "parts": [
                {
                    "part_number": i + 1,
                    "caption": f"အပိုင်း {i + 1}",
                    "video_url": clip_url
                }
                for i, clip_url in enumerate(clip_urls)
            ]
        }), 200

    except Exception as e:
        app.logger.exception("Video processing failed")

        shutil.rmtree(output_folder, ignore_errors=True)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        shutil.rmtree(work_folder, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
