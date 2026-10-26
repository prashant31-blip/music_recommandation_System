import os
import sys
import sqlite3
import pandas as pd

try:
    from .database import DB_PATH, init_db
except ImportError:
    try:
        from backend.database import DB_PATH, init_db
    except ImportError:
        from database import DB_PATH, init_db

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'dataset.csv')

def seed_database(limit_tracks=40000):
    """
    Ingest tracks from dataset.csv into SQLite.
    Deduplicates song-artist pairs while retaining highest popularity release.
    """
    init_db()

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset CSV not found at {DATASET_PATH}")

    print(f"Reading dataset from {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)

    # Basic cleaning
    df = df.dropna(subset=['track_id', 'track_name', 'artists'])
    df['clean_title'] = df['track_name'].astype('string').str.lower().str.strip()
    df['clean_artist'] = df['artists'].astype('string').str.lower().str.strip()

    # Sort so most popular versions come first, then deduplicate
    df = df.sort_values(by='popularity', ascending=False)
    df = df.drop_duplicates(subset=['clean_title', 'clean_artist'])
    conn = sqlite3.connect(DB_PATH)
    preserved_ids = {
        row[0]
        for row in conn.execute("SELECT DISTINCT track_id FROM interactions")
    }
    conn.close()

    # Cap while retaining every genre and ranking tracks by popularity within
    # each genre. A global head() would make the recommender biased toward
    # popular genres and eliminate useful cold-start choices.
    if limit_tracks and len(df) > limit_tracks:
        print(f"Limiting to {limit_tracks} tracks with genre-balanced coverage...")
        genre_count = df['track_genre'].nunique()
        base_count = max(1, limit_tracks // genre_count)
        selected = df.groupby('track_genre', group_keys=False).head(base_count)

        if len(selected) < limit_tracks:
            remaining = df.loc[~df.index.isin(selected.index)]
            selected = pd.concat([selected, remaining.head(limit_tracks - len(selected))])

        preserved = df[df['track_id'].astype(str).isin(preserved_ids)]
        df = pd.concat([selected, preserved]).drop_duplicates('track_id')
        df = df.head(max(limit_tracks, len(preserved)))

    print(f"Preparing {len(df)} tracks for database insertion...")

    records = []
    for _, row in df.iterrows():
        records.append((
            str(row['track_id']),
            str(row['track_name']),
            str(row['artists']),
            str(row.get('album_name', '')),
            int(row.get('popularity', 0)),
            int(row.get('duration_ms', 0)),
            int(1 if row.get('explicit', False) else 0),
            float(row.get('danceability', 0.0)),
            float(row.get('energy', 0.0)),
            int(row.get('key', 0)),
            float(row.get('loudness', 0.0)),
            int(row.get('mode', 0)),
            float(row.get('speechiness', 0.0)),
            float(row.get('acousticness', 0.0)),
            float(row.get('instrumentalness', 0.0)),
            float(row.get('liveness', 0.0)),
            float(row.get('valence', 0.0)),
            float(row.get('tempo', 0.0)),
            str(row.get('track_genre', 'general')),
            None, # preview_url (fetched on demand / cached)
            None  # cover_url (fetched on demand / cached)
        ))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Inserting records into SQLite...")
    cursor.execute("DELETE FROM tracks") # Fresh seed
    cursor.executemany('''
        INSERT OR REPLACE INTO tracks (
            track_id, track_name, artists, album_name, popularity,
            duration_ms, explicit, danceability, energy, key, loudness,
            mode, speechiness, acousticness, instrumentalness, liveness,
            valence, tempo, track_genre, preview_url, cover_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]
    conn.close()

    print(f"Successfully seeded {total} tracks into SQLite database!")

if __name__ == '__main__':
    seed_database(limit_tracks=40000)
