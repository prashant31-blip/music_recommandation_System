"""
VibeNest AI - Machine Learning Recommendation System Training Pipeline
Trains an unsupervised K-Means Clustering model and K-Nearest Neighbors (KNN)
recommender on the 40,000 track acoustic dataset.
"""

import os
import sys
import time
import pickle
import sqlite3
import numpy as np
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DB_PATH = os.path.join(DATA_DIR, 'music.db')
DATASET_CSV = os.path.join(DATA_DIR, 'dataset.csv')
MODEL_OUTPUT_PATH = os.path.join(MODELS_DIR, 'music_recommender_model.pkl')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.ml_model import (
    AcousticScaler,
    AcousticKMeans,
    AcousticKNNRecommender,
    FEATURE_COLS,
    FEATURE_WEIGHTS
)

def assign_vibe_names(kmeans_model, scaler):
    """Interpret cluster centers to generate human-readable mood tags."""
    centers_raw = scaler.inverse_transform(kmeans_model.cluster_centers_)
    profiles = {}
    for i, center in enumerate(centers_raw):
        dance, energy, valence, tempo, acoustic, instr, loud, speech, live = center

        if energy > 0.70 and dance > 0.65:
            name, tag = "⚡ High-Energy Dance & EDM", "Workout / Party"
        elif acoustic > 0.60 and energy < 0.40:
            name, tag = "🌙 Midnight Acoustic & Chill", "Relax / Unwind"
        elif instr > 0.40 and energy < 0.50:
            name, tag = "☕ Deep Focus & Ambient Lo-Fi", "Study / Work"
        elif valence > 0.60 and energy > 0.60:
            name, tag = "🎉 Feel-Good Pop Hits", "Sunny / Upbeat"
        elif energy > 0.75 and valence < 0.40:
            name, tag = "🎸 Intense Rock & Metal", "Adrenaline / Heavy"
        elif acoustic > 0.50 and valence > 0.50:
            name, tag = "🌻 Warm Indie & Folk", "Coffee / Acoustic"
        elif speech > 0.12 and dance > 0.60:
            name, tag = "🎤 Urban Hip-Hop & Rap", "Rhythm / Flow"
        elif instr > 0.55 and acoustic > 0.45:
            name, tag = "🎻 Classical & Cinematic Echoes", "Instrumental"
        elif dance > 0.70 and valence > 0.55:
            name, tag = "✨ Funk, Groove & R&B", "Dancefloor"
        else:
            name, tag = f"🎵 Eclectic Vibe Mix #{i+1}", "Curated"

        profiles[i] = {
            "name": name,
            "tag": tag,
            "center": {
                "danceability": round(float(dance), 2),
                "energy": round(float(energy), 2),
                "valence": round(float(valence), 2),
                "tempo": round(float(tempo), 1),
                "acousticness": round(float(acoustic), 2),
                "loudness": round(float(loud), 1)
            }
        }
    return profiles


