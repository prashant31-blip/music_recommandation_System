import os
import sys
import pickle
import sqlite3
import numpy as np
import pandas as pd

# Add project root to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from .database import DB_PATH
except ImportError:
    try:
        from backend.database import DB_PATH
    except ImportError:
        from database import DB_PATH

try:
    from train_model import (
        AcousticScaler,
        AcousticKMeans,
        AcousticKNNRecommender,
        train_recommender,
        MODEL_OUTPUT_PATH,
        FEATURE_COLS,
        FEATURE_WEIGHTS
    )
except ImportError:
    sys.path.insert(0, ROOT_DIR)
    from train_model import (
        AcousticScaler,
        AcousticKMeans,
        AcousticKNNRecommender,
        train_recommender,
        MODEL_OUTPUT_PATH,
        FEATURE_COLS,
        FEATURE_WEIGHTS
    )

class MusicRecommender:
    """
    Production Machine Learning Recommendation System.
    Combines K-Means acoustic vibe clustering and K-Nearest Neighbors (KNN)
    cosine metric space retrieval across 40,000 tracks.
    """
    def __init__(self):
        self.feature_cols = FEATURE_COLS
        self.feature_weights = FEATURE_WEIGHTS
        self.df_tracks = pd.DataFrame()
        self.track_id_to_idx = {}
        self.idx_to_track_id = {}
        self.X_norm = np.empty((0, len(self.feature_cols)), dtype=np.float32)
        
        # ML Model components
        self.scaler = None
        self.kmeans = None
        self.knn = None
        self.cluster_profiles = {}
        self.cluster_labels = np.array([], dtype=np.int32)
        self.is_ml_trained = False
        
        self.load_engine()

    def load_engine(self):
        """Loads or trains the ML model pipeline and indexes all tracks in RAM."""
        print("[*] Initializing Machine Learning Recommendation Engine...")
        
        # 1. Ensure trained model exists
        if not os.path.exists(MODEL_OUTPUT_PATH):
            print(f"[!] No trained ML model found at {MODEL_OUTPUT_PATH}. Running automated training...")
            try:
                train_recommender(n_clusters=10)
            except Exception as e:
                print(f"[!] Automated training failed: {e}")

        # 2. Load trained ML model bundle
        if os.path.exists(MODEL_OUTPUT_PATH):
            try:
                with open(MODEL_OUTPUT_PATH, 'rb') as f:
                    bundle = pickle.load(f)
                self.scaler = bundle.get('scaler')
                self.kmeans = bundle.get('kmeans')
                self.knn = bundle.get('knn')
                self.cluster_profiles = bundle.get('cluster_profiles', {})
                self.cluster_labels = bundle.get('cluster_labels')
                self.X_norm = bundle.get('X_norm')
                self.track_id_to_idx = bundle.get('track_id_to_idx', {})
                self.idx_to_track_id = {i: tid for tid, i in self.track_id_to_idx.items()}
                self.is_ml_trained = True
                print(f"[+] Loaded trained ML model ({bundle.get('model_name')} v{bundle.get('version')}) with {len(self.cluster_profiles)} vibe clusters.")
            except Exception as e:
                print(f"[!] Error loading ML model pickle: {e}")

        # 3. Load SQLite track metadata
        conn = sqlite3.connect(DB_PATH)
        # Check if cluster_id exists in tracks
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tracks)")
        cols = [c[1] for c in cursor.fetchall()]
        has_cluster = 'cluster_id' in cols

        query = f"""
            SELECT id, track_id, track_name, artists, album_name, popularity,
                   duration_ms, explicit, {', '.join(self.feature_cols)},
                   track_genre, preview_url, cover_url
                   {', cluster_id' if has_cluster else ''}
            FROM tracks
        """
        self.df_tracks = pd.read_sql_query(query, conn)
        conn.close()

        if len(self.df_tracks) == 0:
            print("[!] Warning: No tracks found in SQLite database.")
            return

        # Ensure ID mappings
        self.track_id_to_idx = {tid: i for i, tid in enumerate(self.df_tracks['track_id'])}
        self.idx_to_track_id = {i: tid for i, tid in enumerate(self.df_tracks['track_id'])}

        # Fallback if pickle was absent
        if not self.is_ml_trained or len(self.X_norm) != len(self.df_tracks):
            print("[*] Recomputing fallback normalized embeddings...")
            self.scaler = AcousticScaler(weights=self.feature_weights)
            X_raw = self.df_tracks[self.feature_cols].values.astype(np.float32)
            X_weighted = self.scaler.fit_transform(X_raw)
            norms = np.maximum(np.linalg.norm(X_weighted, axis=1, keepdims=True), 1e-7)
            self.X_norm = (X_weighted / norms).astype(np.float32)
            self.knn = AcousticKNNRecommender()
            self.knn.fit(self.X_norm, self.df_tracks['track_id'])
            self.kmeans = AcousticKMeans(n_clusters=10)
            self.kmeans.fit(X_weighted)
            self.cluster_labels = self.kmeans.labels_

        # Add cluster tags to DataFrame in memory for fast retrieval
        if len(self.cluster_labels) == len(self.df_tracks):
            self.df_tracks['cluster_id'] = self.cluster_labels
            self.df_tracks['vibe_name'] = [
                self.cluster_profiles.get(cid, {}).get('name', f'Cluster {cid}')
                for cid in self.cluster_labels
            ]
            self.df_tracks['vibe_tag'] = [
                self.cluster_profiles.get(cid, {}).get('tag', 'Curated')
                for cid in self.cluster_labels
            ]

        print(f"[OK] Recommender ML ready: {len(self.df_tracks):,} tracks indexed in RAM.")

    def get_track_by_id(self, track_id):
        """Returns track row dictionary by track_id."""
        if track_id not in self.track_id_to_idx:
            return None
        idx = self.track_id_to_idx[track_id]
        return self._format_track_dict(idx)

    def _format_track_dict(self, idx, score=None):
        """Helper to convert DataFrame row to JSON-ready dict with clean, valid JSON types (no NaNs)."""
        row = self.df_tracks.iloc[idx].to_dict()

        preview = row.get('preview_url')
        if preview is None or (isinstance(preview, float) and np.isnan(preview)) or str(preview).lower() in ('nan', 'none'):
            preview = None
        else:
            preview = str(preview)

        cover = row.get('cover_url')
        if cover is None or (isinstance(cover, float) and np.isnan(cover)) or str(cover).lower() in ('nan', 'none') or not str(cover).strip():
            cover = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80"
        else:
            cover = str(cover)

        album = row.get('album_name')
        if album is None or (isinstance(album, float) and np.isnan(album)) or str(album).lower() in ('nan', 'none'):
            album = ''
        else:
            album = str(album)

        def _clean_float(val, default=0.0, digits=3):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            try:
                v = float(val)
                return default if np.isnan(v) else round(v, digits)
            except (ValueError, TypeError):
                return default

        def _clean_int(val, default=0):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            try:
                v = float(val)
                return default if np.isnan(v) else int(v)
            except (ValueError, TypeError):
                return default

        res = {
            'id': _clean_int(row.get('id'), idx + 1),
            'track_id': str(row['track_id']),
            'track_name': str(row['track_name']),
            'artists': str(row['artists']),
            'album_name': album,
            'popularity': _clean_int(row.get('popularity'), 0),
            'duration_ms': _clean_int(row.get('duration_ms'), 0),
            'explicit': _clean_int(row.get('explicit'), 0),
            'danceability': _clean_float(row.get('danceability'), 0.0, 3),
            'energy': _clean_float(row.get('energy'), 0.0, 3),
            'valence': _clean_float(row.get('valence'), 0.0, 3),
            'tempo': _clean_float(row.get('tempo'), 0.0, 1),
            'acousticness': _clean_float(row.get('acousticness'), 0.0, 3),
            'instrumentalness': _clean_float(row.get('instrumentalness'), 0.0, 4),
            'loudness': _clean_float(row.get('loudness'), 0.0, 1),
            'speechiness': _clean_float(row.get('speechiness'), 0.0, 3),
            'liveness': _clean_float(row.get('liveness'), 0.0, 3),
            'track_genre': str(row.get('track_genre', 'pop')),
            'preview_url': preview,
            'cover_url': cover,
            'cluster_id': _clean_int(row.get('cluster_id'), 0),
            'vibe_name': str(row.get('vibe_name', 'Eclectic')),
            'vibe_tag': str(row.get('vibe_tag', 'Music'))
        }
        if score is not None:
            s_val = _clean_float(score, 50.0, 1)
            res['similarity_score'] = s_val
            res['match_score'] = s_val
        return res

    def get_similar_tracks(self, seed_track_id, limit=12):
        """
        ML Content-Based Recommendation using KNN Cosine Distance.
        Finds the closest acoustic neighbors in normalized feature space,
        applying slight genre coherence and strict artist diversity constraints.
        """
        if seed_track_id not in self.track_id_to_idx:
            return []

        seed_idx = self.track_id_to_idx[seed_track_id]
        seed_vec = self.X_norm[seed_idx]
        seed_genre = self.df_tracks.iloc[seed_idx]['track_genre']

        # Query top neighbors (request extra to allow artist diversity filtering)
        candidate_indices, raw_similarities = self.knn.kneighbors(
            seed_vec,
            n_neighbors=min(limit * 4, len(self.df_tracks)),
            exclude_indices=[seed_idx]
        )

        results = []
        seen_artists = {}

        for idx, sim in zip(candidate_indices, raw_similarities):
            if len(results) >= limit:
                break
            track_artist = self.df_tracks.iloc[idx]['artists']
            current_count = seen_artists.get(track_artist, 0)
            if current_count >= 2:
                continue
            seen_artists[track_artist] = current_count + 1

            # Bonus for genre match to preserve musical coherence
            score_val = float(sim)
            if self.df_tracks.iloc[idx]['track_genre'] == seed_genre:
                score_val = min(1.0, score_val + 0.05)

            pct = max(10.0, round(score_val * 100.0, 1))
            results.append(self._format_track_dict(idx, score=pct))

        return results

    def recommend_by_mood(self, valence=0.5, energy=0.5, danceability=0.5, acousticness=0.5, tempo_bpm=120, limit=12):
        """
        ML Mood & Vibe Recommender:
        1. Projects user mood vector into the trained acoustic feature space.
        2. Applies the trained RobustScaler and perceptual weights.
        3. Identifies the nearest K-Means cluster.
        4. Retrieves nearest neighbors via KNN with match percentages.
        """
        raw_target = np.array([[
            float(danceability),
            float(energy),
            float(valence),
            float(tempo_bpm),
            float(acousticness),
            0.10,   # instrumentalness default
            -8.0,   # loudness default dB
            0.06,   # speechiness default
            0.15    # liveness default
        ]], dtype=np.float32)

        # Transform target using trained scaler
        target_weighted = self.scaler.transform(raw_target)[0]
        target_norm = target_weighted / max(float(np.linalg.norm(target_weighted)), 1e-7)

        # Predict cluster
        predicted_cluster = int(self.kmeans.predict(target_weighted.reshape(1, -1))[0])
        cluster_info = self.cluster_profiles.get(predicted_cluster, {})

        # Query KNN
        candidate_indices, raw_similarities = self.knn.kneighbors(
            target_norm,
            n_neighbors=min(limit * 3, len(self.df_tracks))
        )

        results = []
        seen_artists = {}
        for idx, sim in zip(candidate_indices, raw_similarities):
            if len(results) >= limit:
                break
            artist = self.df_tracks.iloc[idx]['artists']
            if seen_artists.get(artist, 0) >= 2:
                continue
            seen_artists[artist] = seen_artists.get(artist, 0) + 1

            match_pct = max(15.0, round(float(sim) * 100.0, 1))
            track_dict = self._format_track_dict(idx, score=match_pct)
            track_dict['matched_vibe'] = cluster_info.get('name', 'Custom Mood')
            results.append(track_dict)

        return results

    def recommend_for_user(self, user_id=1, limit=12):
        """
        Hybrid Personalized Recommendation:
        Aggregates user's liked tracks into a personalized taste vector in the ML embedding space.
        Uses KNN to retrieve unseen tracks closest to their taste centroid.
        Falls back to curated diverse trending hits for cold-start users.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT track_id FROM interactions WHERE user_id = ? AND action = 'like'", (user_id,))
        liked_tids = [r[0] for r in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT track_id FROM interactions WHERE user_id = ?", (user_id,))
        interacted_tids = set(r[0] for r in cursor.fetchall())
        conn.close()

        # Cold start fallback
        if not liked_tids:
            return self.get_trending_tracks(limit=limit)

        liked_indices = [self.track_id_to_idx[tid] for tid in liked_tids if tid in self.track_id_to_idx]
        if not liked_indices:
            return self.get_trending_tracks(limit=limit)

        # Compute centroid user taste vector in normalized ML space
        user_vector = np.mean(self.X_norm[liked_indices], axis=0)
        norm = np.linalg.norm(user_vector)
        user_vector_norm = user_vector / (norm if norm > 0 else 1e-7)

        # Exclude tracks the user already interacted with
        exclude_indices = [self.track_id_to_idx[tid] for tid in interacted_tids if tid in self.track_id_to_idx]

        candidate_indices, similarities = self.knn.kneighbors(
            user_vector_norm,
            n_neighbors=min(limit * 4, len(self.df_tracks)),
            exclude_indices=exclude_indices
        )

        results = []
        seen_artists = {}
        for idx, sim in zip(candidate_indices, similarities):
            if len(results) >= limit:
                break
            artist = self.df_tracks.iloc[idx]['artists']
            if seen_artists.get(artist, 0) >= 2:
                continue
            seen_artists[artist] = seen_artists.get(artist, 0) + 1

            pct = max(20.0, round(float(sim) * 100.0, 1))
            results.append(self._format_track_dict(idx, score=pct))

        # Fallback if filtered out everything
        if len(results) == 0:
            return self.get_trending_tracks(limit=limit)

        return results

    def get_trending_tracks(self, limit=12):
        """Returns top popular tracks ensuring diverse artists and genres."""
        df_sorted = self.df_tracks.sort_values(by='popularity', ascending=False)
        results = []
        seen_artists = set()
        seen_genres = set()

        for idx, row in df_sorted.iterrows():
            if len(results) >= limit:
                break
            artist = row['artists']
            genre = row['track_genre']
            if artist in seen_artists:
                continue
            seen_artists.add(artist)
            seen_genres.add(genre)

            results.append(self._format_track_dict(self.track_id_to_idx[row['track_id']]))

        return results

    def get_cluster_tracks(self, cluster_id=0, limit=12):
        """Returns top popular tracks belonging to a specific ML vibe cluster."""
        matching = self.df_tracks[self.df_tracks['cluster_id'] == cluster_id]
        matching_sorted = matching.sort_values(by='popularity', ascending=False)
        results = []
        seen_artists = set()
        for _, row in matching_sorted.iterrows():
            if len(results) >= limit:
                break
            if row['artists'] in seen_artists:
                continue
            seen_artists.add(row['artists'])
            results.append(self._format_track_dict(self.track_id_to_idx[row['track_id']]))
        return results

    def get_user_taste_analytics(self, user_id=1):
        """Calculates acoustic parameters and ML cluster preferences of the user's liked songs."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT track_id FROM interactions WHERE user_id = ? AND action = 'like'", (user_id,))
        liked_tids = [r[0] for r in cursor.fetchall()]
        conn.close()

        if not liked_tids:
            return {
                "has_profile": False,
                "likes_count": 0,
                "danceability": 0.5,
                "energy": 0.5,
                "valence": 0.5,
                "acousticness": 0.5,
                "top_genres": [],
                "favorite_vibe": "Eclectic Explorer"
            }

        liked_indices = [self.track_id_to_idx[tid] for tid in liked_tids if tid in self.track_id_to_idx]
        if not liked_indices:
            return {"has_profile": False, "likes_count": len(liked_tids)}

        subset = self.df_tracks.iloc[liked_indices]
        top_genres = subset['track_genre'].value_counts().head(3).index.tolist()

        # Dominant ML cluster
        cluster_counts = subset['cluster_id'].value_counts()
        fav_cluster = int(cluster_counts.index[0]) if len(cluster_counts) > 0 else 0
        fav_vibe = self.cluster_profiles.get(fav_cluster, {}).get('name', 'Custom Vibe')

        return {
            "has_profile": True,
            "likes_count": len(liked_indices),
            "danceability": round(float(subset['danceability'].mean()), 2),
            "energy": round(float(subset['energy'].mean()), 2),
            "valence": round(float(subset['valence'].mean()), 2),
            "acousticness": round(float(subset['acousticness'].mean()), 2),
            "top_genres": top_genres,
            "favorite_vibe": fav_vibe
        }

# Global singleton recommender instance
recommender = MusicRecommender()
