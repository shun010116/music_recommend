from flask import Flask
import requests
import base64
import os
from dotenv import load_dotenv

app = Flask(__name__)

# .env 로드
load_dotenv()

# .env에서 API 키 가져오기
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Spotify Client credentials Flow로 Access Token 획득
if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("CLIENT_ID / CLIENT_SECRET이 설정되지 않았습니다.")

def get_spotify_token() -> str:
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    print(b64_auth_str)

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials"
    }

    res = requests.post(url, headers=headers, data=data, timeout=5)
    res.raise_for_status()
    data = res.json()
    return data["access_token"]

