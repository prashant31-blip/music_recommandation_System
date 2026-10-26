/**
 * VIBENEST AI - CANVAS AUDIO RADAR / SPIDER CHART (COLORFUL LIGHT THEME)
 */

export class AudioRadarChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    this.labels = [
      'Energy',
      'Valence',
      'Danceability',
      'Acousticness',
      'Tempo',
      'Loudness'
    ];
    
    this.seedValues = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
    this.compareValues = null;
    
    this.initResize();
  }

  initResize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || 340) * dpr;
    this.canvas.height = (rect.height || 260) * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = rect.width || 340;
    this.height = rect.height || 260;
  }

  normalizeTrackFeatures(track) {
    if (!track) return [0, 0, 0, 0, 0, 0];
    
    // Normalize tempo (typical 60 - 180 BPM)
    const tempoNorm = Math.min(1.0, Math.max(0.0, ((track.tempo || 120) - 50) / 140));
    
    // Normalize loudness (-60 to 0 dB, typical -20 to -3)
    const loudnessNorm = Math.min(1.0, Math.max(0.0, ((track.loudness || -10) + 30) / 30));

    return [
      track.energy || 0.0,
      track.valence || 0.0,
      track.danceability || 0.0,
      track.acousticness || 0.0,
      tempoNorm,
      loudnessNorm
    ];
  }

  updateData(seedTrack, compareTrack = null) {
    this.seedValues = this.normalizeTrackFeatures(seedTrack);
    this.compareValues = compareTrack ? this.normalizeTrackFeatures(compareTrack) : null;
    this.draw();
  }

  draw() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const centerX = this.width / 2;
    const centerY = this.height / 2;
    const radius = Math.min(centerX, centerY) - 36;
    const sides = this.labels.length;
    const angleStep = (Math.PI * 2) / sides;

    ctx.clearRect(0, 0, this.width, this.height);

    // 1. Draw concentric background webs
    const levels = 4;
    for (let l = 1; l <= levels; l++) {
      const r = (radius / levels) * l;
      ctx.beginPath();
      for (let i = 0; i < sides; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * r;
        const y = centerY + Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.16)';
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    // 2. Draw radiating spokes and high-contrast labels
    ctx.font = 'bold 11px Plus Jakarta Sans, sans-serif';
    ctx.fillStyle = '#334155';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < sides; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      // Spoke line
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(203, 213, 225, 0.8)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label text offset
      const labelX = centerX + Math.cos(angle) * (radius + 20);
      const labelY = centerY + Math.sin(angle) * (radius + 14);
      ctx.fillText(this.labels[i], labelX, labelY);
    }

    // 3. Draw Comparison Polygon (if available) in Electric Azure Blue
    if (this.compareValues) {
      this.drawPolygon(
        this.compareValues,
        'rgba(59, 130, 246, 0.25)',
        '#3b82f6',
        centerX,
        centerY,
        radius,
        angleStep
      );
    }

    // 4. Draw Seed Track Polygon in Radiant Rose Pink
    this.drawPolygon(
      this.seedValues,
      'rgba(236, 72, 153, 0.30)',
      '#ec4899',
      centerX,
      centerY,
      radius,
      angleStep
    );
  }

  drawPolygon(values, fillColor, strokeColor, cx, cy, radius, angleStep) {
    const ctx = this.ctx;
    ctx.beginPath();

    for (let i = 0; i < values.length; i++) {
      const val = Math.max(0.05, Math.min(1.0, values[i]));
      const angle = i * angleStep - Math.PI / 2;
      const x = cx + Math.cos(angle) * (radius * val);
      const y = cy + Math.sin(angle) * (radius * val);

      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }

    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.shadowColor = strokeColor;
    ctx.shadowBlur = 6;
    ctx.stroke();
    ctx.shadowBlur = 0; // reset

    // Draw vertex dots
    for (let i = 0; i < values.length; i++) {
      const val = Math.max(0.05, Math.min(1.0, values[i]));
      const angle = i * angleStep - Math.PI / 2;
      const x = cx + Math.cos(angle) * (radius * val);
      const y = cy + Math.sin(angle) * (radius * val);

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}
