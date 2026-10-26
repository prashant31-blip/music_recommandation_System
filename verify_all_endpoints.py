import urllib.request
import json

endpoints = [
    ("Trending / Popular", "http://127.0.0.1:5000/api/tracks/popular?limit=12", "tracks"),
    ("User Recommendations", "http://127.0.0.1:5000/api/recommend/user?user_id=1&limit=8", "recommendations"),
    ("Track Radar (Similar to Mere Yaaraa)", "http://127.0.0.1:5000/api/recommend/similar/0tpwqQhdfJXRcUDSNRjb9O?limit=12", "recommendations"),
]

for name, url, key in endpoints:
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    items = data.get(key, [])
    print(f"[OK] {name}: {len(items)} tracks returned.")
    if items:
        first = items[0]
        print(f"     -> First: '{first['track_name']}' by '{first['artists']}' | Cover: {first.get('cover_url', '')[:35]}... | Score: {first.get('similarity_score') or first.get('match_score') or 'N/A'}")

# Mood recommendation test
mood_payload = json.dumps({'valence': 0.5, 'energy': 0.5, 'danceability': 0.5, 'acousticness': 0.5, 'tempo_bpm': 120, 'limit': 12}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/api/recommend/mood', data=mood_payload, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    items = data.get('recommendations', [])
    print(f"[OK] Mood & Vibe Lab: {len(items)} tracks returned.")
    if items:
        first = items[0]
        print(f"     -> First: '{first['track_name']}' by '{first['artists']}' | Match: {first.get('match_score')}%")
