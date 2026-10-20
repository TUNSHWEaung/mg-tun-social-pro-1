import os
import io
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Google Drive API ရဲ့ Scope (ဖိုင်များကို ဖတ်ရှုရန်)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Buffer API သတင်းအချက်အလက်များ
BUFFER_API_KEY = 'YOUR_BUFFER_API_KEY'
BUFFER_CHANNEL_ID = 'YOUR_BUFFER_CHANNEL_ID' # TikTok ချိတ်ဆက်ထားသော Buffer Channel ID

def get_drive_service():
    """Google Drive API Authentication ပြုလုပ်ခြင်း"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def download_videos_from_folder(folder_id):
    """Google Drive သတ်မှတ်ထားသော Folder ထဲမှ ဗီဒီယိုများကို ဒေါင်းလုပ်ဆွဲခြင်း"""
    service = get_drive_service()
    
    # ဖိုင်တွဲထဲရှိ ဗီဒီယိုဖိုင်များကို ရှာဖွေရန် Query
    query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false"
    results = service.files().list(
        q=query, pageSize=10, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print("ဗီဒီယိုဖိုင်များ မတွေ့ရှိပါ။")
        return []

    downloaded_files = []
    os.makedirs('downloads', exist_ok=True)

    for item in items:
        file_id = item['id']
        file_name = item['name']
        file_path = os.path.join('downloads', file_name)
        
        print(f"ဒေါင်းလုပ်ဆွဲနေသည်: {file_name}...")
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
            
        downloaded_files.append((file_path, file_name))
        print(f"ပြီးဆုံးပါပြီ: {file_path}")

    return downloaded_files

def post_to_buffer(video_url, caption):
    """Buffer API ကိုသုံး၍ ပို့စ်တင်ခြင်း (TikTok အတွက်)"""
    url = "https://api.buffer.com"
    
    # Buffer GraphQL mutation ဖြင့် ဗီဒီယိုပို့စ်တင်ခြင်း
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        __typename
        ... on MutationSuccess {
          success
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    
    payload = {
        "query": query,
        "variables": {
            "input": {
                "channelId": BUFFER_CHANNEL_ID,
                "text": caption,
                "assets": {
                    "video": {
                        "url": video_url
                    }
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BUFFER_API_KEY}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

if __name__ == '__main__':
    # ၁။ သင့်ရဲ့ Google Drive Folder ID ကို ထည့်ပါ
    FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'
    
    # ၂။ ဗီဒီယိုများကို ဒေါင်းလုပ်ဆွဲမည်
    videos = download_videos_from_folder(FOLDER_ID)
    
    # ၃။ Buffer သို့ တင်ရန် (Buffer က Public URL ကိုသာ လက်ခံသောကြောင့် 
    # ဗီဒီယိုဖိုင်များကို Public Cloud တွင် တင်ပြီးသား URL ကို အသုံးပြုရပါမည်)
    for path, name in videos:
        print(f"Buffer သို့ ပို့ဆောင်ရန် စီစဉ်နေသည်: {name}")
        # ဥပမာ - Public URL တစ်ခုရှိပါက အောက်ပါအတိုင်း ချိတ်ဆက်နိုင်ပါသည်
        # response = post_to_buffer("https://your-public-server.com/downloads/" + name, f"Auto upload: {name}")
        # print(response)
