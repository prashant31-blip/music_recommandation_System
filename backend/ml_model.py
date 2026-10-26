"""
VibeNest AI - Machine Learning Core Models
Defines the AcousticScaler, AcousticKMeans clustering model, and
AcousticKNNRecommender metric space indexer.
"""

import numpy as np

# Perceptual acoustic feature weights (human psychoacoustic importance)
FEATURE_COLS = [
    'danceability',
    'energy',
    'valence',
    'tempo',
    'acousticness',
    'instrumentalness',
    'loudness',
    'speechiness',
    'liveness'
]

FEATURE_WEIGHTS = np.array(
    [1.15, 1.25, 1.15, 0.75, 1.00, 0.70, 0.50, 0.45, 0.50],
    dtype=np.float32
)

class AcousticScaler:
    """
    Robust acoustic feature scaler using median and quantile range (5th to 95th percentile).
    Mitigates the influence of tempo and loudness outliers.
    """
    def __init__(self, weights=FEATURE_WEIGHTS):
        self.weights = weights
        self.medians = None
        self.scales = None

    def fit(self, X):
        X = np.asarray(X, dtype=np.float32)
        self.medians = np.median(X, axis=0)
        q5 = np.percentile(X, 5, axis=0)
        q95 = np.percentile(X, 95, axis=0)
        self.scales = q95 - q5
        self.scales[self.scales == 0] = 1.0
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=np.float32)
        X_scaled = (X - self.medians) / self.scales
        return X_scaled * self.weights

    def fit_transform(self, X):
        return self.fit(X).transform(X)

    def inverse_transform(self, X_weighted):
        X_unweighted = np.asarray(X_weighted, dtype=np.float32) / self.weights
        return (X_unweighted * self.scales) + self.medians


class AcousticKMeans:
    """
    Vectorized K-Means Clustering implementation optimized with NumPy BLAS.
    Clusters music tracks into distinct acoustic mood/vibe archetypes.
    """
    def __init__(self, n_clusters=10, max_iter=100, tol=1e-4, random_state=42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state
        self.cluster_centers_ = None
        self.labels_ = None
        self.inertia_ = 0.0

    def fit(self, X):
        X = np.asarray(X, dtype=np.float32)
        n_samples, n_features = X.shape
        np.random.seed(self.random_state)

        # 1. K-Means++ centroid initialization
        centroids = [X[np.random.randint(n_samples)]]
        for _ in range(1, self.n_clusters):
            dist_sq = np.min([np.sum((X - c)**2, axis=1) for c in centroids], axis=0)
            total = np.sum(dist_sq)
            probs = dist_sq / total if total > 0 else np.ones(n_samples) / n_samples
            next_idx = np.random.choice(n_samples, p=probs)
            centroids.append(X[next_idx])
        centroids = np.array(centroids, dtype=np.float32)

        # 2. Iterative optimization
        for it in range(self.max_iter):
            X_sq = np.sum(X**2, axis=1, keepdims=True)
            C_sq = np.sum(centroids**2, axis=1)
            dist_matrix = X_sq + C_sq - 2.0 * np.dot(X, centroids.T)

            labels = np.argmin(dist_matrix, axis=1)

            new_centroids = np.zeros_like(centroids)
            for k in range(self.n_clusters):
                mask = (labels == k)
                if np.any(mask):
                    new_centroids[k] = np.mean(X[mask], axis=0)
                else:
                    new_centroids[k] = centroids[k]

            shift = np.max(np.abs(centroids - new_centroids))
            centroids = new_centroids
            if shift < self.tol:
                break

        X_sq = np.sum(X**2, axis=1, keepdims=True)
        C_sq = np.sum(centroids**2, axis=1)
        dist_matrix = X_sq + C_sq - 2.0 * np.dot(X, centroids.T)
        self.labels_ = np.argmin(dist_matrix, axis=1)
        self.inertia_ = float(np.sum(np.min(dist_matrix, axis=1)))
        self.cluster_centers_ = centroids
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=np.float32)
        X_sq = np.sum(X**2, axis=1, keepdims=True)
        C_sq = np.sum(self.cluster_centers_**2, axis=1)
        dist_matrix = X_sq + C_sq - 2.0 * np.dot(X, self.cluster_centers_.T)
        return np.argmin(dist_matrix, axis=1)


class AcousticKNNRecommender:
    """
    Vectorized K-Nearest Neighbors recommendation engine using Cosine Distance.
    Operates on L2-normalized feature embeddings.
    """
    def __init__(self):
        self.X_norm = None
        self.track_ids = None
        self.track_id_to_idx = {}

    def fit(self, X_norm, track_ids):
        self.X_norm = np.asarray(X_norm, dtype=np.float32)
        self.track_ids = list(track_ids)
        self.track_id_to_idx = {tid: i for i, tid in enumerate(self.track_ids)}
        return self

    def kneighbors(self, query_norm, n_neighbors=12, exclude_indices=None):
        query_norm = np.asarray(query_norm, dtype=np.float32).reshape(1, -1)
        similarities = np.dot(self.X_norm, query_norm.T).ravel()

        if exclude_indices:
            for idx in exclude_indices:
                if 0 <= idx < len(similarities):
                    similarities[idx] = -1.0

        top_indices = np.argsort(-similarities)[:n_neighbors]
        top_scores = similarities[top_indices]
        return top_indices, top_scores
