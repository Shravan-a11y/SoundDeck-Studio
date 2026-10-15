import unittest
from unittest.mock import patch, AsyncMock
import httpx
from starlette.testclient import TestClient

from app.main import app
from app.schemas import PlaylistConstraints, StudioCurateRequest
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaResponseValidationError,
)
from app.services.studio_curator import (
    curate_playlist,
    extract_classifier_tags,
    generate_track_explanation,
)
from app.services.tag_classifier import GENRE_TAGS, MOOD_TAGS, CONTEXT_TAGS


class TestStudioCuratorUnit(unittest.TestCase):
    """Unit tests for helper utilities in studio_curator."""

    def test_extract_classifier_tags_variations(self):
        # Test multi-word and stemmed tag extraction
        genres = extract_classifier_tags(["indie-rock", "acoustic tracks"], GENRE_TAGS)
        self.assertIn("indie rock", genres)
        self.assertIn("acoustic", genres)

        moods = extract_classifier_tags(["very calm", "relaxing vibe"], MOOD_TAGS)
        self.assertIn("calm", moods)
        self.assertIn("relaxing", moods)

        contexts = extract_classifier_tags(["late-night studying", "workout session"], CONTEXT_TAGS)
        self.assertIn("late night", contexts)
        self.assertIn("study", contexts)
        self.assertIn("workout", contexts)

    def test_generate_track_explanation(self):
        constraints = PlaylistConstraints(
            seed_artist="Lord Huron",
            target_genres=["indie"],
            target_moods=["calm"],
            target_contexts=["study"],
        )
        track = {
            "title": "Ends of the Earth",
            "artist": "Lord Huron",
            "genres": ["indie"],
            "moods": ["calm"],
            "contexts": ["study"],
            "sounddeck_score": 0.88,
            "relevance_score": 0.92,
            "diversity_adjustment": 0.04,
        }
        explanation = generate_track_explanation(track, constraints)
        self.assertIn("genre 'indie'", explanation)
        self.assertIn("mood 'calm'", explanation)
        self.assertIn("context 'study'", explanation)
        self.assertIn("diversity penalty applied", explanation)


