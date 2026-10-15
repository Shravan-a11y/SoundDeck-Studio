import csv
import io
import unittest
from starlette.testclient import TestClient

from app.main import app
from app.services.export import export_playlist_to_csv, sanitize_csv_value, CSV_FIELDNAMES


class TestStudioExport(unittest.TestCase):
    """Focused test suite for SoundDeck Studio Stage 4 CSV Export."""

    def setUp(self):
        self.client = TestClient(app)

    # 1. Successful export
    def test_successful_export(self):
        payload = {
            "playlist_id": "study-vibes-01",
            "tracks": [
                {
                    "ranking_position": 1,
                    "title": "The Night We Met",
                    "artist": "Lord Huron",
                    "album": "Strange Trails",
                    "url": "https://www.last.fm/music/Lord+Huron/_/The+Night+We+Met",
                    "tags": ["indie", "folk", "acoustic"],
                    "genres": ["indie", "folk"],
                    "moods": ["calm"],
                    "contexts": ["study"],
                    "match_score": 1.0,
                    "hybrid_score": 0.925,
                    "diversity_adjustment": 0.0,
                    "sounddeck_score": 0.74,
                    "explanation": "Seed artist match establishing playlist core aesthetic",
                },
                {
                    "ranking_position": 2,
                    "title": "Rivers and Roads",
                    "artist": "The Head and the Heart",
                    "album": "The Head and the Heart",
                    "url": "https://www.last.fm/music/The+Head+and+the+Heart/_/Rivers+and+Roads",
                    "tags": ["indie", "acoustic"],
                    "genres": ["indie"],
                    "moods": ["calm"],
                    "contexts": ["study"],
                    "match_score": 0.85,
                    "hybrid_score": 0.88,
                    "diversity_adjustment": 0.0,
                    "sounddeck_score": 0.704,
                    "explanation": "Matches requested indie genre and calm mood",
                },
            ],
        }

        response = self.client.post("/api/studio/export.csv", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/csv; charset=utf-8")

        reader = list(csv.reader(io.StringIO(response.text)))
        # Header + 2 rows = 3 rows
        self.assertEqual(len(reader), 3)
        self.assertEqual(reader[0], CSV_FIELDNAMES)

        row1 = reader[1]
        self.assertEqual(row1[0], "1")  # Position
        self.assertEqual(row1[1], "The Night We Met")  # Track Title
        self.assertEqual(row1[2], "Lord Huron")  # Artist
        self.assertEqual(row1[3], "Strange Trails")  # Album
        self.assertEqual(row1[9], "1.0000")  # Match Score
        self.assertEqual(row1[10], "0.9250")  # Hybrid Score
        self.assertEqual(row1[12], "0.7400")  # Final Score
        self.assertIn("Seed artist match", row1[13])  # Explanation

    # 2. Empty playlist export
    def test_empty_playlist_export(self):
        payload = {
            "playlist_id": "empty-set",
            "tracks": [],
        }
        response = self.client.post("/api/studio/export.csv", json=payload)
        self.assertEqual(response.status_code, 200)

        reader = list(csv.reader(io.StringIO(response.text)))
        # Exactly 1 row: the header
        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[0], CSV_FIELDNAMES)

    # 3. Fields containing commas and quotation marks
    def test_fields_containing_commas_and_quotes(self):
        tricky_title = 'Love, Loss, and "Memories"'
        tricky_artist = 'Simon, Garfunkel & "Friends"'
        payload = {
            "tracks": [
                {
                    "title": tricky_title,
                    "artist": tricky_artist,
                    "genres": ["indie, alternative", "folk"],
                }
            ]
        }
        response = self.client.post("/api/studio/export.csv", json=payload)
        self.assertEqual(response.status_code, 200)

        reader = list(csv.reader(io.StringIO(response.text)))
        self.assertEqual(len(reader), 2)
        row = reader[1]
        self.assertEqual(row[1], tricky_title)
        self.assertEqual(row[2], tricky_artist)

    # 4. Fields containing newlines
    def test_fields_containing_newlines(self):
        multiline_explanation = "Track 1 summary.\nRecommended for studying.\r\nLate night listening."
        payload = {
            "tracks": [
                {
                    "title": "Ambient Study 1",
                    "artist": "SoundDeck",
                    "explanation": multiline_explanation,
                }
            ]
        }
        response = self.client.post("/api/studio/export.csv", json=payload)
        self.assertEqual(response.status_code, 200)

        reader = list(csv.reader(io.StringIO(response.text)))
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[1][13], multiline_explanation)

    # 5. Formula-injection protection (CWE-1236)
    def test_formula_injection_protection(self):
        dangerous_tracks = [
            {
                "title": "=cmd|' /C calc'!A0",
                "artist": "+12345",
                "album": "@SUM(1+1)",
                "explanation": "-Dangerous Formula",
                "url": "\thttp://injected.com",
            }
        ]
        csv_text = export_playlist_to_csv(dangerous_tracks)

        # In raw CSV, values starting with dangerous formula characters must be prefixed with a single quote
        self.assertIn("'=cmd|' /C calc'!A0", csv_text)
        self.assertIn("'+12345", csv_text)
        self.assertIn("'@SUM(1+1)", csv_text)
        self.assertIn("'-Dangerous Formula", csv_text)

        # Direct unit check on sanitize_csv_value
        self.assertEqual(sanitize_csv_value("=1+1"), "'=1+1")
        self.assertEqual(sanitize_csv_value("+cmd"), "'+cmd")
        self.assertEqual(sanitize_csv_value("@eval"), "'@eval")
        self.assertEqual(sanitize_csv_value("-minus"), "'-minus")
        self.assertEqual(sanitize_csv_value("  =indented"), "'  =indented")
        self.assertEqual(sanitize_csv_value("Safe Title"), "Safe Title")

    # 6. Missing optional fields
    def test_missing_optional_fields(self):
        minimal_tracks = [
            {
                "title": "Minimal Track",
                "artist": "Bare Artist",
                # All other fields (album, url, scores, explanation, etc.) omitted
            }
        ]
        response = self.client.post("/api/studio/export.csv", json={"tracks": minimal_tracks})
        self.assertEqual(response.status_code, 200)

        reader = list(csv.reader(io.StringIO(response.text)))
        self.assertEqual(len(reader), 2)
        row = reader[1]
        self.assertEqual(row[1], "Minimal Track")
        self.assertEqual(row[2], "Bare Artist")
        # Ensure omitted optional fields are clean empty strings, not "None"
        self.assertEqual(row[3], "")  # Album
        self.assertEqual(row[4], "")  # URL
        self.assertEqual(row[9], "")  # Match Score
        self.assertEqual(row[10], "")  # Hybrid Score
        self.assertEqual(row[13], "")  # Explanation

    # 7. Invalid request payload
    def test_invalid_request_payload(self):
        # tracks should be a list, pass a string
        response1 = self.client.post("/api/studio/export.csv", json={"tracks": "not-a-list"})
        self.assertEqual(response1.status_code, 422)

        # malformed items
        response2 = self.client.post("/api/studio/export.csv", json={"tracks": ["not-an-object"]})
        self.assertEqual(response2.status_code, 422)

    # 8. Correct response headers
    def test_correct_response_headers(self):
        # Custom playlist_id should be reflected in the filename
        payload = {
            "playlist_id": "late-night-lofi-2026",
            "tracks": [{"title": "Track 1", "artist": "Artist 1"}],
        }
        response = self.client.post("/api/studio/export.csv", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/csv; charset=utf-8")
        self.assertEqual(
            response.headers["content-disposition"],
            'attachment; filename="late-night-lofi-2026.csv"',
        )

        # Default playlist_id when none provided
        response_default = self.client.post("/api/studio/export.csv", json={"tracks": []})
        self.assertIn('attachment; filename="sounddeck-playlist.csv"', response_default.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
