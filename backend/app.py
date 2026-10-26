import os
import sys

# Ensure backend directory and project root are in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

try:
    from .database import init_db, get_db, check_db_connection, DB_PATH
    from .recommender import recommender
    from .audio_fetcher import fetch_and_cache_preview
    from .seed_data import seed_database
except ImportError:
    try:
        from backend.database import init_db, get_db, check_db_connection, DB_PATH
        from backend.recommender import recommender
        from backend.audio_fetcher import fetch_and_cache_preview
        from backend.seed_data import seed_database
    except ImportError:
        from database import init_db, get_db, check_db_connection, DB_PATH
        from recommender import recommender
        from audio_fetcher import fetch_and_cache_preview
        from seed_data import seed_database

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

# Ensure database is initialized
init_db()
db_health = check_db_connection()
if db_health.get("tables", {}).get("tracks", 0) == 0:
    print("[!] Tracks table is empty. Running automated seed...")
    try:
        seed_database(limit_tracks=40000)
        recommender.load_engine()
    except Exception as e:
        print(f"[!] Auto-seed error: {e}")

# --- Static Frontend Serving ---
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# --- API Routes ---

@app.route('/api/health', methods=['GET'])
def health():
    db_status = check_db_connection()
    return jsonify({
        "status": "healthy" if db_status.get("connected") else "degraded",
        "tracks_indexed": len(recommender.df_tracks) if recommender.df_tracks is not None else 0,
        "ml_model_trained": recommender.is_ml_trained,
        "clusters_count": len(recommender.cluster_profiles),
        "database": db_status
    })

@app.route('/api/db-check', methods=['GET'])
def db_check():
    return jsonify(check_db_connection())

@app.route('/api/clusters', methods=['GET'])
def get_clusters():
    return jsonify({
        "clusters": recommender.cluster_profiles,
        "count": len(recommender.cluster_profiles)
    })

@app.route('/api/clusters/<int:cluster_id>/tracks', methods=['GET'])
def get_cluster_tracks(cluster_id):
    limit = request.args.get('limit', default=12, type=int)
    tracks = recommender.get_cluster_tracks(cluster_id=cluster_id, limit=limit)
    return jsonify({
        "cluster_id": cluster_id,
        "cluster_info": recommender.cluster_profiles.get(cluster_id, {}),
        "tracks": tracks
    })

@app.route('/api/genres', methods=['GET'])
def get_genres():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track_genre FROM tracks WHERE track_genre IS NOT NULL ORDER BY track_genre ASC")
        genres = [r['track_genre'] for r in cursor.fetchall()]
    return jsonify({"genres": genres})

@app.route('/api/tracks/popular', methods=['GET'])
def get_popular():
    limit = request.args.get('limit', default=12, type=int)
    tracks = recommender.get_trending_tracks(limit=limit)
    return jsonify({"tracks": tracks})

@app.route('/api/tracks/search', methods=['GET'])
def search_tracks():
    query = request.args.get('q', default='', type=str).strip().lower()
    genre = request.args.get('genre', default='', type=str).strip().lower()
    limit = request.args.get('limit', default=20, type=int)

    sql = "SELECT * FROM tracks WHERE 1=1"
    params = []

    if query:
        sql += " AND (LOWER(track_name) LIKE ? OR LOWER(artists) LIKE ? OR LOWER(album_name) LIKE ?)"
        wildcard = f"%{query}%"
        params.extend([wildcard, wildcard, wildcard])

    if genre:
        sql += " AND LOWER(track_genre) = ?"
        params.append(genre)

    sql += " ORDER BY popularity DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()

    for r in results:
        if not r.get('cover_url'):
            r['cover_url'] = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80"

    return jsonify({"tracks": results, "count": len(results)})

@app.after_request
def add_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/api/tracks/<track_id>', methods=['GET'])
def get_track(track_id):
    track = recommender.get_track_by_id(track_id)
    if not track:
        return jsonify({"error": "Track not found"}), 404
    return jsonify({"track": track})

@app.route('/api/tracks/<track_id>/preview', methods=['GET'])
def get_preview(track_id):
    track = recommender.get_track_by_id(track_id)
    if not track:
        return jsonify({"error": "Track not found"}), 404
    
    media = fetch_and_cache_preview(track_id, track['track_name'], track['artists'], genre=track.get('track_genre'))
    return jsonify(media)

