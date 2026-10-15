# SoundDeck Studio — 90-Second Demonstration Script

**Target Audience:** Independent DJs, event organizers, music curators, and hackathon judges.
**Estimated Run Time:** ~90 seconds
**Prerequisites Running:** Ollama daemon (`qwen3:1.7b`), FastAPI backend (`http://localhost:8000`), Vite frontend (`http://localhost:5173`).

---

### [0:00 – 0:15] Introduction & Target User
* **Visual:** Browser opened to SoundDeck Studio at `http://localhost:5173`. Clean dark-mode interface with purple/cyan accents.
* **Speaker:**
  > "Independent DJs and venue curators often spend hours assembling thematic setlists. Commercial streaming algorithms are black boxes that prioritize sponsored tracks and repeat the same major-label artists.
  >
  > Welcome to **SoundDeck Studio**—a local AI-powered music curation workstation that turns natural-language creative prompts into transparent, diverse, production-ready playlists."

---

### [0:15 – 0:25] Local AI Status & Privacy
* **Visual:** Cursor points to the top-right header status indicator showing **"Ollama Connected (qwen3:1.7b)"** with a glowing green dot.
* **Speaker:**
  > "Notice our live AI status pill in the header. SoundDeck Studio does not send your creative briefs to cloud providers. It runs inference locally using the open-weight **Qwen 1.7B** model via Ollama—keeping your prompts completely private, cost-free, and offline-capable for reasoning."

---

### [0:25 – 0:40] Natural-Language Prompt & Constraint Parsing
* **Visual:** In the prompt textarea, highlight the default prompt:
  *`"Create a calm indie playlist for late-night studying. Include acoustic tracks, start with Lord Huron, and avoid repeating artists."`*
  Show the sliders set to: Track Limit = 10, Max Per Artist = 1, Diversity Weight = 0.20.
  Click **"Generate Playlist"**.
* **Speaker:**
  > "We input a natural-language description. When we click Generate, Qwen 1.7B parses this prompt into structured constraints: extracting the seed artist Lord Huron, desired genres like indie and acoustic, the calm mood, and a strict limit of one track per artist."

---

### [0:40 – 0:55] Ranked Tracklist & Transparent Explanations
* **Visual:** The tracklist loads with 10 ranked tracks. Scroll through the top tracks (#1 Lord Huron, #2 Gregory Alan Isakov, #3 Milo Greene, #4 The Paper Kites). Highlight the badge with SoundDeck score and the explanation text.
* **Speaker:**
  > "Here is our curated tracklist. Instead of an unexplainable list, SoundDeck scores each candidate using a deterministic hybrid engine: 60% acoustic similarity from Last.fm, 20% genre taxonomy, and 15% mood profile, penalized by our artist diversity penalty.
  >
  > Each track includes a plain-English explanation explaining exactly why it was selected."

---

### [0:55 – 1:15] Playlist Analytics & Diversity Audit
* **Visual:** Click on the **"Analytics Dashboard"** tab. Show the 4 KPI cards (10 Tracks, 10 Unique Artists, 0.0% Repetition Ratio, 100% Metadata Coverage), the Genre distribution bars, and the Catalog Constraint Notes.
* **Speaker:**
  > "DJs cannot afford unintended repetition. Switching to the Analytics Dashboard, we see our diversity audit: 10 unique artists across 10 tracks, giving us a 0% repetition ratio.
  >
  > Furthermore, SoundDeck is honest: if catalog metadata lacks specific tags—such as 'calm'—it clearly reports them under Catalog Constraint Notes rather than fabricating fake data."

---

### [1:15 – 1:25] Secure CSV Export (Formula Injection Protection)
* **Visual:** Click the **"Export CSV"** button in the header or top card. The browser downloads `sd-xxxx.csv`. A toast notification confirms export. Open the CSV in a text viewer showing columns `Position, Track Title, Artist, ..., Final Recommendation Score, Explanation`.
* **Speaker:**
  > "With one click, we export the setlist directly to CSV for ingestion into DJ software or spreadsheet organizers. Every text field is sanitized against spreadsheet formula injection (CWE-1236), preventing malicious payload execution."

---

### [1:25 – 1:30] Conclusion: Why Local Open-Weight AI Matters
* **Visual:** Zoom out to show the full dashboard and footer ("Powered by Ollama, Qwen 1.7B, Last.fm & MusicBrainz").
* **Speaker:**
  > "SoundDeck Studio combines local open-weight AI reasoning with deterministic music intelligence—giving artists full transparency, strict diversity controls, and total ownership over their curation workflow. Thank you!"
