/**
 * VIBENEST AI - REST API CLIENT
 */

// Automatically determine backend URL:
// If running directly through Flask server (port 5000), use relative path '/api'
// If opened via Live Server (port 5500, 3000, etc.) or local file, point to http://127.0.0.1:5000/api
const getApiBase = () => {
  if (typeof window === 'undefined') return '/api';
  const port = window.location.port;
  if (port === '5000' || (!port && window.location.protocol.startsWith('http') && window.location.pathname.startsWith('/api'))) {
    return '/api';
  }
  return 'http://127.0.0.1:5000/api';
};

const API_BASE = getApiBase();

export const api = {
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return await res.json();
    } catch (e) {
      console.error('Health check failed:', e);
      return { status: 'error', error: e.message };
    }
  },

  async getClusters() {
    try {
      const res = await fetch(`${API_BASE}/clusters`);
      const data = await res.json();
      return data.clusters || {};
    } catch (e) {
      console.error('Failed to fetch clusters:', e);
      return {};
    }
  },

  async getClusterTracks(clusterId, limit = 12) {
    try {
      const res = await fetch(`${API_BASE}/clusters/${clusterId}/tracks?limit=${limit}`);
      const data = await res.json();
      return data.tracks || [];
    } catch (e) {
      console.error('Failed to fetch cluster tracks:', e);
      return [];
    }
  },

  async getGenres() {
    try {
      const res = await fetch(`${API_BASE}/genres`);
      const data = await res.json();
      return data.genres || [];
    } catch (e) {
      console.error('Failed to fetch genres:', e);
      return [];
    }
  },

  async getPopular(limit = 12) {
    try {
      const res = await fetch(`${API_BASE}/tracks/popular?limit=${limit}`);
      const data = await res.json();
      return data.tracks || [];
    } catch (e) {
      console.error('Failed to fetch popular tracks:', e);
      return [];
    }
  },

  async searchTracks(q = '', genre = '', limit = 20) {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (genre) params.set('genre', genre);
      params.set('limit', limit);
      const res = await fetch(`${API_BASE}/tracks/search?${params.toString()}`);
      const data = await res.json();
      return data.tracks || [];
    } catch (e) {
      console.error('Search failed:', e);
      return [];
    }
  },

  async getTrack(trackId) {
    try {
      const res = await fetch(`${API_BASE}/tracks/${encodeURIComponent(trackId)}`);
      const data = await res.json();
      return data.track || null;
    } catch (e) {
      console.error(`Failed to fetch track ${trackId}:`, e);
      return null;
    }
  },

  async getPreview(trackId) {
    try {
      const res = await fetch(`${API_BASE}/tracks/${encodeURIComponent(trackId)}/preview`);
      return await res.json();
    } catch (e) {
      console.error(`Failed to fetch preview for ${trackId}:`, e);
      return { preview_url: null, cover_url: null };
    }
  },

  async getSimilarTracks(trackId, limit = 12) {
    try {
      const res = await fetch(`${API_BASE}/recommend/similar/${encodeURIComponent(trackId)}?limit=${limit}`);
      return await res.json();
    } catch (e) {
      console.error(`Failed to fetch similar tracks for ${trackId}:`, e);
      return { seed_track: null, recommendations: [] };
    }
  },

  async recommendMood(moodParams) {
    try {
      const res = await fetch(`${API_BASE}/recommend/mood`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(moodParams)
      });
      const data = await res.json();
      return data.recommendations || [];
    } catch (e) {
      console.error('Failed to fetch mood recommendations:', e);
      return [];
    }
  },

  async recommendUser(userId = 1, limit = 12) {
    try {
      const res = await fetch(`${API_BASE}/recommend/user?user_id=${userId}&limit=${limit}`);
      const data = await res.json();
      return data.recommendations || [];
    } catch (e) {
      console.error('Failed to fetch user recommendations:', e);
      return [];
    }
  },

  async logInteraction(trackId, action = 'like', userId = 1) {
    try {
      const res = await fetch(`${API_BASE}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: trackId, action, user_id: userId })
      });
      return await res.json();
    } catch (e) {
      console.error('Failed to log interaction:', e);
      return { success: false };
    }
  },

  async getUserLikes(userId = 1) {
    try {
      const res = await fetch(`${API_BASE}/user/likes?user_id=${userId}`);
      const data = await res.json();
      return data.likes || [];
    } catch (e) {
      console.error('Failed to fetch likes:', e);
      return [];
    }
  },

  async getUserTaste(userId = 1) {
    try {
      const res = await fetch(`${API_BASE}/user/taste?user_id=${userId}`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch taste profile:', e);
      return null;
    }
  }
};
