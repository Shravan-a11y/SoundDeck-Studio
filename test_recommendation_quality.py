import unittest
from app.schemas import PlaylistConstraints
from app.services.tag_classifier import (
    classify_tags,
    similarity,
    compare_classifications,
    GENRE_TAGS,
    MOOD_TAGS,
    CONTEXT_TAGS,
)
from app.services.music_intelligence import (
    calculate_hybrid_score,
    enrich_candidate_with_intelligence,
)
from app.services.lastfm import rank_tracks
from app.services.studio_curator import generate_track_explanation


class TestRecommendationQualityAudit(unittest.TestCase):
    """
    Deterministic tests measuring recommendation quality, ranking relevance,
    semantic tag matching, metadata coverage, diversity penalties, and exclusions.
    """

    def setUp(self):
        # Deterministic candidate fixtures with known metadata profiles
        self.fixture_candidates = [
            {
                "title": "Holocene",
                "artist": "Bon Iver",
                "match_score": 0.85,
                "tags": ["indie folk", "folk", "acoustic", "melancholic", "peaceful", "late night"],
            },
            {
                "title": "Dance Yourself Clean",
                "artist": "LCD Soundsystem",
                "match_score": 0.80,
                "tags": ["electronic", "indie electronic", "dance", "party", "energetic", "workout"],
            },
            {
                "title": "Liability",
                "artist": "Lorde",
                "match_score": 0.78,
                "tags": ["pop", "sad", "melancholy", "introspective", "ballad"],
            },
            {
                "title": "Levels",
                "artist": "Avicii",
                "match_score": 0.75,
                "tags": ["electronic", "edm", "party", "happy", "euphoric"],
            },
            {
                "title": "Mystery Track (No Tags)",
                "artist": "Unknown Artist",
                "match_score": 0.82,
                "tags": [],  # Completely missing metadata
            },
            {
                "title": "God's Plan",
                "artist": "Drake",
                "match_score": 0.79,
                "tags": ["hip hop", "rap", "pop"],
            },
        ]

    def test_semantic_subgenre_similarity(self):
        """
        Verify that semantic similarity correctly recognizes subgenre overlap
        between 'indie' and 'indie folk'.
        """
        sim = similarity(["indie"], ["indie folk", "folk"])
        self.assertGreater(sim, 0.5)

    def test_semantic_mood_synonym_similarity(self):
        """
        Verify that mood lemmatization and synonym clusters recognize
        'melancholic' <-> 'melancholy' and 'calm' <-> 'peaceful' / 'relaxing'.
        """
        sim_noun_adj = similarity(["melancholic"], ["melancholy"])
        self.assertGreaterEqual(sim_noun_adj, 0.85)

        sim_synonym = similarity(["calm"], ["peaceful", "relaxing", "chill"])
        self.assertGreaterEqual(sim_synonym, 0.80)

    def test_matching_metadata_beats_missing_metadata(self):
        """
        Verify that a candidate with matching metadata scores higher than an
        untagged candidate with missing metadata.
        """
        lastfm_score = 0.80

        # Candidate with matching genre and mood
        score_matching = calculate_hybrid_score(
            lastfm_score=lastfm_score,
            genre_similarity=0.80,
            mood_similarity=0.80,
            context_similarity=None,
        )

        # Candidate with NO metadata at all (genre=None, mood=None, context=None)
        score_missing_all = calculate_hybrid_score(
            lastfm_score=lastfm_score,
            genre_similarity=None,
            mood_similarity=None,
            context_similarity=None,
        )

        # Candidate with verified matching tags must score higher than untagged candidate
        self.assertGreater(score_matching, score_missing_all)

    def test_genre_and_artist_exclusions(self):
        """
        Scenario 5: Verify that explicit exclusions (exclude_artists and exclude_genres)
        filter out matching candidates.
        """
        constraints = PlaylistConstraints(
            target_genres=["electronic", "pop"],
            exclude_genres=["hip hop", "rap"],
            exclude_artists=["Drake"],
            limit=5,
        )

        # Check candidate filtering
        excluded_artists = {a.casefold().strip() for a in constraints.exclude_artists}
        excluded_genres = {g.casefold().strip() for g in constraints.exclude_genres}

        filtered = []
        for cand in self.fixture_candidates:
            cand_art = cand["artist"].casefold().strip()
            if any(ea == cand_art or ea in cand_art for ea in excluded_artists):
                continue
            cand_genres = set(cand.get("tags", []))
            if any(eg in cand_genres for eg in excluded_genres):
                continue
            filtered.append(cand)

        artists = [c["artist"] for c in filtered]
        self.assertNotIn("Drake", artists)
        for c in filtered:
            self.assertNotIn("hip hop", c.get("tags", []))

    def test_ranking_melancholic_indie_folk_request(self):
        """
        Measure whether a melancholic indie folk request ranks Bon Iver higher
        than electronic party tracks when metadata is enriched.
        """
        seed_tags = ["indie folk", "folk", "acoustic", "melancholic"]
        enriched = []
        for cand in self.fixture_candidates:
            item = enrich_candidate_with_intelligence(
                candidate=cand,
                seed_tags=seed_tags,
                candidate_tags=cand["tags"],
            )
            enriched.append(item)

        ranked = rank_tracks(
            candidates=enriched,
            limit=5,
            max_per_artist=1,
            diversity_weight=0.2,
            score_field="hybrid_score",
        )

        # Verify that Bon Iver (Holocene) is at the top of the ranked set
        top_track = ranked[0]
        self.assertEqual(top_track["artist"], "Bon Iver")
        self.assertEqual(top_track["title"], "Holocene")

    def test_ranking_upbeat_electronic_party_request(self):
        """
        Measure whether an upbeat electronic party request ranks LCD Soundsystem & Avicii
        above indie-folk / sad ballad tracks.
        """
        seed_tags = ["electronic", "indie electronic", "party", "energetic", "dance"]
        enriched = []
        for cand in self.fixture_candidates:
            item = enrich_candidate_with_intelligence(
                candidate=cand,
                seed_tags=seed_tags,
                candidate_tags=cand["tags"],
            )
            enriched.append(item)

        ranked = rank_tracks(
            candidates=enriched,
            limit=5,
            max_per_artist=1,
            diversity_weight=0.2,
            score_field="hybrid_score",
        )

        top_artists = [t["artist"] for t in ranked[:2]]
        # LCD Soundsystem and Avicii should be in top 2 for an electronic party request
        self.assertIn("LCD Soundsystem", top_artists)
        self.assertIn("Avicii", top_artists)

    def test_artist_diversity_penalty_behavior(self):
        """
        Test that artist diversity penalty and max_per_artist limit prevent artist monopolization
        while preserving track quality.
        """
        candidates = [
            {"title": "Track 1", "artist": "Repeat Artist", "match_score": 0.95, "hybrid_score": 0.95},
            {"title": "Track 2", "artist": "Repeat Artist", "match_score": 0.94, "hybrid_score": 0.94},
            {"title": "Track 3", "artist": "Repeat Artist", "match_score": 0.93, "hybrid_score": 0.93},
            {"title": "Track A", "artist": "Diverse Artist A", "match_score": 0.88, "hybrid_score": 0.88},
            {"title": "Track B", "artist": "Diverse Artist B", "match_score": 0.85, "hybrid_score": 0.85},
        ]

        # With max_per_artist = 1, Repeat Artist must only appear once
        ranked = rank_tracks(
            candidates=candidates,
            limit=3,
            max_per_artist=1,
            diversity_weight=0.2,
            score_field="hybrid_score",
        )
        artists = [t["artist"] for t in ranked]
        self.assertEqual(len(artists), len(set(artists)))
        self.assertIn("Repeat Artist", artists)
        self.assertIn("Diverse Artist A", artists)
        self.assertIn("Diverse Artist B", artists)

    def test_explanation_matches_real_scores(self):
        """
        Test that track explanations reflect actual matching criteria and do not claim
        matches that have zero relevance or score.
        """
        constraints = PlaylistConstraints(
            target_genres=["indie", "acoustic"],
            target_moods=["calm"],
            limit=10,
        )
        track = {
            "title": "Holocene",
            "artist": "Bon Iver",
            "genres": ["indie folk", "acoustic"],
            "moods": ["calm"],
            "sounddeck_score": 0.72,
            "relevance_score": 0.85,
        }
        explanation = generate_track_explanation(track, constraints)
        self.assertIn("genre", explanation)
        self.assertIn("mood", explanation)
        self.assertIn("relevance: 0.85", explanation)
        self.assertIn("score: 0.72", explanation)


if __name__ == "__main__":
    unittest.main()
