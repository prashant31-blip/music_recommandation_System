/**
 * VIBENEST AI - MAIN APPLICATION CONTROLLER
 */

import { api } from './api.js?v=2.3';
import { MusicPlayer } from './player.js?v=2.3';
import { AudioRadarChart } from './radar.js?v=2.3';

class VibeNestApp {
  constructor() {
    this.player = new MusicPlayer();
    this.radar = new AudioRadarChart('canvas-radar');

    this.currentSeedTrack = null;
    this.activeGenre = '';
    this.activeSearchQuery = '';

    this.initElements();
    this.bindEvents();
    this.loadInitialData();
  }

  // ============================================================
  // INITIALIZE HTML ELEMENTS
  // ============================================================

  initElements() {

    // Navigation
    this.navButtons = document.querySelectorAll('.nav-item button');
    this.viewSections = document.querySelectorAll('.view-section');

    // Header Search
    this.searchInput = document.getElementById('main-search-input');
    this.searchDropdown = document.getElementById('search-dropdown');
    this.genreSelect = document.getElementById('genre-select');

    // Discover View
    this.moodChips = document.querySelectorAll('.mood-chip');
    this.trendingGrid = document.getElementById('trending-tracks-grid');
    this.recommendedGrid = document.getElementById('recommended-tracks-grid');

    // Radar View
    this.radarSeedTitle = document.getElementById('radar-seed-title');
    this.radarSeedArtist = document.getElementById('radar-seed-artist');
    this.radarSeedCover = document.getElementById('radar-seed-cover');

    this.radarSimilarGrid = document.getElementById('radar-similar-grid');

    this.featurePills = {
      energy: document.getElementById('feat-energy'),
      valence: document.getElementById('feat-valence'),
      dance: document.getElementById('feat-dance'),
      tempo: document.getElementById('feat-tempo')
    };

    // Mood Lab View
    this.presetTiles = document.querySelectorAll('.preset-tile');

    this.sliderValence = document.getElementById('slider-valence');
    this.sliderEnergy = document.getElementById('slider-energy');
    this.sliderDance = document.getElementById('slider-dance');
    this.sliderAcoustic = document.getElementById('slider-acoustic');
    this.sliderTempo = document.getElementById('slider-tempo');

    this.btnTriggerMood = document.getElementById('btn-trigger-mood');
    this.moodResultsGrid = document.getElementById('mood-results-grid');

    // Library View
    this.libraryGrid = document.getElementById('library-tracks-grid');

    this.tasteLikesCount = document.getElementById('taste-likes-count');
    this.tasteDominantGenre = document.getElementById('taste-dominant-genre');
    this.tasteEnergyVal = document.getElementById('taste-energy-val');
    this.tasteValenceVal = document.getElementById('taste-valence-val');
  }

  // ============================================================
  // EVENT HANDLERS
  // ============================================================

