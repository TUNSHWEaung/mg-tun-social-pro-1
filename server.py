from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.get_json()
    yt_url = data.get('url')
    
    # ဒီနေရာမှာ YouTube Download၊ ၃ မိနစ်စာ ခွဲထုတ်ခြင်း၊ စာတန်းထိုးထည့်ခြင်း စတဲ့ Python Code များကို Run ခိုင်းပါမယ်
    print(f"Processing URL: {yt_url}")
    
    # Video Processing အလုပ်များပြီးပါက
    return jsonify({
        "status": "success",
        "message": "Video processed and split successfully!"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
