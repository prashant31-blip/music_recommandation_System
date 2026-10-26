import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'music.db')

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = dict_factory
    try:
        yield conn
    finally:
        conn.close()

def check_db_connection():
    """Check database connectivity, file existence, and record counts."""
    info = {
        "connected": False,
        "db_path": os.path.abspath(DB_PATH),
        "db_exists": os.path.exists(DB_PATH),
        "db_size_bytes": 0,
        "db_size_mb": 0.0,
        "sqlite_version": sqlite3.sqlite_version,
        "tables": {},
        "status": "unhealthy",
        "error": None
    }
    
    if info["db_exists"]:
        info["db_size_bytes"] = os.path.getsize(DB_PATH)
        info["db_size_mb"] = round(info["db_size_bytes"] / (1024 * 1024), 2)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']
            
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                counts[table] = cursor.fetchone()['count']
            
            info["tables"] = counts
            cursor.execute("SELECT 1 as probe")
            probe = cursor.fetchone()
            if probe and probe['probe'] == 1:
                info["connected"] = True
                info["status"] = "healthy"
    except Exception as e:
        info["error"] = str(e)
        info["status"] = "error"
        
    return info

def init_db():
    """Create database tables and indexes if they do not exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tracks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id TEXT UNIQUE,
                track_name TEXT NOT NULL,
                artists TEXT NOT NULL,
                album_name TEXT,
                popularity INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                explicit INTEGER DEFAULT 0,
                danceability REAL DEFAULT 0.0,
                energy REAL DEFAULT 0.0,
                key INTEGER DEFAULT 0,
                loudness REAL DEFAULT 0.0,
                mode INTEGER DEFAULT 0,
                speechiness REAL DEFAULT 0.0,
                acousticness REAL DEFAULT 0.0,
                instrumentalness REAL DEFAULT 0.0,
                liveness REAL DEFAULT 0.0,
                valence REAL DEFAULT 0.0,
                tempo REAL DEFAULT 0.0,
                track_genre TEXT,
                preview_url TEXT DEFAULT NULL,
                cover_url TEXT DEFAULT NULL
            )
        ''')

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User interactions (likes, plays, skips)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                track_id TEXT NOT NULL,
                action TEXT NOT NULL, -- 'like', 'unlike', 'play', 'skip'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks (track_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Playlists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Playlist items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                track_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE,
                FOREIGN KEY (track_id) REFERENCES tracks (track_id)
            )
        ''')

        # Create indexes for fast search and joins
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_track_id ON tracks (track_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_name ON tracks (track_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_artists ON tracks (artists)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks (track_genre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_popularity ON tracks (popularity DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions (user_id, track_id)')

        # Insert default guest user if none exists
        cursor.execute('INSERT OR IGNORE INTO users (id, username) VALUES (1, "Guest Listener")')

        conn.commit()

if __name__ == '__main__':
    init_db()
    print(f"Database initialized at: {DB_PATH}")
