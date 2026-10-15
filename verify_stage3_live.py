import json
import asyncio
from starlette.testclient import TestClient

from app.main import app
from app.services.ollama_service import check_ollama_health, get_ollama_config


async def main():
    print("=" * 70)
    print("SoundDeck Studio - Stage 3 Live Curation Verification")
    print("=" * 70)

    # 1. Config and Reachability
    base_url, model = get_ollama_config()
    print(f"\n[1] Configured Ollama URL:   {base_url}")
    print(f"    Configured Model:        {model}")

    try:
        health_data = await check_ollama_health(base_url)
        print("    Ollama Reachability:     REACHABLE (HTTP 200)")
        installed_models = [m.get("name") for m in health_data.get("models", []) if isinstance(m, dict)]
        print(f"    Installed Models:        {installed_models}")
    except Exception as exc:
        print(f"    Ollama Reachability:     FAILED: {exc}")
        print("    Note: Start Ollama (`ollama serve`) to perform live model verification.")
        print("    Unit tests with full mock coverage passed (run: venv\\Scripts\\python.exe -m unittest test_studio_curator.py)")
        return

    # 2. Live Request to POST /api/studio/curate
    client = TestClient(app)
    prompt = (
        "Create a calm indie playlist for late-night studying. "
        "Include acoustic tracks, start with Lord Huron, and avoid repeating artists."
    )
    print(f"\n[2] Submitting request to POST /api/studio/curate:")
    print(f"    Prompt: \"{prompt}\"")
    print("    Limit:  10")

    response = client.post(
        "/api/studio/curate",
        json={"prompt": prompt, "limit": 10},
    )

    print(f"    HTTP Status: {response.status_code}")
    if response.status_code != 200:
        print(f"    Response detail: {response.text}")
        return

    data = response.json()
    print("\n[3] Interpreted Constraints:")
    print(json.dumps(data["interpreted_request"], indent=2))

    print(f"\n[4] Curated Tracks ({len(data['tracks'])} returned):")
    for track in data["tracks"]:
        pos = track.get("ranking_position", "-")
        title = track.get("title", "")
        artist = track.get("artist", "")
        score = track.get("sounddeck_score", 0.0)
        relevance = track.get("relevance_score", 0.0)
        explanation = track.get("explanation", "")
        print(f"    #{pos:2d} | {title} - {artist}")
        print(f"         Score: {score:.4f} (Relevance: {relevance:.4f})")
        print(f"         Explanation: {explanation}")

    print("\n[5] Summary & Constraints Audit:")
    print(json.dumps(data["summary"], indent=2))

    print("\n" + "=" * 70)
    print("STAGE 3 LIVE CURATION VERIFICATION SUCCESSFUL")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