@app.route('/api/recommend/similar/<track_id>', methods=['GET'])
def recommend_similar(track_id):
    limit = request.args.get('limit', default=12, type=int)
    similar = recommender.get_similar_tracks(track_id, limit=limit)
    seed = recommender.get_track_by_id(track_id)
    return jsonify({
        "seed_track": seed,
        "recommendations": similar
    })

@app.route('/api/recommend/mood', methods=['POST'])
def recommend_mood():
    data = request.get_json() or {}
    valence = data.get('valence', 0.5)
    energy = data.get('energy', 0.5)
    danceability = data.get('danceability', 0.5)
    acousticness = data.get('acousticness', 0.5)
    tempo_bpm = data.get('tempo_bpm', 120)
    limit = data.get('limit', 12)

    results = recommender.recommend_by_mood(
        valence=valence,
        energy=energy,
        danceability=danceability,
        acousticness=acousticness,
        tempo_bpm=tempo_bpm,
        limit=limit
    )
    return jsonify({"recommendations": results})

@app.route('/api/recommend/user', methods=['GET'])
def recommend_user():
    user_id = request.args.get('user_id', default=1, type=int)
    limit = request.args.get('limit', default=12, type=int)
    results = recommender.recommend_for_user(user_id=user_id, limit=limit)
    return jsonify({"recommendations": results})

@app.route('/api/interactions', methods=['POST'])
def log_interaction():
    data = request.get_json() or {}
    user_id = data.get('user_id', 1)
    track_id = data.get('track_id')
    action = data.get('action') # 'like', 'unlike', 'play', 'skip'

    if not track_id or not action:
        return jsonify({"error": "Missing track_id or action"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if action == 'unlike':
            cursor.execute("DELETE FROM interactions WHERE user_id = ? AND track_id = ? AND action = 'like'",
                           (user_id, track_id))
        else:
            cursor.execute("INSERT INTO interactions (user_id, track_id, action) VALUES (?, ?, ?)",
                           (user_id, track_id, action))
        conn.commit()

    return jsonify({"success": True, "action": action, "track_id": track_id})

@app.route('/api/user/likes', methods=['GET'])
def get_user_likes():
    user_id = request.args.get('user_id', default=1, type=int)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.* FROM tracks t
            JOIN interactions i ON t.track_id = i.track_id
            WHERE i.user_id = ? AND i.action = 'like'
            GROUP BY t.track_id
            ORDER BY i.created_at DESC
        """, (user_id,))
        likes = cursor.fetchall()

    for r in likes:
        if not r.get('cover_url'):
            r['cover_url'] = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80"

    return jsonify({"likes": likes, "count": len(likes)})

@app.route('/api/user/taste', methods=['GET'])
def get_user_taste():
    user_id = request.args.get('user_id', default=1, type=int)
    profile = recommender.get_user_taste_analytics(user_id)
    return jsonify(profile)

@app.route('/api/playlists', methods=['GET', 'POST'])
def handle_playlists():
    if request.method == 'GET':
        user_id = request.args.get('user_id', default=1, type=int)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, COUNT(pt.id) as track_count
                FROM playlists p
                LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                WHERE p.user_id = ?
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (user_id,))
            playlists = cursor.fetchall()
        return jsonify({"playlists": playlists})

    elif request.method == 'POST':
        data = request.get_json() or {}
        user_id = data.get('user_id', 1)
        name = data.get('name', 'My New Playlist').strip()
        description = data.get('description', '')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO playlists (user_id, name, description) VALUES (?, ?, ?)",
                           (user_id, name, description))
            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({"id": new_id, "name": name, "description": description}), 201

    return jsonify({"error": "Unsupported method"}), 405

@app.route('/api/playlists/<int:playlist_id>/tracks', methods=['GET', 'POST'])
def handle_playlist_tracks(playlist_id):
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            data = request.get_json() or {}
            track_id = data.get('track_id')
            if not track_id:
                return jsonify({"error": "track_id required"}), 400
            cursor.execute("INSERT INTO playlist_tracks (playlist_id, track_id) VALUES (?, ?)", (playlist_id, track_id))
            conn.commit()
            return jsonify({"success": True}), 201

        elif request.method == 'GET':
            cursor.execute("""
                SELECT t.* FROM tracks t
                JOIN playlist_tracks pt ON t.track_id = pt.track_id
                WHERE pt.playlist_id = ?
                ORDER BY pt.added_at DESC
            """, (playlist_id,))
            tracks = cursor.fetchall()
            return jsonify({"tracks": tracks, "count": len(tracks)})

    return jsonify({"error": "Unsupported method"}), 405

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Music Recommendation System server on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)
