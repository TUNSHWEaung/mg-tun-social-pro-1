
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "service": "MG TUN Video API"
    })

@app.post("/process-video")
def process_video():
    data = request.get_json(silent=True) or {}
    yt_url = data.get("url")

    if not isinstance(yt_url, str) or not yt_url.strip():
        return jsonify({
            "status": "error",
            "message": "url is required"
        }), 400

    if not yt_url.startswith(("https://", "http://")):
        return jsonify({
            "status": "error",
            "message": "Invalid URL"
        }), 400

    print(f"Received URL: {yt_url}")

    # TODO: Add actual video-processing logic here.
    return jsonify({
        "status": "accepted",
        "message": "URL received; video processing is not implemented yet.",
        "url": yt_url
    }), 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