  bindEvents() {

    // ----------------------------------------------------------
    // Navigation
    // ----------------------------------------------------------

    this.navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.dataset.view;
        this.switchView(targetView);
      });
    });

    // ----------------------------------------------------------
    // Search Bar
    // ----------------------------------------------------------

    let searchDebounce = null;

    this.searchInput.addEventListener('input', (e) => {

      clearTimeout(searchDebounce);

      const query = e.target.value.trim();

      if (!query) {
        this.searchDropdown.classList.remove('show');
        return;
      }

      searchDebounce = setTimeout(() => {
        this.handleSearch(query);
      }, 220);
    });

    // ----------------------------------------------------------
    // Close Search Dropdown
    // ----------------------------------------------------------

    document.addEventListener('click', (e) => {

      if (
        !this.searchInput.contains(e.target) &&
        !this.searchDropdown.contains(e.target)
      ) {
        this.searchDropdown.classList.remove('show');
      }

    });

    // ----------------------------------------------------------
    // Genre Filter
    // ----------------------------------------------------------

    this.genreSelect.addEventListener('change', (e) => {

      this.activeGenre = e.target.value;

      this.loadTrendingTracks();

    });

    // ----------------------------------------------------------
    // Quick Mood Chips
    // ----------------------------------------------------------

    this.moodChips.forEach(chip => {

      chip.addEventListener('click', () => {

        this.moodChips.forEach(c => {
          c.classList.remove('active');
        });

        chip.classList.add('active');

        const mood = chip.dataset.mood;

        this.applyQuickMood(mood);

      });

    });

    // ----------------------------------------------------------
    // Mood Presets
    // ----------------------------------------------------------

    this.presetTiles.forEach(tile => {

      tile.addEventListener('click', () => {

        this.presetTiles.forEach(t => {
          t.classList.remove('active');
        });

        tile.classList.add('active');

        this.applyPresetValues(tile.dataset);

      });

    });

    // ----------------------------------------------------------
    // Mood Slider Updates
    // ----------------------------------------------------------

    const sliders = [

      {
        el: this.sliderValence,
        badge: 'badge-valence',
        format: v => `${Math.round(v * 100)}%`
      },

      {
        el: this.sliderEnergy,
        badge: 'badge-energy',
        format: v => `${Math.round(v * 100)}%`
      },

      {
        el: this.sliderDance,
        badge: 'badge-dance',
        format: v => `${Math.round(v * 100)}%`
      },

      {
        el: this.sliderAcoustic,
        badge: 'badge-acoustic',
        format: v => `${Math.round(v * 100)}%`
      },

      {
        el: this.sliderTempo,
        badge: 'badge-tempo',
        format: v => `${v} BPM`
      }

    ];

    sliders.forEach(s => {

      if (s.el) {

        s.el.addEventListener('input', (e) => {

          const badge = document.getElementById(s.badge);

          if (badge) {
            badge.textContent = s.format(
              parseFloat(e.target.value)
            );
          }

        });

      }

    });

    // ----------------------------------------------------------
    // Mood Recommendation Button
    // ----------------------------------------------------------

    if (this.btnTriggerMood) {

      this.btnTriggerMood.addEventListener(
        'click',
        () => this.fetchMoodRecommendations()
      );

    }

    // ----------------------------------------------------------
    // Like Event
    // ----------------------------------------------------------

    document.addEventListener('like-toggled', () => {

      this.loadUserPersonalizedFeed();
      this.loadLibraryData();

    });

  }

  // ============================================================
  // SWITCH VIEW
  // ============================================================

  switchView(viewName) {

    this.navButtons.forEach(btn => {

      btn.classList.toggle(
        'active',
        btn.dataset.view === viewName
      );

    });

    this.viewSections.forEach(sec => {

      sec.classList.toggle(
        'active',
        sec.id === `view-${viewName}`
      );

    });

    // Load library when opened
    if (viewName === 'library') {

      this.loadLibraryData();

    }

    // Load default radar track
    else if (
      viewName === 'radar' &&
      !this.currentSeedTrack
    ) {

      api.getPopular(1).then(tracks => {

        if (tracks.length > 0) {

          this.selectSeedTrack(tracks[0]);

        }

      }).catch(error => {

        console.error(
          'Unable to load default radar track:',
          error
        );

      });

    }

  }

  // ============================================================
  // INITIAL DATABASE / APPLICATION DATA
  // ============================================================

  async loadInitialData() {

    // ----------------------------------------------------------
    // Check Backend + Database
    // ----------------------------------------------------------

    try {

      const health = await api.checkHealth();

      const statsVal =
        document.querySelector('.sidebar-stats .stats-value');

      const statsSub =
        document.querySelector('.sidebar-stats .stats-sub');

      if (
        health &&
        health.status === 'healthy'
      ) {

        const count =
          health.tracks_indexed ||
          (health.database?.tables?.tracks) ||
          40000;

        if (statsVal) {

          statsVal.innerHTML =
            `<span style="
              display:inline-block;
              width:8px;
              height:8px;
              border-radius:50%;
              background:#10b981;
              box-shadow:0 0 8px rgba(16,185,129,0.6);
              margin-right:6px;
            "></span>
            ${Number(count).toLocaleString()} Tracks`;

        }

        if (statsSub) {

          statsSub.textContent =
            'SQLite Database Connected • Live';

        }

      }

      else if (statsSub) {

        statsSub.textContent =
          'Backend Reconnecting...';

      }

    }

    catch (e) {

      console.warn(
        'Initial health check notice:',
        e
      );

    }

    // ----------------------------------------------------------
    // Load Genres
    // ----------------------------------------------------------

    try {

      const genres = await api.getGenres();

      this.genreSelect.innerHTML =
        '<option value="">All Genres</option>';

      genres.slice(0, 35).forEach(g => {

        const opt =
          document.createElement('option');

        opt.value = g;

        opt.textContent =
          g.charAt(0).toUpperCase() +
          g.slice(1);

        this.genreSelect.appendChild(opt);

      });

    }

    catch (error) {

      console.error(
        'Error loading genres:',
        error
      );

    }

    // ----------------------------------------------------------
    // Load User Likes
    // ----------------------------------------------------------

    try {

      const likes =
        await api.getUserLikes(1);

      likes.forEach(t => {

        this.player.likedTrackIds.add(
          t.track_id
        );

      });

    }

    catch (error) {

      console.error(
        'Error loading user likes:',
        error
      );

    }

    // ----------------------------------------------------------
    // Load Main Views
    // ----------------------------------------------------------

    await this.loadTrendingTracks();

    await this.loadUserPersonalizedFeed();

  }

  // ============================================================
  // TRENDING TRACKS
  // ============================================================

  async loadTrendingTracks() {

    this.trendingGrid.innerHTML =
      '<div class="empty-state">Loading trending hits...</div>';

    try {

      let tracks = [];

      if (this.activeGenre) {

        tracks =
          await api.searchTracks(
            '',
            this.activeGenre,
            12
          );

      }

      else {

        tracks =
          await api.getPopular(12);

      }

      // Resilient fallback if activeGenre yielded 0
      if (!tracks || tracks.length === 0) {
        tracks = await api.getPopular(12);
      }

      this.renderTrackCards(
        tracks,
        this.trendingGrid
      );

    }

    catch (error) {

      console.error(
        'Error loading trending tracks:',
        error
      );

      this.trendingGrid.innerHTML =
        '<div class="empty-state">Unable to load tracks.</div>';

    }

  }

  // ============================================================
  // PERSONALIZED FEED
  // ============================================================

  async loadUserPersonalizedFeed() {

    try {

      let tracks =
        await api.recommendUser(1, 8);

      // If user has no interactions yet or list is empty, display curated ML trending tracks
      if (!tracks || tracks.length === 0) {
        tracks = await api.getPopular(8);
      }

      this.renderTrackCards(
        tracks,
        this.recommendedGrid
      );

    }

    catch (error) {

      console.error(
        'Error loading personalized recommendations:',
        error
      );

    }

  }

  // ============================================================
  // SEARCH
  // ============================================================

  async handleSearch(query) {

    this.activeSearchQuery = query;

    try {

      const tracks =
        await api.searchTracks(
          query,
          '',
          8
        );

      // No results
      if (!tracks || tracks.length === 0) {

        this.searchDropdown.innerHTML =
          `<div style="
            padding:14px;
            text-align:center;
            color:var(--text-muted);
            font-size:0.85rem;
          ">
            No matching tracks found
          </div>`;

        this.searchDropdown.classList.add('show');

        return;
      }

      // Clear previous results
      this.searchDropdown.innerHTML = '';

      // Create search results
      tracks.forEach(track => {

        const item =
          document.createElement('div');

        item.className =
          'search-dropdown-item';

        const cover =
          track.cover_url ||
          'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100&auto=format&fit=crop&q=80';

        item.innerHTML = `
          <img
            src="${cover}"
            alt="cover"
          />

          <div class="search-item-info">

            <div class="search-item-title">
              ${this.escapeHtml(track.track_name)}
            </div>

            <div class="search-item-artist">
              ${this.escapeHtml(track.artists)}
              &bull;
              ${this.escapeHtml(track.track_genre || '')}
            </div>

          </div>
        `;

        // ======================================================
        // IMPORTANT FIX
        // Search result now goes directly to music player
        // ======================================================

        item.addEventListener('click', () => {

          // Close dropdown
          this.searchDropdown.classList.remove('show');

          // Put searched song into player
          // This was missing in the original code.
          this.player.setQueue([track], 0);

          // Also use it as Radar seed
          this.selectSeedTrack(track);

          // Open Radar
          this.switchView('radar');

        });

        this.searchDropdown.appendChild(item);

      });

      this.searchDropdown.classList.add('show');

    }

    catch (error) {

      console.error(
        'Search error:',
        error
      );

      this.searchDropdown.innerHTML =
        `<div style="
          padding:14px;
          text-align:center;
          color:var(--text-muted);
          font-size:0.85rem;
        ">
          Search failed. Please try again.
        </div>`;

      this.searchDropdown.classList.add('show');

    }

  }

  // ============================================================
  // SELECT RADAR SEED TRACK
  // ============================================================

  async selectSeedTrack(track) {

    if (!track) return;

    this.currentSeedTrack = track;

    // Track title
    if (this.radarSeedTitle) {

      this.radarSeedTitle.textContent =
        track.track_name || 'Unknown Track';

    }

    // Artist
    if (this.radarSeedArtist) {

      this.radarSeedArtist.textContent =
        track.artists || 'Unknown Artist';

    }

    // Cover
    const cover =
      track.cover_url ||
      'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80';

    if (this.radarSeedCover) {

      this.radarSeedCover.src = cover;

    }

    // Feature pills
    if (this.featurePills.energy) {

      this.featurePills.energy.textContent =
        `${Math.round((track.energy || 0) * 100)}%`;

    }

    if (this.featurePills.valence) {

      this.featurePills.valence.textContent =
        `${Math.round((track.valence || 0) * 100)}%`;

    }

    if (this.featurePills.dance) {

      this.featurePills.dance.textContent =
        `${Math.round((track.danceability || 0) * 100)}%`;

    }

    if (this.featurePills.tempo) {

      this.featurePills.tempo.textContent =
        `${Math.round(track.tempo || 120)} BPM`;

    }

    // Radar chart
    try {

      this.radar.updateData(
        track,
        null
      );

    }

    catch (error) {

      console.warn(
        'Radar update error:',
        error
      );

    }

    // Similar songs
    if (this.radarSimilarGrid) {

      this.radarSimilarGrid.innerHTML =
        '<div class="empty-state">Computing cosine similarity across 40,000 tracks...</div>';

      try {

        const resp =
          await api.getSimilarTracks(
            track.track_id,
            12
          );

        this.renderTrackCards(
          resp.recommendations || [],
          this.radarSimilarGrid,
          true
        );

      }

      catch (error) {

        console.error(
          'Similar track error:',
          error
        );

        this.radarSimilarGrid.innerHTML =
          '<div class="empty-state">Unable to load similar tracks.</div>';

      }

    }

  }

  // ============================================================
  // QUICK MOOD
  // ============================================================

  applyQuickMood(mood) {

    const presets = {

      workout: {
        valence: 0.85,
        energy: 0.95,
        danceability: 0.85,
        tempo_bpm: 140
      },

      chill: {
        valence: 0.60,
        energy: 0.30,
        danceability: 0.45,
        tempo_bpm: 85
      },

      focus: {
        valence: 0.50,
        energy: 0.35,
        danceability: 0.30,
        tempo_bpm: 95
      },

      party: {
        valence: 0.90,
        energy: 0.90,
        danceability: 0.90,
        tempo_bpm: 128
      },

      lofi: {
        valence: 0.35,
        energy: 0.25,
        danceability: 0.40,
        tempo_bpm: 78
      }

    };

    if (!mood || mood === 'all') {
      this.loadTrendingTracks();
      return;
    }

    const target =
      presets[mood] || presets.chill;

    this.trendingGrid.innerHTML =
      '<div class="empty-state">Filtering by vibe vector...</div>';

    api.recommendMood({
      ...target,
      limit: 12
    })
      .then(tracks => {

        this.renderTrackCards(
          tracks,
          this.trendingGrid
        );

      })
      .catch(error => {

        console.error(
          'Mood recommendation error:',
          error
        );

        this.trendingGrid.innerHTML =
          '<div class="empty-state">Unable to calculate recommendations.</div>';

      });

  }

  // ============================================================
  // MOOD PRESET VALUES
  // ============================================================

  applyPresetValues(data) {

    if (data.valence) {
      this.sliderValence.value =
        data.valence;
    }

    if (data.energy) {
      this.sliderEnergy.value =
        data.energy;
    }

    if (data.dance) {
      this.sliderDance.value =
        data.dance;
    }

    if (data.acoustic) {
      this.sliderAcoustic.value =
        data.acoustic;
    }

    if (data.tempo) {
      this.sliderTempo.value =
        data.tempo;
    }

    // Update badges
    this.sliderValence.dispatchEvent(
      new Event('input')
    );

    this.sliderEnergy.dispatchEvent(
      new Event('input')
    );

    this.sliderDance.dispatchEvent(
      new Event('input')
    );

    this.sliderAcoustic.dispatchEvent(
      new Event('input')
    );

    this.sliderTempo.dispatchEvent(
      new Event('input')
    );

    this.fetchMoodRecommendations();

  }

  // ============================================================
  // MOOD RECOMMENDATIONS
  // ============================================================

  async fetchMoodRecommendations() {

    this.moodResultsGrid.innerHTML =
      '<div class="empty-state">Calculating mood vector distance...</div>';

    const params = {

      valence:
        parseFloat(this.sliderValence.value),

      energy:
        parseFloat(this.sliderEnergy.value),

      danceability:
        parseFloat(this.sliderDance.value),

      acousticness:
        parseFloat(this.sliderAcoustic.value),

      tempo_bpm:
        parseFloat(this.sliderTempo.value),

      limit: 12

    };

    try {

      const tracks =
        await api.recommendMood(params);

      this.renderTrackCards(
        tracks,
        this.moodResultsGrid
      );

    }

    catch (error) {

      console.error(
        'Mood recommendation error:',
        error
      );

      this.moodResultsGrid.innerHTML =
        '<div class="empty-state">Unable to load mood recommendations.</div>';

    }

  }

  // ============================================================
  // LIBRARY
  // ============================================================

  async loadLibraryData() {

    try {

      const likes =
        await api.getUserLikes(1);

      const taste =
        await api.getUserTaste(1);

      if (this.tasteLikesCount) {

        this.tasteLikesCount.textContent =
          likes.length;

      }

      if (this.tasteDominantGenre) {

        this.tasteDominantGenre.textContent =
          (
            taste?.top_genres &&
            taste.top_genres.length > 0
          )
            ? taste.top_genres.join(', ')
            : 'Explore More';

      }

      if (this.tasteEnergyVal) {

        this.tasteEnergyVal.textContent =
          `${Math.round(
            (taste?.energy || 0.5) * 100
          )}%`;

      }

      if (this.tasteValenceVal) {

        this.tasteValenceVal.textContent =
          `${Math.round(
            (taste?.valence || 0.5) * 100
          )}%`;

      }

      // No likes
      if (likes.length === 0) {

        this.libraryGrid.innerHTML = `
          <div
            class="empty-state"
            style="grid-column: 1 / -1;"
          >

            <div class="empty-state-icon">
              💖
            </div>

            <h3>
              No Liked Songs Yet
            </h3>

            <p>
              Click the heart icon on any song
              to save it here and refine your
              taste model.
            </p>

          </div>
        `;

        return;

      }

      this.renderTrackCards(
        likes,
        this.libraryGrid
      );

    }

    catch (error) {

      console.error(
        'Library loading error:',
        error
      );

    }

  }

  // ============================================================
  // RENDER TRACK CARDS
  // ============================================================

  renderTrackCards(
    tracks,
    container,
    isRadarView = false
  ) {

    if (
      !tracks ||
      tracks.length === 0
    ) {

      container.innerHTML =
        '<div class="empty-state" style="grid-column: 1 / -1;">No tracks found matching criteria</div>';

      return;

    }

    container.innerHTML = '';

    tracks.forEach((track, idx) => {

      const card =
        document.createElement('div');

      card.className =
        'track-card';

      const isLiked =
        this.player.likedTrackIds.has(
          track.track_id
        );

      const defaultCover =
        'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80';

      const coverUrl =
        track.cover_url ||
        defaultCover;

      const scoreBadge =
        track.similarity_score

          ? `<span class="card-badge badge-similarity">
              ${track.similarity_score}% Match
             </span>`

          : (
            track.match_score

              ? `<span class="card-badge badge-similarity">
                    ${track.match_score}% Vibe
                   </span>`

              : `<span class="card-badge">
                    ${track.track_genre || 'Pop'}
                   </span>`
          );

      card.innerHTML = `

        <div class="card-cover-wrapper">

          <img
            src="${coverUrl}"
            alt="Album Art"
            class="card-cover-img"
            loading="lazy"
          />

          <button
            class="card-overlay-btn"
            title="Play Now"
          >

            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >

              <path
                d="M8 5v14l11-7z"
              />

            </svg>

          </button>

        </div>

        <div
          class="card-title"
          title="${this.escapeHtml(track.track_name)}"
        >
          ${this.escapeHtml(track.track_name)}
        </div>

        <div
          class="card-artist"
          title="${this.escapeHtml(track.artists)}"
        >
          ${this.escapeHtml(track.artists)}
        </div>

        ${track.vibe_name ? `<div style="font-size:0.73rem; color:#c084fc; font-weight:500; margin: 2px 0 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${this.escapeHtml(track.vibe_name)}">${this.escapeHtml(track.vibe_name)}</div>` : ''}

        <div class="card-footer">

          ${scoreBadge}

          <div class="card-actions">

            <button
              class="btn-icon-sm btn-similar"
              title="Find Similar (Radar)"
            >

              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >

                <circle
                  cx="12"
                  cy="12"
                  r="10"
                />

                <circle
                  cx="12"
                  cy="12"
                  r="6"
                />

                <circle
                  cx="12"
                  cy="12"
                  r="2"
                />

              </svg>

            </button>

            <button
              class="btn-icon-sm btn-like ${isLiked ? 'liked' : ''}"
              title="${isLiked ? 'Unlike' : 'Like'}"
            >

              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="${isLiked ? 'currentColor' : 'none'}"
                stroke="currentColor"
                stroke-width="2"
              >

                <path
                  d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                />

              </svg>

            </button>

          </div>

        </div>
      `;

      // ========================================================
      // PLAY TRACK
      // ========================================================

      const coverWrapper =
        card.querySelector(
          '.card-cover-wrapper'
        );

      coverWrapper.style.cursor =
        'pointer';

      coverWrapper.addEventListener(
        'click',
        () => {

          // Play selected track
          this.player.setQueue(
            tracks,
            idx
          );

        }
      );

      // ========================================================
      // FIND SIMILAR
      // ========================================================

      const similarBtn =
        card.querySelector(
          '.btn-similar'
        );

      similarBtn.addEventListener(
        'click',
        (e) => {

          e.stopPropagation();

          this.selectSeedTrack(track);

          this.switchView('radar');

        }
      );

      // ========================================================
      // LIKE / UNLIKE
      // ========================================================

      const likeBtn =
        card.querySelector(
          '.btn-like'
        );

      likeBtn.addEventListener(
        'click',
        async (e) => {

          e.stopPropagation();

          const currentlyLiked =
            this.player.likedTrackIds.has(
              track.track_id
            );

          try {

            if (currentlyLiked) {

              this.player.likedTrackIds.delete(
                track.track_id
              );

              likeBtn.classList.remove(
                'liked'
              );

              likeBtn
                .querySelector('svg')
                .setAttribute(
                  'fill',
                  'none'
                );

              await api.logInteraction(
                track.track_id,
                'unlike'
              );

            }

            else {

              this.player.likedTrackIds.add(
                track.track_id
              );

              likeBtn.classList.add(
                'liked'
              );

              likeBtn
                .querySelector('svg')
                .setAttribute(
                  'fill',
                  'currentColor'
                );

              await api.logInteraction(
                track.track_id,
                'like'
              );

            }

            document.dispatchEvent(
              new CustomEvent(
                'like-toggled',
                {
                  detail: {
                    track_id:
                      track.track_id
                  }
                }
              )
            );

          }

          catch (error) {

            console.error(
              'Like interaction error:',
              error
            );

          }

        }
      );

      // ========================================================
      // RADAR HOVER
      // ========================================================

      if (isRadarView) {

        card.addEventListener(
          'mouseenter',
          () => {

            if (this.currentSeedTrack) {

              this.radar.updateData(
                this.currentSeedTrack,
                track
              );

            }

          }
        );

        card.addEventListener(
          'mouseleave',
          () => {

            if (this.currentSeedTrack) {

              this.radar.updateData(
                this.currentSeedTrack,
                null
              );

            }

          }
        );

      }

      container.appendChild(card);

    });

  }

  // ============================================================
  // ESCAPE HTML
  // ============================================================

  escapeHtml(str) {

    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

// ============================================================
// START APPLICATION
// ============================================================

document.addEventListener(
  'DOMContentLoaded',
  () => {

    window.app =
      new VibeNestApp();

  }
);