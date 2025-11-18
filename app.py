from flask import Flask, render_template, request, flash, redirect, url_for
import requests
import base64
import os
from dotenv import load_dotenv
import random
from pymongo import MongoClient
from bson import ObjectId

# .env 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")


# .env에서 API 키 가져오기
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("CLIENT_ID / CLIENT_SECRET이 설정되지 않았습니다.")

SEED_GENRES = [
    "acoustic", "afrobeat", "alt-rock", "alternative",
    "ambient", "anime", "bluegrass", "blues", "bossanova",
    "brazil", "breakbeat", "british", "cantopop", "chill",
    "classical", "club", "comedy", "country", "dance",
    "dancehall", "death-metal", "deep-house", "detroit-techno",
    "disco", "disney", "drum-and-bass", "dub", "dubstep",
    "edm", "electro", "electronic", "emo", "folk",
    "french", "funk", "garage", "german", "gospel",
    "goth", "grindcore", "groove", "grunge", "hard-rock",
    "hardcore", "hardstyle", "heavy-metal", "hip-hop", "holidays",
    "honky-tonk", "house", "idm", "indian", "indie",
    "indie-pop", "industrial", "iranian", "j-dance", "j-idol",
    "j-pop", "j-rock", "jazz", "k-pop", "kids",
    "latin", "metal", "metalcore", "minimal-techno", "movies",
    "new-age", "new-release", "opera", "piano", "pop",
    "pop-film", "post-dubstep", "power-pop", "progressive-house",
    "psych-rock", "punk", "punk-rock", "r-n-b", "reggae",
    "reggaeton", "rock", "rock-n-roll", "salsa", "samba",
    "singer-songwriter", "ska", "sleep", "soul", "soundtracks",
    "spanish", "study", "swedish", "synth-pop", "tango",
    "techno", "trance", "trip-hop", "turkish", "work-out",
    "world-music",
]

# MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['music']
saved_tracks_col = db['like']

# Spotify Client credentials Flow로 Access Token 획득
def get_spotify_token() -> str:
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

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

def search_tracks_by_genre(genre: str, limit: int = 10):
    '''
    Spotify Search API를 통해 장르 검색 후 상위 검색 결과 리턴
    '''
    token = get_spotify_token()
    
    url = "https://api.spotify.com/v1/search"
    params = {
        "q": f'genre:"{genre}"',
        "market": "KR",
        "type": "track",
        "limit": 50
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }

    res = requests.get(url, headers=headers, params=params, timeout=5)
    res.raise_for_status()
    data = res.json()

    items = data.get("tracks", {}).get("items", [])
    all_tracks = []

    for t in items:
        track_name = t.get("name")
        artists = ", ".join([a.get("name", "") for a in t.get("artists", [])])
        album = t.get("album", {}).get("name")
        images = t.get("album", {}).get("images", [])
        image_url = images[0]["url"] if images else None
        external_url = t.get("external_urls", {}).get("spotify")

        all_tracks.append({
            "name": track_name,
            "artists": artists,
            "album": album,
            "image": image_url,
            "url": external_url,
        })

    if not all_tracks:
        return []

    if len(all_tracks) > limit:
        return random.sample(all_tracks, limit)
    else:
        return all_tracks

@app.route("/", methods=["GET"])
def index():
    '''
    장르 선택 페이지
    '''
    genres = SEED_GENRES
    return render_template("index.html", genres=genres)

@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    '''
    선택한 장르를 받아서 추천 곡 제시
    '''
    genre = request.form.get("genre")
    limit = request.form.get("limit", type=int, default=10)

    if not genre:
        flash("장르를 선택해주세요")
        return redirect(url_for("index"))
    
    try:
        tracks = search_tracks_by_genre(genre, limit=limit)
    except requests.HTTPError as e:
        print("Spotify API Error: ", e)
        flash("Spotify API 호출 중 오류 발생")
        return redirect(url_for("index"))
    except Exception as e:
        print("Unexpected Error: ", e)
        flash("오류 발생")
        return redirect(url_for("index"))
    
    if not tracks:
        flash("해당 장르에 알맞은 추천곡이 없습니다. 다른 장르를 선택해보세요")
        return redirect(url_for("index"))
    
    return render_template("results.html", genre=genre, tracks=tracks, limit=limit)

@app.route("/save", methods=["POST"])
def save_track():
    '''
    검색 결과에서 선택한 트랙을 DB에 저장
    '''

    name = request.form.get("name")
    artists = request.form.get("artists")
    album = request.form.get("album")
    image = request.form.get("image")
    url_ = request.form.get("url")

    if not name or not artists:
        flash("필수정보가 부족합니다.")
        return redirect(request.referrer or url_for("index"))
    
    doc = {
        "name": name,
        "artist": artists,
        "album": album,
        "image": image,
        "url": url_,
    }
    
    saved_tracks_col.insert_one(doc)
    flash(f"{name}이/가 트랙에 저장되었습니다.")
    return redirect(url_for("saved_tracks"))

@app.route("/saved", methods=["GET"])
def saved_tracks():
    '''
    MongoDB에 저장된 음악 목록 출력
    '''

    tracks = list(saved_tracks_col.find())

    return render_template("saved.html", tracks=tracks)

@app.route("/delete", methods=["POST"])
def delete_track():
    track_id = request.form.get("id")

    if track_id:
        saved_tracks_col.delete_one({"_id": ObjectId(track_id)})
        flash("음악이 삭제되었습니다.")

    return redirect(url_for("saved_tracks"))

if __name__ == "__main__":
    app.run(debug=True)