# 🎵 VibeNest AI — Intelligent Music Recommendation System

A full-stack, end-to-end music recommendation web application built with **Flask (Python)**, **SQLite**, and **Vanilla HTML5 / CSS3 / JavaScript** with a glassmorphism dark-mode user experience.

![UI Overview](https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1200&auto=format&fit=crop&q=80)

---

## 🌟 Key Features

### 1. Multi-Strategy Recommendation Engines
* **Track-to-Track Radar (Content-Based Cosine Similarity)**:
  - Standardized feature vector matching across 9 acoustic dimensions: `danceability`, `energy`, `valence`, `tempo`, `acousticness`, `instrumentalness`, `loudness`, `speechiness`, and `liveness`.
  - Robust-scaled, perceptually weighted feature matrices pre-loaded in memory for fast similarity searches across 40,000+ tracks.
  - Interactive HTML5 `<canvas>` radar spiderweb chart comparing the seed track's acoustic profile against recommended songs.
* **Mood & Vibe Laboratory (Vector Sliders & Presets)**:
  - Presets for *Power Gym*, *Summer Party*, *Midnight Chill*, *Deep Focus*, and *Coffee Shop Lo-Fi*.
  - Continuous sliders for **Valence (Sad ↔ Happy)**, **Energy (Calm ↔ Intense)**, **Danceability**, **Acousticness**, and **Tempo (BPM)** with instant Euclidean distance vector matching.
* **Personalized Hybrid Feed (User Taste Vector)**:
  - Dynamically recalculates the user's taste centroid based on liked tracks and interaction history.
  - Automatically filters out already played tracks and suggests diverse songs aligned with their profile.

### 2. Audio Playback & Open Media Enrichment
* **Live 30-Second Audio Previews**: Integrated on-demand resolution via iTunes Search API with persistent SQLite caching.
* **Web Audio API Ambient Synthesizer**: Smooth fallback chord synthesis ensuring tracks always play reliably without silent failures.
* **Persistent Bottom Glass Player Dock**:
  - Vinyl disc rotation animation on active tracks.
  - Interactive seek rail with timestamps.
  - Volume control and instant heart/like state toggle.
  - Real-time animated HTML5 `<canvas>` frequency spectrum equalizer bars.

### 3. Database Architecture (SQLite)
* `tracks`: 40,000 curated Spotify tracks spanning the available genres with genre-balanced selection, deduplication, and indexing on title, artist, genre, and popularity.
* `users`: Profile and account management.
* `interactions`: Real-time logging of plays, likes, unlikes, and skips.
* `playlists` & `playlist_tracks`: Custom playlist creation.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* Python 3.10+ installed
* Dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Machine Learning Model Training (Optional)
The system automatically uses the pre-trained ML model, but you can retrain it on the 40,000 dataset at any time:
```bash
python train_model.py
```
This trains:
* **K-Means Clustering** (10 acoustic vibe archetypes like *High-Energy Dance*, *Midnight Chill*, *Warm Indie*)
* **K-Nearest Neighbors (KNN)** metric cosine indexer
* Serializes the model bundle to `models/music_recommender_model.pkl`

### 3. Run the Application
Launch the entire system (backend server + static frontend) with a single command:
```bash
python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```text
music-recommandation-system/
├── backend/
│   ├── __init__.py           # Backend package marker
│   ├── app.py               # Flask application with REST API endpoints & static routing
│   ├── database.py          # SQLite schema, indexing, and connection management
│   ├── ml_model.py          # ML core models: AcousticScaler, AcousticKMeans, AcousticKNNRecommender
│   ├── recommender.py       # Production ML recommender integrating KNN & KMeans clusters
│   ├── audio_fetcher.py     # iTunes 30-sec preview & cover artwork resolver with caching
│   └── seed_data.py         # Automated dataset ingestion and cleaning script
├── data/
│   ├── dataset.csv          # Spotify 114k tracks dataset
│   └── music.db             # Indexed SQLite database (40,000 tracks)
├── models/
│   └── music_recommender_model.pkl # Trained ML model bundle (KMeans + KNN + Scaler)
├── frontend/
│   ├── index.html           # Single-Page Application interface
│   ├── css/
│   │   ├── styles.css       # Obsidian glassmorphic design system and responsive grid
│   │   └── player.css       # Persistent audio player dock and equalizer styles
│   └── js/
│       ├── api.js           # REST API client
│       ├── player.js        # HTML5 audio player & canvas equalizer spectrum
│       ├── radar.js         # Canvas audio feature radar spiderweb chart
│       └── app.js           # Navigation, search, mood lab, and UI interactions
├── requirements.txt         # Python package dependencies
├── train_model.py           # Standalone Machine Learning model training pipeline
├── run.py                   # One-click startup script
└── README.md                # Project documentation
```

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & total tracks indexed |
| `GET` | `/api/genres` | List of 112 available genres |
| `GET` | `/api/tracks/popular?limit=12` | Top trending songs by popularity |
| `GET` | `/api/tracks/search?q=...&genre=...` | Substring search across title, artist, or genre |
| `GET` | `/api/tracks/<track_id>/preview` | Resolve 30s audio MP3/AAC preview and 600x600 cover art |
| `GET` | `/api/recommend/similar/<track_id>?limit=12` | Cosine similarity recommendations for seed song |
| `POST` | `/api/recommend/mood` | Mood vector matching (valence, energy, dance, acoustic, tempo) |
| `GET` | `/api/recommend/user?user_id=1&limit=12` | Personalized hybrid recommendations from user's taste vector |
| `POST` | `/api/interactions` | Log interactions (`like`, `unlike`, `play`, `skip`) |
| `GET` | `/api/user/likes?user_id=1` | Get user's liked tracks |
| `GET` | `/api/user/taste?user_id=1` | Get acoustic analytics of user's taste profile |
