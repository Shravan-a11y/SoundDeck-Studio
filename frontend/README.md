# SoundDeck Studio — Frontend

**SoundDeck Studio** is a local AI-powered music curation application for independent DJs and event organizers.

This frontend is built with:
- **React 19**
- **Vite 8**
- **Tailwind CSS v4** (`@tailwindcss/vite`)
- **Lucide React** for icons

---

## Getting Started

### 1. Start the Backend API Server
Ensure the Python virtual environment is activated and the FastAPI server is running:

```powershell
# From the project root
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the Frontend Development Server
In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server will start at `http://localhost:5173`. Requests to `/api/*` are automatically proxied to `http://127.0.0.1:8000`.

### 3. Build for Production
To build the optimized production bundle:

```powershell
cd frontend
npm run build
```

---

## Features

- **Live Ollama Status Monitor**: Real-time status indicator showing connectivity to the local `qwen3:1.7b` model.
- **Natural-Language Prompt Workspace**: Rich textarea with preset chips, parameter controls (track count, max per artist, diversity weight), and duplicate submission prevention.
- **Ordered Playlist View**: Visual track list displaying positions, titles, artists, albums, genre/mood pills, recommendation scores, relevance, diversity penalties, and Last.fm links.
- **Analytics Dashboard**: Real-time KPI cards (unique artists, repetition ratio, metadata coverage, average scores) and visual distribution meters for genres and moods.
- **CSV Export**: Direct integration with `/api/studio/export.csv` downloading formula-injection-protected CSV files.
