# SoundDeck Studio

**SoundDeck Studio** is a local AI-assisted music curation workstation designed for independent DJs, event curators, and music organizers. It combines prompt interpretation powered by a locally hosted open-weight large language model (**Qwen 1.7B** via **Ollama**) with a deterministic, hybrid music recommendation engine, artist-diversity ranking, playlist analytics, and secure CSV export.

---

## 1. Product Overview

Creating cohesive, thematic playlists for live events, radio sets, or venue atmospheres usually requires hours of manual track selection or reliance on commercial black-box algorithms. Commercial recommendation systems frequently favor mainstream label tracks, suffer from excessive artist repetition, and offer zero insight into why a track was recommended.

SoundDeck Studio provides an open, transparent alternative:
- Natural-language playlist specifications are parsed by a local open-weight LLM into validated structured constraints.
- Candidate tracks are retrieved using MusicBrainz and Last.fm catalog metadata.
- A deterministic hybrid scoring engine ranks candidates using acoustic similarity, genre alignment, and mood profile matching.
- An artist-diversity penalty prevents artist monopolization.
- The resulting playlist is presented with transparent explanations, a diversity and repetition analytics audit, and spreadsheet-safe CSV export.

---

## 2. Target Users and Problem

| Target User | Pain Point | SoundDeck Studio Solution |
| :--- | :--- | :--- |
| **Independent DJs** | Need thematic sets matching specific vibes without repeating artists. | Explicit artist-diversity controls (`max_per_artist`, `diversity_weight`) and clear ranking explanations. |
| **Event / Venue Curators** | Commercial streaming algorithms lack transparency and produce repetitive loops. | Deterministic hybrid scoring and an automated diversity audit (repetition ratio, metadata coverage). |
| **Privacy-Conscious Creators** | Hesitant to send private set notes or creative prompts to commercial cloud LLMs. | Natural-language reasoning executes entirely on localhost using Ollama (`qwen3:1.7b`). |

---

## 3. Features Implemented

The following features are **fully implemented and verified**:

- **Local Natural-Language Constraint Parsing**: Translates freeform DJ prompts into validated Pydantic schemas (`PlaylistConstraints`) using local Ollama inference (`POST /api/ai/parse-playlist-request`).
- **Live AI Health Monitoring**: Probes the local Ollama daemon for status, model availability, and installed models (`GET /api/ai/status`).
- **MusicBrainz & Last.fm Metadata Retrieval**: Queries MusicBrainz for recording and artist disambiguation; queries Last.fm for similar tracks and tag taxonomies with local SQLite caching.
- **Hybrid Recommendation Scoring**:
  $$\text{Score} = 0.60 \cdot S_{\text{lastfm}} + 0.20 \cdot S_{\text{genre}} + 0.15 \cdot S_{\text{mood}} + 0.05 \cdot S_{\text{context}}$$
- **Artist-Diversity Ranking**: Applies a configurable penalty ($\text{penalty} = \text{diversity\_weight} \cdot \text{count}$) to artists with multiple tracks and enforces a strict `max_per_artist` cutoff.
- **Explainable Recommendations**: Generates human-readable explanations for every selected track based on matching tags, seeds, and relevance scores.
- **Catalog Constraint Auditing**: Unmet constraints (e.g. unavailable mood tags, insufficient catalog candidates to meet requested track count without violating artist diversity) are explicitly reported in API responses and UI alerts.
- **Deterministic Playlist Analytics**: Computes track count, unique artists, repetition ratio, metadata coverage, average recommendation score, duplicate counts, and genre/mood distributions (`POST /api/studio/curate`).
- **Spreadsheet-Safe CSV Export**: Exports tracklists to CSV with protection against spreadsheet formula injection (CWE-1236) by escaping leading dangerous characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes (`POST /api/studio/export.csv`).
- **Modern Responsive Frontend**: Built with React 19, Vite, Tailwind CSS, and Lucide React. Includes real-time AI status monitoring, parameter sliders, responsive tracklists, tabbed analytics dashboards, and direct CSV download.

---

## 4. Architecture