class TestStudioCuratorIntegration(unittest.TestCase):
    """Integration and scenario tests for SoundDeck Studio Stage 3."""

    def setUp(self):
        self.client = TestClient(app)
        self.artist_tags_patch = patch("app.services.studio_curator.get_artist_tags", new_callable=AsyncMock)
        self.mock_artist_tags = self.artist_tags_patch.start()
        self.mock_artist_tags.return_value = []

    def tearDown(self):
        self.artist_tags_patch.stop()

    # -------------------------------------------------------------------------
    # 1. A successful curation request
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_successful_curation_request(self, mock_parse, mock_similar, mock_tags):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            seed_track="The Night We Met",
            target_genres=["indie", "acoustic"],
            target_moods=["calm"],
            target_contexts=["study"],
            limit=5,
            max_per_artist=2,
            diversity_weight=0.2,
        )

        mock_similar.return_value = [
            {"title": "Meet Me in the Woods", "artist": "Lord Huron", "match_score": 0.9, "url": "http://last.fm/1"},
            {"title": "Rivers and Roads", "artist": "The Head and the Heart", "match_score": 0.85, "url": "http://last.fm/2"},
            {"title": "Holocene", "artist": "Bon Iver", "match_score": 0.8, "url": "http://last.fm/3"},
            {"title": "White Winter Hymnal", "artist": "Fleet Foxes", "match_score": 0.75, "url": "http://last.fm/4"},
            {"title": "Bloom", "artist": "The Paper Kites", "match_score": 0.7, "url": "http://last.fm/5"},
        ]

        def tag_side_effect(artist, title):
            mapping = {
                ("Lord Huron", "The Night We Met"): ["indie", "acoustic", "calm", "study"],
                ("Lord Huron", "Meet Me in the Woods"): ["indie", "acoustic", "calm"],
                ("The Head and the Heart", "Rivers and Roads"): ["indie", "acoustic", "calm", "study"],
                ("Bon Iver", "Holocene"): ["indie", "acoustic", "calm"],
                ("Fleet Foxes", "White Winter Hymnal"): ["indie", "folk"],
                ("The Paper Kites", "Bloom"): ["indie", "acoustic", "calm"],
            }
            return mapping.get((artist, title), ["indie"])

        mock_tags.side_effect = tag_side_effect

        response = self.client.post(
            "/api/studio/curate",
            json={
                "prompt": "Create a calm indie acoustic playlist for studying starting with Lord Huron",
                "limit": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["playlist_id"].startswith("sd-"))
        self.assertEqual(data["interpreted_request"]["seed_artist"], "Lord Huron")
        self.assertEqual(len(data["tracks"]), 5)
        self.assertEqual(data["summary"]["track_count"], 5)
        self.assertGreaterEqual(data["summary"]["unique_artist_count"], 3)

        # Confirm analytics is attached to curation response
        self.assertIn("analytics", data)
        self.assertEqual(data["analytics"]["total_tracks"], 5)
        self.assertGreaterEqual(data["analytics"]["unique_artists"], 3)
        self.assertIn("repetition_ratio", data["analytics"])
        self.assertIn("genre_distribution", data["analytics"])
        self.assertIn("mood_distribution", data["analytics"])
        self.assertIn("metadata_coverage", data["analytics"])

        # Confirm each track has scores, ranking, and explanation
        for i, track in enumerate(data["tracks"], start=1):
            self.assertEqual(track["ranking_position"], i)
            self.assertIn("sounddeck_score", track)
            self.assertIn("relevance_score", track)
            self.assertIn("explanation", track)
            self.assertTrue(len(track["explanation"]) > 0)

    # -------------------------------------------------------------------------
    # 2. Genre constraints influencing ranking
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_genre_constraints_influencing_ranking(self, mock_parse, mock_similar, mock_tags):
        # Two tracks with identical Last.fm score (0.80)
        candidates = [
            {"title": "Track Indie", "artist": "Indie Band", "match_score": 0.80, "url": None},
            {"title": "Track Rock", "artist": "Rock Band", "match_score": 0.80, "url": None},
        ]
        mock_similar.return_value = candidates

        def tag_side_effect(artist, title):
            if artist == "Indie Band":
                return ["indie"]
            elif artist == "Rock Band":
                return ["rock"]
            return []

        mock_tags.side_effect = tag_side_effect

        # When asking for "indie"
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Test Seed",
            seed_track="Test Track",
            target_genres=["indie"],
            limit=5,
        )
        resp1 = self.client.post("/api/studio/curate", json={"prompt": "indie music"})
        tracks1 = resp1.json()["tracks"]
        indie_pos = next(t["ranking_position"] for t in tracks1 if t["artist"] == "Indie Band")
        rock_pos = next(t["ranking_position"] for t in tracks1 if t["artist"] == "Rock Band")
        self.assertLess(indie_pos, rock_pos, "Indie track should rank ahead of Rock track when indie is requested")

        # When asking for "rock"
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Test Seed",
            seed_track="Test Track",
            target_genres=["rock"],
            limit=5,
        )
        resp2 = self.client.post("/api/studio/curate", json={"prompt": "rock music"})
        tracks2 = resp2.json()["tracks"]
        indie_pos2 = next(t["ranking_position"] for t in tracks2 if t["artist"] == "Indie Band")
        rock_pos2 = next(t["ranking_position"] for t in tracks2 if t["artist"] == "Rock Band")
        self.assertLess(rock_pos2, indie_pos2, "Rock track should rank ahead of Indie track when rock is requested")

    # -------------------------------------------------------------------------
    # 3. Mood constraints influencing ranking
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_mood_constraints_influencing_ranking(self, mock_parse, mock_similar, mock_tags):
        mock_similar.return_value = [
            {"title": "Calm Song", "artist": "Calm Artist", "match_score": 0.80, "url": None},
            {"title": "Angry Song", "artist": "Angry Artist", "match_score": 0.80, "url": None},
        ]

        def tag_side_effect(artist, title):
            if artist == "Calm Artist":
                return ["calm"]
            elif artist == "Angry Artist":
                return ["aggressive", "angry"]
            return []

        mock_tags.side_effect = tag_side_effect

        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Test Seed",
            seed_track="Test Track",
            target_moods=["calm"],
            limit=5,
        )

        resp = self.client.post("/api/studio/curate", json={"prompt": "calm music"})
        tracks = resp.json()["tracks"]
        calm_pos = next(t["ranking_position"] for t in tracks if t["artist"] == "Calm Artist")
        angry_pos = next(t["ranking_position"] for t in tracks if t["artist"] == "Angry Artist")
        self.assertLess(calm_pos, angry_pos, "Calm track should rank ahead of Angry track when calm is requested")

    # -------------------------------------------------------------------------
    # 4. Seed artist handling
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.resolve_seed_track_for_artist", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_seed_artist_handling(self, mock_parse, mock_resolve, mock_similar, mock_tags):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            seed_track=None,
            target_genres=["indie"],
            limit=5,
        )
        mock_resolve.return_value = "The Night We Met"
        mock_similar.return_value = [
            {"title": "Ends of the Earth", "artist": "Lord Huron", "match_score": 0.85, "url": None},
            {"title": "Rivers and Roads", "artist": "The Head and the Heart", "match_score": 0.80, "url": None},
        ]
        mock_tags.return_value = ["indie"]

        resp = self.client.post("/api/studio/curate", json={"prompt": "Start with Lord Huron"})
        self.assertEqual(resp.status_code, 200)
        tracks = resp.json()["tracks"]
        self.assertTrue(len(tracks) >= 1)
        # Seed track should be included and ranked
        artists_in_playlist = [t["artist"] for t in tracks]
        self.assertIn("Lord Huron", artists_in_playlist)
        self.assertEqual(tracks[0]["artist"], "Lord Huron")

    # -------------------------------------------------------------------------
    # 5. Artist-diversity enforcement
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_artist_diversity_enforcement(self, mock_parse, mock_similar, mock_tags):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Artist A",
            seed_track="Track 0",
            target_genres=["indie"],
            limit=5,
            max_per_artist=2,
            diversity_weight=0.5,
        )
        # 5 tracks by Artist A, 2 by Artist B
        mock_similar.return_value = [
            {"title": "Track A1", "artist": "Artist A", "match_score": 0.95, "url": None},
            {"title": "Track A2", "artist": "Artist A", "match_score": 0.94, "url": None},
            {"title": "Track A3", "artist": "Artist A", "match_score": 0.93, "url": None},
            {"title": "Track A4", "artist": "Artist A", "match_score": 0.92, "url": None},
            {"title": "Track B1", "artist": "Artist B", "match_score": 0.70, "url": None},
            {"title": "Track B2", "artist": "Artist B", "match_score": 0.69, "url": None},
        ]
        mock_tags.return_value = ["indie"]

        resp = self.client.post("/api/studio/curate", json={"prompt": "Diverse indie", "limit": 5})
        self.assertEqual(resp.status_code, 200)
        tracks = resp.json()["tracks"]

        artist_a_tracks = [t for t in tracks if t["artist"] == "Artist A"]
        self.assertLessEqual(len(artist_a_tracks), 2, "Should not exceed max_per_artist=2")

        # Second track of Artist A should receive a diversity penalty
        if len(artist_a_tracks) >= 2:
            self.assertGreater(artist_a_tracks[1]["diversity_adjustment"], 0.0)

    # -------------------------------------------------------------------------
    # 6. Duplicate prevention
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_duplicate_prevention(self, mock_parse, mock_similar, mock_tags):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            seed_track="The Night We Met",
            limit=5,
        )
        # Duplicates with differing casing and whitespace
        mock_similar.return_value = [
            {"title": "The Night We Met", "artist": "Lord Huron", "match_score": 1.0, "url": None},
            {"title": "the night we met ", "artist": "lord huron", "match_score": 0.95, "url": None},
            {"title": "Ends of the Earth", "artist": "Lord Huron", "match_score": 0.85, "url": None},
            {"title": "ENDS OF THE EARTH", "artist": "Lord Huron", "match_score": 0.84, "url": None},
            {"title": "Rivers and Roads", "artist": "The Head and the Heart", "match_score": 0.80, "url": None},
        ]
        mock_tags.return_value = ["indie"]

        resp = self.client.post("/api/studio/curate", json={"prompt": "No duplicates"})
        self.assertEqual(resp.status_code, 200)
        tracks = resp.json()["tracks"]

        track_keys = [(t["artist"].casefold(), t["title"].casefold()) for t in tracks]
        self.assertEqual(len(track_keys), len(set(track_keys)), "All tracks in playlist must be unique")

    # -------------------------------------------------------------------------
    # 7. Empty candidate results
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.retrieve_candidates", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_empty_candidate_results(self, mock_parse, mock_retrieve):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="NonExistentArtistXYZ123",
            limit=10,
        )
        mock_retrieve.return_value = ([], None, ["No catalog tracks found."])

        resp = self.client.post("/api/studio/curate", json={"prompt": "Unknown artist"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["tracks"], [])
        self.assertEqual(data["summary"]["track_count"], 0)
        self.assertTrue(len(data["summary"]["unmet_constraints"]) > 0)

    # -------------------------------------------------------------------------
    # 8. Unavailable Ollama
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_unavailable_ollama(self, mock_parse):
        # Connection error -> 503
        mock_parse.side_effect = OllamaConnectionError("Connection refused to Ollama")
        resp1 = self.client.post("/api/studio/curate", json={"prompt": "Any prompt"})
        self.assertEqual(resp1.status_code, 503)
        self.assertIn("Local AI service unavailable", resp1.json()["detail"])

        # Timeout error -> 504
        mock_parse.side_effect = OllamaTimeoutError("Timed out waiting for Ollama")
        resp2 = self.client.post("/api/studio/curate", json={"prompt": "Any prompt"})
        self.assertEqual(resp2.status_code, 504)
        self.assertIn("timed out", resp2.json()["detail"])

        # Validation error -> 502
        mock_parse.side_effect = OllamaResponseValidationError("Bad json")
        resp3 = self.client.post("/api/studio/curate", json={"prompt": "Any prompt"})
        self.assertEqual(resp3.status_code, 502)

    # -------------------------------------------------------------------------
    # 9. Unavailable music metadata service
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_unavailable_music_metadata_service(self, mock_parse, mock_similar):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            seed_track="The Night We Met",
            limit=10,
        )
        mock_similar.side_effect = httpx.HTTPError("Last.fm unreachable")

        resp = self.client.post("/api/studio/curate", json={"prompt": "Lord Huron playlist"})
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Unable to retrieve music metadata", resp.json()["detail"])

    # -------------------------------------------------------------------------
    # 10. Unmet constraints
    # -------------------------------------------------------------------------
    @patch("app.services.studio_curator.get_track_tags", new_callable=AsyncMock)
    @patch("app.services.studio_curator.get_similar_tracks", new_callable=AsyncMock)
    @patch("app.services.studio_curator.parse_playlist_request", new_callable=AsyncMock)
    def test_unmet_constraints_reporting(self, mock_parse, mock_similar, mock_tags):
        # User requests limit=20, genre="metal", mood="aggressive", but only 2 calm acoustic tracks exist
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Acoustic Folk Band",
            seed_track="Acoustic Song",
            target_genres=["metal"],
            target_moods=["aggressive"],
            target_contexts=["workout"],
            limit=20,
        )
        mock_similar.return_value = [
            {"title": "Track 1", "artist": "Acoustic Folk Band", "match_score": 0.8, "url": None},
        ]
        mock_tags.return_value = ["acoustic", "calm"]

        resp = self.client.post("/api/studio/curate", json={"prompt": "Heavy metal workout", "limit": 20})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        unmet = data["summary"]["unmet_constraints"]

        # Track count limit could not be met
        self.assertTrue(any("Requested 20 tracks" in u for u in unmet))
        # Genre metal was not in catalog metadata
        self.assertTrue(any("metal" in u for u in unmet))
        # Mood aggressive was not in catalog metadata
        self.assertTrue(any("aggressive" in u for u in unmet))

    # -------------------------------------------------------------------------
    # 11. Existing endpoint backward compatibility
    # -------------------------------------------------------------------------
    def test_root_endpoint_compatibility(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "SoundDeck Studio")

    @patch("app.main.check_ollama_health", new_callable=AsyncMock)
    def test_ai_status_endpoint_compatibility(self, mock_health):
        mock_health.return_value = {"models": [{"name": "qwen3:1.7b"}]}
        resp = self.client.get("/api/ai/status")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "connected")

    @patch("app.main.parse_playlist_request", new_callable=AsyncMock)
    def test_parse_playlist_request_endpoint_compatibility(self, mock_parse):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            target_genres=["indie"],
            limit=20,
        )
        resp = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Indie songs like Lord Huron"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["constraints"]["seed_artist"], "Lord Huron")

    @patch("app.main.get_track_tags", new_callable=AsyncMock)
    @patch("app.main.get_similar_tracks", new_callable=AsyncMock)
    def test_generate_playlist_legacy_endpoint_compatibility(self, mock_similar, mock_tags):
        mock_tags.return_value = ["indie", "folk"]
        mock_similar.return_value = [
            {"title": "Ends of the Earth", "artist": "Lord Huron", "match_score": 0.85, "url": None},
            {"title": "Rivers and Roads", "artist": "The Head and the Heart", "match_score": 0.80, "url": None},
        ]
        resp = self.client.get(
            "/api/playlists/generate",
            params={"artist": "Lord Huron", "track": "The Night We Met", "limit": 2},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("seed", data)
        self.assertIn("playlist", data)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["method"], "SoundDeck genre, mood, context, relevance and diversity ranking")
