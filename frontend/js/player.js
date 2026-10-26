/**
 * VIBENEST AI - ROBUST AUDIO PLAYER & EQUALIZER
 * Guaranteed zero beep sounds, smooth queue streaming & real audio playback
 */

import { api } from './api.js';

export class MusicPlayer {
  constructor() {
    this.audio = new Audio();
    this.audio.preload = 'auto';
    this.currentTrack = null;
    this.queue = [];
    this.currentIndex = -1;
    this.isPlaying = false;
    this.isLoading = false;
    this.likedTrackIds = new Set();
    this.errorRetryCount = 0;

    this.initElements();
    this.bindEvents();
    this.initEqualizer();
  }

  initElements() {
    this.artworkImg = document.getElementById('player-artwork-img');
    this.artworkContainer = document.getElementById('player-artwork-container');
    this.trackTitle = document.getElementById('player-track-name');
    this.artistName = document.getElementById('player-artist-name');
    this.playBtn = document.getElementById('btn-player-play');
    this.prevBtn = document.getElementById('btn-player-prev');
    this.nextBtn = document.getElementById('btn-player-next');
    this.likeBtn = document.getElementById('btn-player-like');
    
    this.currentTimeLabel = document.getElementById('label-current-time');
    this.durationLabel = document.getElementById('label-duration');
    this.progressRail = document.getElementById('progress-bar-rail');
    this.progressFill = document.getElementById('progress-bar-fill');
    
    this.volumeSlider = document.getElementById('volume-slider');
    this.equalizerCanvas = document.getElementById('canvas-equalizer');

    // Create Toast Container if not present
    this.toastContainer = document.getElementById('player-toast-container');
    if (!this.toastContainer) {
      this.toastContainer = document.createElement('div');
      this.toastContainer.id = 'player-toast-container';
      this.toastContainer.className = 'player-toast-container';
      document.body.appendChild(this.toastContainer);
    }
  }

