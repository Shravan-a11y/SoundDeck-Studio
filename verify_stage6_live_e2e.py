import json
import httpx
import sys

def main():
    print("=" * 60)
    print("SoundDeck Studio - Stage 6 Live End-to-End Verification")
    print("=" * 60)

    # 1. Verify Frontend Server
    frontend_url = "http://localhost:5173"
    print(f"\n[1] Checking React Vite Frontend at {frontend_url}...")
    try:
        r = httpx.get(frontend_url, timeout=5.0)
        print(f"    Frontend HTTP Status: {r.status_code}")
        assert r.status_code == 200
        assert "<title>SoundDeck Studio</title>" in r.text or "vite" in r.text.lower()
        print("    Frontend successfully responding with HTML bundle.")
    except Exception as e:
        print(f"    Frontend check failed: {e}")
        return False

    # 2. Verify AI Status Endpoint (via FastAPI backend directly and via Vite proxy)
    backend_url = "http://127.0.0.1:8000"
    print(f"\n[2] Checking AI Status Endpoint at {backend_url}/api/ai/status...")
    try:
        r = httpx.get(f"{backend_url}/api/ai/status", timeout=5.0)
        print(f"    Status code: {r.status_code}")
        ai_status = r.json()
        print(f"    AI Status Response: {json.dumps(ai_status, indent=2)}")
        assert ai_status.get("status") == "connected"
        assert ai_status.get("configured_model") == "qwen3:1.7b"
        assert ai_status.get("model_available") is True
        print("    AI Status is connected with local Ollama qwen3:1.7b model.")
    except Exception as e:
        print(f"    AI Status check failed: {e}")
        return False

    # Also check via Vite proxy: http://127.0.0.1:5173/api/ai/status
    print(f"\n[2b] Checking AI Status through Vite Reverse Proxy at {frontend_url}/api/ai/status...")
    try:
        r = httpx.get(f"{frontend_url}/api/ai/status", timeout=5.0)
        print(f"    Proxy Status code: {r.status_code}")
        assert r.status_code == 200
        assert r.json().get("status") == "connected"
        print("    Vite reverse proxy to FastAPI is functioning correctly.")
    except Exception as e:
        print(f"    Vite proxy check failed: {e}")
        return False

    # 3. Submit a Natural-Language Playlist Request to Live Backend
    prompt = "Create a calm indie playlist for late-night studying. Include acoustic tracks, start with Lord Huron, and avoid repeating artists."
    payload = {
        "prompt": prompt,
        "limit": 10,
        "max_per_artist": 1,
        "diversity_weight": 0.2
    }
    print(f"\n[3] Submitting live playlist curation request...")
    print(f"    Prompt: \"{prompt}\"")
    print(f"    Requested limit: 10, max_per_artist: 1")

    try:
        curate_res = httpx.post(
            f"{backend_url}/api/studio/curate",
            json=payload,
            timeout=120.0
        )
        print(f"    Curation HTTP Status: {curate_res.status_code}")
        if curate_res.status_code != 200:
            print(f"    Error detail: {curate_res.text}")
            return False

        data = curate_res.json()
        playlist_id = data.get("playlist_id")
        interpreted = data.get("interpreted_request", {})
        tracks = data.get("tracks", [])
        analytics = data.get("analytics", {})
        summary = data.get("summary", {})

        print(f"\n[4] Verified Curation Response:")
        print(f"    Playlist ID: {playlist_id}")
        print(f"    Interpreted Seed Artist: {interpreted.get('seed_artist')}")
        print(f"    Interpreted Seed Track: {interpreted.get('seed_track')}")
        print(f"    Interpreted Genres: {interpreted.get('target_genres')}")
        print(f"    Interpreted Moods: {interpreted.get('target_moods')}")
        print(f"    Total Tracks Returned: {len(tracks)}")

        print("\n[5] Tracklist Sample (Top 3):")
        for t in tracks[:3]:
            print(f"    #{t.get('ranking_position')} - {t.get('title')} by {t.get('artist')} "
                  f"[Score: {t.get('sounddeck_score')}]")
            print(f"       Explanation: {t.get('explanation')}")

        print("\n[6] Analytics Summary:")
        print(f"    Total Tracks: {analytics.get('total_tracks')}")
        print(f"    Unique Artists: {analytics.get('unique_artists')}")
        print(f"    Repetition Ratio: {analytics.get('repetition_ratio')}")
        print(f"    Metadata Coverage: {analytics.get('metadata_coverage')}")
        print(f"    Mean Recommendation Score: {analytics.get('average_recommendation_score')}")
        print(f"    Genre Distribution: {analytics.get('genre_distribution')}")
        print(f"    Mood Distribution: {analytics.get('mood_distribution')}")
        print(f"    Unmet Constraints: {summary.get('unmet_constraints')}")

        # 7. Export the generated playlist to CSV
        print("\n[7] Exporting playlist to CSV via POST /api/studio/export.csv...")
        export_payload = {
            "playlist_id": playlist_id,
            "tracks": tracks
        }

        # Also inject a formula injection test track to verify protection on live export
        export_payload["tracks"].append({
            "ranking_position": len(tracks) + 1,
            "title": "=cmd|' /C calc'!A0",
            "artist": "+DDE(\"cmd\";\"/C calc\";\"!A0\")",
            "album": "@SUM(1+1)",
            "sounddeck_score": 0.999,
            "relevance_score": 0.999,
            "diversity_adjustment": 0.0,
            "genres": ["folk"],
            "moods": ["calm"],
            "explanation": "-2+3*cmd|' /C calc'!A0"
        })

        export_res = httpx.post(
            f"{backend_url}/api/studio/export.csv",
            json=export_payload,
            timeout=10.0
        )
        print(f"    Export HTTP Status: {export_res.status_code}")
        assert export_res.status_code == 200
        assert "text/csv" in export_res.headers.get("content-type", "")

        csv_text = export_res.text
        lines = [line.strip() for line in csv_text.strip().split("\n") if line.strip()]
        header = lines[0]
        print(f"    CSV Header: {header}")
        assert "Position" in header
        assert "Track Title" in header
        assert "Artist" in header
        assert "Final Recommendation Score" in header
        assert "Explanation" in header

        with open("stage6_exported_playlist.csv", "w", encoding="utf-8") as f:
            f.write(csv_text)
        print("    Saved exported CSV to stage6_exported_playlist.csv")

        print(f"    Total CSV Rows (including header): {len(lines)}")
        print("\n[8] Inspecting CSV Rows:")
        for idx, line in enumerate(lines[:5]):
            print(f"    Row {idx}: {line}")

        # Check sanitization of the formula injected test row
        last_row = lines[-1]
        print(f"\n    Formula-Injected Test Row in CSV: {last_row}")
        # Ensure '=' was sanitized with leading quote or tick
        assert "'=cmd" in last_row or "\"'=cmd" in last_row
        assert "'+DDE" in last_row or "\"'+DDE" in last_row
        assert "'@SUM" in last_row or "\"'@SUM" in last_row
        assert "'-2+3" in last_row or "\"'-2+3" in last_row
        print("    [PASS] CSV formula injection protection verified: leading '=','+','-','@' escaped with single tick.")

        print("\n" + "=" * 60)
        print("STAGE 6 LIVE END-TO-END VERIFICATION: SUCCESS!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"    Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