```mermaid
graph TD
    UI[React 19 + Vite Frontend\nlocalhost:5173] -->|HTTP / Reverse Proxy| API[FastAPI Backend\nlocalhost:8000]

    subgraph "Local Offline Inference"
        API -->|REST API :11434| Ollama[Ollama Server\nqwen3:1.7b]
    end

    subgraph "Music Intelligence & Catalog"
        API -->|Search & Disambiguation| MB[MusicBrainz API\n(Online)]
        API -->|Similar Tracks & Tags| LFM[Last.fm API\n(Online)]
        API <-->|Cached Metadata| Cache[(SQLite Cache\ndata/music_metadata.sqlite3)]
    end

    subgraph "Core Recommendation Pipeline"
        Engine[Hybrid Scoring Engine\n0.60 Acoustic / 0.20 Genre / 0.15 Mood]
        DivRank[Artist Diversity Ranker\nmax_per_artist & penalty]
        Analytics[Playlist Analytics Service\nRepetition & Distribution Audit]
        Export[CSV Export Sanitizer\nCWE-1236 Protection]
    end

    API --> Engine
    Engine --> DivRank
    DivRank --> Analytics
    DivRank --> Export
```

> [!NOTE]
> **Data Processing Note:** While LLM prompt interpretation executes 100% locally on localhost via Ollama, track metadata retrieval and similarity lookups require an active internet connection to communicate with the MusicBrainz and Last.fm public APIs (unless queries hit the local SQLite cache).

---

## 5. Technology Stack

- **Backend Framework:** FastAPI 0.143+, Uvicorn, Python 3.11+
- **Local AI Engine:** Ollama with `qwen3:1.7b` (Q4_K_M GGUF, 2.0B parameters)
- **Data Validation:** Pydantic v2
- **HTTP Client:** HTTPX (async & sync)
- **Local Cache:** Python standard `sqlite3`
- **Frontend Framework:** React 19, Vite 8
- **Styling:** Tailwind CSS v4, Lucide React icons
- **Security:** Spreadsheet formula sanitization (CWE-1236), CORS middleware, path-safe filename sanitization

---

## 6. How the Local AI Model is Used

SoundDeck Studio utilizes the open-weight **Qwen 1.7B** (`qwen3:1.7b`) model via Ollama's `/api/chat` endpoint.

1. **Structured Extraction:** The user's natural-language prompt is injected into a strict system prompt instructing the model to return raw JSON adhering to `PlaylistConstraints`.
2. **Deterministic Fallback:** If the local model returns markdown code blocks or conversational text, the parser strips markdown fences and extracts the valid JSON object.
3. **Pydantic Validation:** The extracted JSON is validated through Pydantic to ensure constraints such as `limit` ($\le 50$), `max_per_artist` ($\ge 1$), and `diversity_weight` ($0.0 \dots 1.0$) are within bounds.
4. **Zero Cloud Telemetry:** No user prompts, DJ notes, or playlist concepts are transmitted to third-party AI APIs.

---

## 7. Installation Prerequisites