  bindEvents() {
    if (this.playBtn) {
      this.playBtn.addEventListener('click', () => this.togglePlay());
    }
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => this.playPrevious());
    }
    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => this.playNext());
    }
    if (this.likeBtn) {
      this.likeBtn.addEventListener('click', () => this.toggleLikeCurrent());
    }

    // Native Audio Events
    this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
    this.audio.addEventListener('ended', () => this.playNext());
    
    this.audio.addEventListener('playing', () => {
      this.setLoadingState(false);
      this.setPlayState(true);
      this.errorRetryCount = 0;
    });

    this.audio.addEventListener('pause', () => {
      this.setPlayState(false);
    });

    this.audio.addEventListener('waiting', () => {
      this.setLoadingState(true);
    });

    this.audio.addEventListener('canplay', () => {
      this.setLoadingState(false);
    });

    // Graceful error handler: NEVER emit a beep!
    this.audio.addEventListener('error', (e) => {
      console.warn('Audio stream error encountered:', e);
      this.setLoadingState(false);
      this.handleStreamFailure();
    });

    // Scrubber click seek
    if (this.progressRail) {
      this.progressRail.addEventListener('click', (e) => {
        if (!this.audio.duration) return;
        const rect = this.progressRail.getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.audio.currentTime = percent * this.audio.duration;
        this.progressFill.style.width = `${percent * 100}%`;
      });
    }

    // Volume Slider
    if (this.volumeSlider) {
      this.audio.volume = parseFloat(this.volumeSlider.value || 0.8);
      this.volumeSlider.addEventListener('input', (e) => {
        this.audio.volume = parseFloat(e.target.value);
      });
    }
  }

  showToast(message, type = 'info') {
    if (!this.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `player-toast toast-${type}`;
    toast.textContent = message;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 400);
    }, 2800);
  }

  setQueue(tracks, startIndex = 0) {
    this.queue = tracks || [];
    this.currentIndex = startIndex;
    if (this.queue.length > 0 && startIndex >= 0 && startIndex < this.queue.length) {
      this.loadTrack(this.queue[startIndex], true);
    }
  }

  async loadTrack(track, autoPlay = true) {
    if (!track) return;
    this.currentTrack = track;
    this.errorRetryCount = 0;

    // 1. Instant Optimistic UI Update (0ms latency feedback)
    this.trackTitle.textContent = track.track_name || 'Loading Track...';
    this.artistName.textContent = track.artists || 'Artist';
    this.currentTimeLabel.textContent = '0:00';
    this.durationLabel.textContent = '0:30';
    this.progressFill.style.width = '0%';
    this.updateLikeButtonUI();

    const defaultCover = 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80';
    this.artworkImg.src = track.cover_url || defaultCover;

    // Show loading spinner on play button
    this.setLoadingState(true);

    // Stop currently playing audio before switching sources
    this.audio.pause();
    this.audio.removeAttribute('src');

    // 2. Resolve audio preview URL from cache or backend multi-tier engine
    let previewUrl = track.preview_url;
    if (!previewUrl) {
      try {
        const media = await api.getPreview(track.track_id);
        if (media.cover_url) {
          this.artworkImg.src = media.cover_url;
          track.cover_url = media.cover_url;
        }
        previewUrl = media.preview_url;
        track.preview_url = previewUrl;

        if (media.source === 'artist_radio') {
          this.showToast(`Playing artist radio preview for "${track.artists}"`, 'info');
        } else if (media.source === 'genre_radio') {
          this.showToast(`Playing ${track.track_genre || 'music'} radio preview`, 'info');
        }
      } catch (err) {
        console.warn('Preview resolution network error:', err);
      }
    }

    // 3. Initiate Real Audio Stream
    if (previewUrl) {
      this.audio.src = previewUrl;
      this.audio.load();

      if (autoPlay) {
        const playPromise = this.audio.play();
        if (playPromise !== undefined) {
          playPromise.then(() => {
            this.setPlayState(true);
            this.setLoadingState(false);
          }).catch(err => {
            this.setLoadingState(false);
            if (err.name === 'NotAllowedError') {
              // Browser requires user gesture before playing audio
              console.log('Autoplay deferred until user interaction.');
              this.setPlayState(false);
            } else if (err.name === 'AbortError') {
              // Rapid switching between songs, safe to ignore
            } else {
              console.warn('Audio playback failed:', err);
              this.handleStreamFailure();
            }
          });
        }
      } else {
        this.setLoadingState(false);
      }
    } else {
      // If preview completely unavailable, gracefully move to next track without beeping
      this.setLoadingState(false);
      this.handleStreamFailure();
    }

    // Log play interaction in SQLite
    api.logInteraction(track.track_id, 'play');
    document.dispatchEvent(new CustomEvent('track-playing', { detail: track }));
  }

  handleStreamFailure() {
    if (!this.currentTrack) return;
    this.errorRetryCount++;
    const songName = this.currentTrack.track_name || 'Track';

    if (this.queue.length > 1 && this.errorRetryCount < 3) {
      this.showToast(`"${songName}" preview unavailable. Playing next...`, 'warning');
      setTimeout(() => this.playNext(), 600);
    } else {
      this.showToast(`Audio preview unavailable for "${songName}".`, 'warning');
      this.setPlayState(false);
    }
  }

  togglePlay() {
    if (!this.currentTrack && this.queue.length > 0) {
      this.loadTrack(this.queue[0], true);
      return;
    }

    if (!this.currentTrack) return;

    if (this.isPlaying) {
      this.audio.pause();
      this.setPlayState(false);
    } else {
      if (this.audio.src) {
        this.setLoadingState(true);
        this.audio.play().then(() => {
          this.setPlayState(true);
          this.setLoadingState(false);
        }).catch(err => {
          this.setLoadingState(false);
          console.warn('Play toggle error:', err);
          this.handleStreamFailure();
        });
      } else {
        this.loadTrack(this.currentTrack, true);
      }
    }
  }

  setPlayState(playing) {
    this.isPlaying = playing;
    if (this.artworkContainer) {
      this.artworkContainer.classList.toggle('playing', playing);
    }
    if (this.playBtn && !this.isLoading) {
      this.playBtn.innerHTML = playing 
        ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`
        : `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
      this.playBtn.title = playing ? 'Pause' : 'Play';
    }
  }

  setLoadingState(loading) {
    this.isLoading = loading;
    if (!this.playBtn) return;
    if (loading) {
      this.playBtn.innerHTML = `
        <svg class="spinner-svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
        </svg>
      `;
      this.playBtn.title = 'Loading audio...';
    } else {
      this.setPlayState(this.isPlaying);
    }
  }

  playNext() {
    if (this.queue.length === 0) return;
    this.currentIndex = (this.currentIndex + 1) % this.queue.length;
    this.loadTrack(this.queue[this.currentIndex], true);
  }

  playPrevious() {
    if (this.queue.length === 0) return;
    this.currentIndex = (this.currentIndex - 1 + this.queue.length) % this.queue.length;
    this.loadTrack(this.queue[this.currentIndex], true);
  }

  onTimeUpdate() {
    if (!this.audio.duration) return;
    const current = this.audio.currentTime;
    const duration = this.audio.duration;
    
    this.currentTimeLabel.textContent = this.formatTime(current);
    this.durationLabel.textContent = this.formatTime(duration);
    
    const pct = (current / duration) * 100;
    this.progressFill.style.width = `${pct}%`;
  }

  formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  async toggleLikeCurrent() {
    if (!this.currentTrack) return;
    const tid = this.currentTrack.track_id;
    const isLiked = this.likedTrackIds.has(tid);
    
    if (isLiked) {
      this.likedTrackIds.delete(tid);
      await api.logInteraction(tid, 'unlike');
      this.showToast(`Removed from Liked Songs`, 'info');
    } else {
      this.likedTrackIds.add(tid);
      await api.logInteraction(tid, 'like');
      this.showToast(`Added to Liked Songs ❤️`, 'info');
    }
    
    this.updateLikeButtonUI();
    document.dispatchEvent(new CustomEvent('like-toggled', { detail: { track_id: tid, isLiked: !isLiked } }));
  }

  updateLikeButtonUI() {
    if (!this.likeBtn || !this.currentTrack) return;
    const isLiked = this.likedTrackIds.has(this.currentTrack.track_id);
    this.likeBtn.classList.toggle('liked', isLiked);
    this.likeBtn.innerHTML = isLiked
      ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`
      : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`;
  }

  // --- Live Canvas Audio Equalizer Spectrum ---
  initEqualizer() {
    if (!this.equalizerCanvas) return;
    const ctx = this.equalizerCanvas.getContext('2d');
    const bars = 8;
    const barWidth = 4;
    const gap = 3;

    const render = () => {
      ctx.clearRect(0, 0, this.equalizerCanvas.width, this.equalizerCanvas.height);
      const isLive = this.isPlaying && !this.isLoading;
      
      for (let i = 0; i < bars; i++) {
        let height = 3; // resting height
        if (isLive) {
          const t = Date.now() / 150 + i * 0.8;
          height = Math.sin(t) * 10 + 14;
        }

        const x = i * (barWidth + gap) + 10;
        const y = this.equalizerCanvas.height - height;

        const grad = ctx.createLinearGradient(0, y, 0, this.equalizerCanvas.height);
        grad.addColorStop(0, '#ec4899');
        grad.addColorStop(0.5, '#8b5cf6');
        grad.addColorStop(1, '#3b82f6');

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth, height);
      }

      requestAnimationFrame(render);
    };

    render();
  }
}
