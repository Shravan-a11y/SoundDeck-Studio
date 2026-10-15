import unittest

from app.services.analytics import calculate_playlist_analytics


class TestPlaylistAnalytics(unittest.TestCase):
    """Focused test suite for SoundDeck Studio Stage 4 Playlist Analytics."""

    # 1. Empty playlist
    def test_empty_playlist(self):
        analytics = calculate_playlist_analytics([])
        self.assertEqual(analytics["total_tracks"], 0)
        self.assertEqual(analytics["unique_artists"], 0)
        self.assertEqual(analytics["artist_distribution"], {})
        self.assertEqual(analytics["repetition_ratio"], 0.0)
        self.assertEqual(analytics["genre_distribution"], {})
        self.assertEqual(analytics["mood_distribution"], {})
        self.assertEqual(analytics["duplicate_track_count"], 0)
        self.assertEqual(analytics["metadata_coverage"], 0.0)
        self.assertIsNone(analytics["average_hybrid_score"])
        self.assertIsNone(analytics["average_recommendation_score"])
        self.assertEqual(analytics["unmet_constraints"], [])
        self.assertTrue(len(analytics["notes"]) > 0)

    # 2. Multiple unique artists
    def test_multiple_unique_artists(self):
        tracks = [
            {"title": "Track 1", "artist": "Artist Alpha"},
            {"title": "Track 2", "artist": "Artist Beta"},
            {"title": "Track 3", "artist": "Artist Gamma"},
        ]
        analytics = calculate_playlist_analytics(tracks)
        self.assertEqual(analytics["total_tracks"], 3)
        self.assertEqual(analytics["unique_artists"], 3)
        self.assertEqual(analytics["repetition_ratio"], 0.0)
        self.assertEqual(analytics["artist_distribution"]["Artist Alpha"], 1)
        self.assertEqual(analytics["artist_distribution"]["Artist Beta"], 1)
        self.assertEqual(analytics["artist_distribution"]["Artist Gamma"], 1)

    # 3. Repeated artists
    def test_repeated_artists(self):
        # Sequence: Alpha (new), Beta (new), Alpha (repeat 1), Gamma (new), Alpha (repeat 2)
        tracks = [
            {"title": "Song 1", "artist": "Lord Huron"},
            {"title": "Song 2", "artist": "Bon Iver"},
            {"title": "Song 3", "artist": "Lord Huron"},
            {"title": "Song 4", "artist": "Fleet Foxes"},
            {"title": "Song 5", "artist": "Lord Huron"},
        ]
        analytics = calculate_playlist_analytics(tracks)
        self.assertEqual(analytics["total_tracks"], 5)
        self.assertEqual(analytics["unique_artists"], 3)
        self.assertEqual(analytics["artist_distribution"]["Lord Huron"], 3)
        # 2 repeated encounters out of 5 tracks = 2/5 = 0.4
        self.assertEqual(analytics["repetition_ratio"], 0.4)

    # 4. Missing artist names
    def test_missing_artist_names(self):
        tracks = [
            {"title": "Track 1", "artist": "Known Artist"},
            {"title": "Track 2", "artist": None},
            {"title": "Track 3", "artist": "   "},
            {"title": "Track 4", "artist": ""},
        ]
        analytics = calculate_playlist_analytics(tracks)
        self.assertEqual(analytics["total_tracks"], 4)
        self.assertEqual(analytics["unique_artists"], 1)
        self.assertIn("[Unknown Artist]", analytics["artist_distribution"])
        self.assertEqual(analytics["artist_distribution"]["[Unknown Artist]"], 3)
        self.assertEqual(analytics["artist_distribution"]["Known Artist"], 1)
        # Missing artists must not produce false repetition
        self.assertEqual(analytics["repetition_ratio"], 0.0)

    # 5. Genre distribution
    def test_genre_distribution(self):
        tracks = [
            {"title": "Song A", "artist": "Band 1", "genres": ["indie", "acoustic"]},
            {"title": "Song B", "artist": "Band 2", "genres": ["indie", "rock"]},
            {"title": "Song C", "artist": "Band 3", "genres": ["acoustic"]},
        ]
        analytics = calculate_playlist_analytics(tracks)
        dist = analytics["genre_distribution"]
        self.assertEqual(dist["indie"], 2)
        self.assertEqual(dist["acoustic"], 2)
        self.assertEqual(dist["rock"], 1)

    # 6. Mood distribution
    def test_mood_distribution(self):
        tracks = [
            {"title": "Song 1", "artist": "Band 1", "moods": ["calm", "relaxing"]},
            {"title": "Song 2", "artist": "Band 2", "moods": ["calm"]},
            {"title": "Song 3", "artist": "Band 3", "moods": ["sad"]},
        ]
        analytics = calculate_playlist_analytics(tracks)
        dist = analytics["mood_distribution"]
        self.assertEqual(dist["calm"], 2)
        self.assertEqual(dist["relaxing"], 1)
        self.assertEqual(dist["sad"], 1)

    # 7. Missing tags
    def test_missing_tags(self):
        # 1 track with metadata, 2 tracks without any tags
        tracks = [
            {"title": "Song 1", "artist": "Band 1", "tags": ["indie", "calm"], "genres": ["indie"], "moods": ["calm"]},
            {"title": "Song 2", "artist": "Band 2", "tags": [], "genres": [], "moods": []},
            {"title": "Song 3", "artist": "Band 3"},
        ]
        analytics = calculate_playlist_analytics(tracks)
        self.assertEqual(analytics["metadata_coverage"], round(1 / 3, 4))
        self.assertEqual(analytics["genre_distribution"], {"indie": 1})
        self.assertEqual(analytics["mood_distribution"], {"calm": 1})

    # 8. Duplicate tracks
    def test_duplicate_tracks(self):
        tracks = [
            {"title": "The Night We Met", "artist": "Lord Huron"},
            {"title": "the night we met ", "artist": "lord huron"},
            {"title": "Ends of the Earth", "artist": "Lord Huron"},
        ]
        analytics = calculate_playlist_analytics(tracks)
        self.assertEqual(analytics["total_tracks"], 3)
        self.assertEqual(analytics["duplicate_track_count"], 1)

    # 9. Missing scoring fields
    def test_missing_scoring_fields(self):
        # Tracks without scoring fields
        tracks_no_scores = [
            {"title": "Song 1", "artist": "Artist 1"},
            {"title": "Song 2", "artist": "Artist 2"},
        ]
        analytics_empty = calculate_playlist_analytics(tracks_no_scores)
        self.assertIsNone(analytics_empty["average_hybrid_score"])
        self.assertIsNone(analytics_empty["average_recommendation_score"])

        # Partial scoring fields
        tracks_partial = [
            {"title": "Song 1", "artist": "Artist 1", "hybrid_score": 0.80, "sounddeck_score": 0.70},
            {"title": "Song 2", "artist": "Artist 2", "hybrid_score": 0.90, "sounddeck_score": None},
            {"title": "Song 3", "artist": "Artist 3", "relevance_score": 0.60},
        ]
        analytics_partial = calculate_playlist_analytics(tracks_partial)
        # hybrid: (0.80 + 0.90) / 2 = 0.85
        self.assertEqual(analytics_partial["average_hybrid_score"], 0.8500)
        # recommendation: sounddeck 0.70, None, relevance fallback 0.60 -> (0.70 + 0.60) / 2 = 0.65
        self.assertEqual(analytics_partial["average_recommendation_score"], 0.6500)

    # 10. Unmet constraints
    def test_unmet_constraints(self):
        unmet = [
            "Requested 20 tracks, but only 5 tracks satisfied constraints.",
            "Target genre 'metal' had no matching tracks in candidate metadata.",
        ]
        analytics = calculate_playlist_analytics([], unmet_constraints=unmet)
        self.assertEqual(analytics["unmet_constraints"], unmet)


if __name__ == "__main__":
    unittest.main()