def update_database_clusters(df_tracks, cluster_labels):
    """Persist cluster IDs to SQLite tracks table for fast querying."""
    if not os.path.exists(DB_PATH):
        return

    print("[*] Updating SQLite database with ML cluster labels...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(tracks)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'cluster_id' not in columns:
        cursor.execute("ALTER TABLE tracks ADD COLUMN cluster_id INTEGER DEFAULT 0")

    updates = [(int(cluster_labels[i]), str(df_tracks.iloc[i]['track_id'])) for i in range(len(df_tracks))]
    cursor.executemany("UPDATE tracks SET cluster_id = ? WHERE track_id = ?", updates)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_cluster ON tracks (cluster_id)")
    conn.commit()
    conn.close()
    print(f"[+] Updated {len(updates):,} tracks in SQLite with ML cluster labels.")


def train_recommender(n_clusters=10):
    start_time = time.time()
    print("=" * 65)
    print("   TRAINING VIBENEST AI MACHINE LEARNING RECOMMENDATION MODEL")
    print("=" * 65)

    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1. Load Data
    if os.path.exists(DB_PATH):
        print(f"[*] Loading dataset from SQLite: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        query = f"""
            SELECT id, track_id, track_name, artists, album_name, popularity,
                   duration_ms, explicit, {', '.join(FEATURE_COLS)},
                   track_genre, preview_url, cover_url
            FROM tracks
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
    elif os.path.exists(DATASET_CSV):
        print(f"[*] Loading dataset from CSV: {DATASET_CSV}")
        df = pd.read_csv(DATASET_CSV)
        df = df.dropna(subset=['track_id', 'track_name', 'artists'] + FEATURE_COLS)
        df = df.drop_duplicates(subset=['track_id'])
    else:
        raise FileNotFoundError("No dataset found.")

    n_tracks = len(df)
    print(f"[+] Dataset loaded: {n_tracks:,} tracks.")

    # 2. Extract feature matrix
    X_raw = df[FEATURE_COLS].values.astype(np.float32)

    # 3. Fit Scaler
    print("[*] Training Robust Scaler (5th-95th percentile with perceptual weighting)...")
    scaler = AcousticScaler(weights=FEATURE_WEIGHTS)
    X_weighted = scaler.fit_transform(X_raw)

    # 4. Row normalize vectors for cosine geometry
    norms = np.maximum(np.linalg.norm(X_weighted, axis=1, keepdims=True), 1e-7)
    X_norm = (X_weighted / norms).astype(np.float32)

    # 5. Fit K-Means
    print(f"[*] Training K-Means Cluster Model (k={n_clusters})...")
    kmeans = AcousticKMeans(n_clusters=n_clusters, max_iter=100, random_state=42)
    kmeans.fit(X_weighted)
    cluster_labels = kmeans.labels_
    print(f"[+] K-Means converged successfully (inertia: {kmeans.inertia_:,.1f})")

    # 6. Fit KNN Metric Model
    print("[*] Training K-Nearest Neighbors (KNN) metric index...")
    knn = AcousticKNNRecommender()
    knn.fit(X_norm, df['track_id'])
    print("[+] KNN model indexed.")

    # 7. Identify Clusters
    cluster_profiles = assign_vibe_names(kmeans, scaler)
    print("\n--- Identified Musical Vibe Clusters ---")
    for cid in range(n_clusters):
        count = int(np.sum(cluster_labels == cid))
        pct = (count / n_tracks) * 100
        cinfo = cluster_profiles[cid]
        print(f"  Cluster {cid:2d} | {cinfo['name']} ({cinfo['tag']}): {count:,} songs ({pct:.1f}%)")

    # 8. Update SQLite
    try:
        update_database_clusters(df, cluster_labels)
    except Exception as e:
        print(f"[!] SQLite cluster update skipped: {e}")

    # 9. Save Serialized Model
    print(f"\n[*] Serializing trained ML model to: {MODEL_OUTPUT_PATH}")
    model_bundle = {
        'model_name': 'VibeNest-Acoustic-KNN-KMeans',
        'version': '2.1.0',
        'trained_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'n_tracks': n_tracks,
        'feature_cols': FEATURE_COLS,
        'feature_weights': FEATURE_WEIGHTS,
        'scaler': scaler,
        'kmeans': kmeans,
        'knn': knn,
        'cluster_profiles': cluster_profiles,
        'cluster_labels': cluster_labels.astype(np.int32),
        'X_norm': X_norm,
        'track_ids': list(df['track_id']),
        'track_id_to_idx': {tid: i for i, tid in enumerate(df['track_id'])}
    }

    with open(MODEL_OUTPUT_PATH, 'wb') as f:
        pickle.dump(model_bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

    file_size_mb = os.path.getsize(MODEL_OUTPUT_PATH) / (1024 * 1024)
    elapsed = round(time.time() - start_time, 2)
    print(f"[+] Model training completed successfully in {elapsed}s ({file_size_mb:.2f} MB saved).")
    print("=" * 65)

    return model_bundle

if __name__ == '__main__':
    train_recommender(n_clusters=10)