Before installing, ensure the following are installed on your system:
- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Version 3.11 or later
- **Node.js:** Version 18 or later (with `npm`)
- **Ollama:** Installed from [ollama.com](https://ollama.com)
- **Last.fm API Key:** A free API account from [last.fm/api](https://www.last.fm/api)

---

## 8. Windows PowerShell Setup

Open Windows PowerShell and clone/navigate to the project directory:

```powershell
cd C:\Users\shrav\Desktop\Shravan\MLH

# 1. Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create .env configuration
Copy-Item .env.example .env
```

Edit `.env` to supply your Last.fm API credentials and configuration:

```ini
LASTFM_API_KEY=your_lastfm_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b
```

---

## 9. Ollama Model Setup

1. Start the Ollama server (in a dedicated terminal or as a service):
   ```powershell
   ollama serve
   ```
2. Pull the Qwen 1.7B open-weight model:
   ```powershell
   ollama pull qwen3:1.7b
   ```
3. Verify the model is present:
   ```powershell
   ollama list
   ```

---

## 10. Backend Startup

With your virtual environment activated:

```powershell
# Start the FastAPI backend on port 8000
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify backend health in another terminal:
```powershell
curl.exe -s http://127.0.0.1:8000/api/ai/status
```
Expected output:
```json
{
  "status": "connected",
  "base_url": "http://127.0.0.1:11434",
  "configured_model": "qwen3:1.7b",
  "model_available": true,
  "installed_models": ["qwen3:1.7b"]
}
```

---

## 11. Frontend Startup

In a separate terminal, install dependencies and start the Vite dev server:

```powershell
cd frontend
npm install
npm run dev
```

The frontend will run at: **`http://localhost:5173/`**
The Vite server automatically proxies `/api/*` calls to the FastAPI backend at `http://127.0.0.1:8000`.

To build the production frontend bundle:
```powershell
npm run build
```

---

## 12. Testing Instructions

SoundDeck Studio includes comprehensive automated test suites covering unit logic, error resilience, and live end-to-end flows.

### Running Regression and Unit Tests
```powershell
# Run all 55 unit tests
.\venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
```

Test coverage includes:
- `test_ollama_service.py` (21 tests): Parsing, schema validation, connection failure (503), timeout (504), missing model (404), invalid JSON (502).
- `test_studio_curator.py` (16 tests): Candidate retrieval, tag enrichment, diversity constraints, explanations, unmet constraint auditing.
- `test_analytics.py` (10 tests): Repetition ratios, unique artist counting, metadata coverage, edge cases with empty or 1-track playlists.
- `test_studio_export.py` (8 tests): CSV formatting, header alignment, formula injection protection against `=`, `+`, `-`, `@`, `\t`, `\r`.
- Component tests: `test_hybrid_scoring.py`, `test_tag_classifier.py`, `test_cache.py`, `test_music_intelligence.py`, `test_lastfm.py`.

### Running Live End-to-End Verification
With Ollama and the backend running, execute:
```powershell
.\venv\Scripts\python.exe verify_stage6_live_e2e.py
```
This tests Vite frontend accessibility, backend AI status, live natural-language curation with Ollama, track ranking, analytics calculation, and CSV export with live injection validation.

---

## 13. API Endpoint Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service health and version check. |
| `GET` | `/api/ai/status` | Real-time status of the local Ollama daemon and configured model. |
| `POST` | `/api/ai/parse-playlist-request` | Parses a natural-language prompt into validated `PlaylistConstraints`. |
| `POST` | `/api/studio/curate` | End-to-end curation: prompt parsing, candidate retrieval, hybrid scoring, diversity ranking, explanations, and analytics. |
| `POST` | `/api/studio/export.csv` | Exports playlist tracks to a sanitized CSV file with formula-injection escaping. |
| `GET` | `/api/playlists/generate` | Legacy endpoint for direct seed-based recommendation generation. |

---

## 14. Known Limitations

1. **Catalog Candidate Counts vs. Strict Diversity:** If a user requests a high track limit (e.g., 25) with `max_per_artist: 1`, but the seed track's similar pool on Last.fm only contains 15 distinct artists, SoundDeck Studio returns 15 tracks and explicitly reports the unmet count. It will not fabricate fake tracks or silently relax diversity limits.
2. **Metadata Tag Sparsity:** Some niche or indie tracks on Last.fm lack community tags for mood or context. When tags are missing, `metadata_coverage` reflects the gap, and the system relies on acoustic similarity and artist-level tags.
3. **External Network Requirement:** While LLM reasoning runs locally on your machine, track discovery relies on the availability of MusicBrainz and Last.fm public APIs. If external networks are offline and the cache is cold, candidates cannot be fetched.

---

## 15. Security and Configuration Guidance

- **Formula Injection Mitigation (CWE-1236):** All user-controllable text written to CSV exports is checked for leading formula characters (`=`, `+`, `-`, `@`, tab, carriage return). Any matching cell is automatically prefixed with a single quote (`'`), preventing malicious spreadsheet execution when opened in Microsoft Excel, LibreOffice Calc, or Google Sheets.
- **Header Injection & Path Traversal:** The `playlist_id` parameter used in the `Content-Disposition` attachment filename is strictly filtered to alphanumeric characters, hyphens, and underscores.
- **Credentials & API Keys:** The Last.fm API key must be kept in `.env` and never committed to Git. Root `.gitignore` ignores `.env`, `*.log`, `data/*.sqlite3`, `*.csv`, `venv/`, and `frontend/dist/`.

---

## 16. Future Improvements

The following items are planned for future major releases:
- **Audio Waveform & BPM Analysis:** Integration of local audio feature analysis (key, tempo/BPM, danceability) for seamless DJ transitions.
- **Direct Export to DJ Software:** Exporting setlists directly to M3U8, Rekordbox XML, and Serato crate formats.
- **Completely Offline Catalog Mode:** Pre-indexing a local MP3/FLAC music library using SQLite/Chromadb, eliminating reliance on external web APIs.
- **Multi-Seed Blending:** Supporting multiple simultaneous seed tracks and artists with weighted interpolation.

---

## License

*A formal open-source license decision (e.g. MIT, Apache 2.0, GPLv3) remains pending project owner review.*
