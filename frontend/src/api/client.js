/**
 * SoundDeck Studio Frontend API Client
 * Interfaces with FastAPI backend endpoints:
 * - GET  /api/ai/status
 * - POST /api/studio/curate
 * - POST /api/studio/export.csv
 */

const API_BASE = '/api';

export async function fetchAiStatus() {
  try {
    const res = await fetch(`${API_BASE}/ai/status`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    return {
      status: 'disconnected',
      error: err.message || 'Could not reach SoundDeck backend.',
    };
  }
}

export async function curatePlaylist({ prompt, limit, maxPerArtist, diversityWeight }) {
  const payload = {
    prompt: prompt.trim(),
    ...(limit ? { limit: Number(limit) } : {}),
    ...(maxPerArtist ? { max_per_artist: Number(maxPerArtist) } : {}),
    ...(diversityWeight !== undefined ? { diversity_weight: Number(diversityWeight) } : {}),
  };

  const res = await fetch(`${API_BASE}/studio/curate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const detail = data?.detail || `Curation failed with status ${res.status}`;
    const err = new Error(detail);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }

  return data;
}

export async function exportPlaylistCsv({ playlistId, tracks }) {
  const payload = {
    playlist_id: playlistId || 'sounddeck-playlist',
    tracks: tracks || [],
  };

  const res = await fetch(`${API_BASE}/studio/export.csv`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorMsg = `Export failed with HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson?.detail) errorMsg = errJson.detail;
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }

  // Extract filename from Content-Disposition header if available
  let filename = `${playlistId || 'sounddeck-playlist'}.csv`;
  const disposition = res.headers.get('content-disposition');
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/i);
    if (match && match[1]) {
      filename = match[1].trim();
    }
  }

  const blob = await res.blob();
  return { blob, filename };
}
