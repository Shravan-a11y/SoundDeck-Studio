import json
import asyncio
from starlette.testclient import TestClient

from app.main import app
from app.services.ollama_service import check_ollama_health, get_ollama_config
from app.schemas import PlaylistConstraints


async def main():
    print("=" * 60)
    print("SoundDeck Studio - Stage 2 Integration Verification")
    print("=" * 60)

    # 1. Config and Reachability
    base_url, model = get_ollama_config()
    print(f"\n[1] Configured Ollama URL:   {base_url}")
    print(f"    Configured Model:        {model}")

    try:
        health_data = await check_ollama_health(base_url)
        print("    Ollama Reachability:     REACHABLE (HTTP 200)")
    except Exception as exc:
        print(f"    Ollama Reachability:     FAILED: {exc}")
        return

    # 2. Verify Configured Model Exists
    installed_models = [m.get("name") for m in health_data.get("models", []) if isinstance(m, dict)]
    print(f"    Installed Models:        {installed_models}")
    model_match = any(m == model or m.startswith(f"{model}:") for m in installed_models)
    print(f"[2] Model '{model}' Available: {model_match}")
    if not model_match:
        print(f"    ERROR: Model '{model}' not found in installed models.")
        return

    # 3. Live Request through FastAPI TestClient
    client = TestClient(app)
    prompt = (
        "Create a calm indie playlist for late-night studying. "
        "Use acoustic songs, avoid repeating artists, and start with a track by Lord Huron."
    )
    print(f"\n[3] Submitting prompt to POST /api/ai/parse-playlist-request:")
    print(f"    Prompt: \"{prompt}\"")

    response = client.post(
        "/api/ai/parse-playlist-request",
        json={"prompt": prompt},
    )

    print(f"    HTTP Status: {response.status_code}")
    if response.status_code != 200:
        print(f"    Response text: {response.text}")
        return

    resp_json = response.json()
    print(f"\n[4] Returned Payload from Ollama:")
    print(json.dumps(resp_json, indent=2))

    # 4. Confirm Pydantic validation
    constraints = PlaylistConstraints.model_validate(resp_json["constraints"])
    print(f"\n[5] Schema Validation: PASSED")
    print(f"    Seed Artist:      {constraints.seed_artist}")
    print(f"    Seed Track:       {constraints.seed_track}")
    print(f"    Target Genres:    {constraints.target_genres}")
    print(f"    Target Moods:     {constraints.target_moods}")
    print(f"    Target Contexts:  {constraints.target_contexts}")
    print(f"    Limit:            {constraints.limit}")
    print(f"    Max Per Artist:   {constraints.max_per_artist}")
    print(f"    Diversity Weight: {constraints.diversity_weight}")

    # 5. Test Invalid Request
    print(f"\n[6] Testing Invalid Request (empty prompt):")
    invalid_resp = client.post("/api/ai/parse-playlist-request", json={"prompt": ""})
    print(f"    Empty prompt HTTP Status: {invalid_resp.status_code} (Expected 422)")
    assert invalid_resp.status_code == 422, "Expected 422 for empty prompt"

    print("\n" + "=" * 60)
    print("STAGE 2 VERIFICATION SUCCESSFUL")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
