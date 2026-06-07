import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from app import create_app
from app.main.health import services as health_services


class FakeCleanupResponse:
    def __init__(self, status, payload):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class CleanupExpiredMessengerStoriesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config.update(
            INTERNAL_SERVICE_TOKEN="test-internal-token",
            MESSENGER_SERVICE_TIMEOUT_SECONDS=1,
            MESSENGER_CLEANUP_TIMEOUT_SECONDS=30,
        )
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_cleanup_falls_back_to_next_messenger_url_when_first_is_unavailable(self):
        self.app.config["MESSENGER_SERVICE_URLS"] = [
            "http://localhost:8000",
            "https://messenger.example.test",
        ]
        calls = []
        timeouts = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            timeouts.append(timeout)
            if request.full_url.startswith("http://localhost:8000/"):
                raise URLError("connection refused")

            return FakeCleanupResponse(
                200,
                {
                    "status": "ok",
                    "service": "messenger",
                    "result": {
                        "expired_stories": 2,
                        "media_cleaned": 1,
                    },
                },
            )

        with patch.object(health_services, "urlopen", side_effect=fake_urlopen):
            response, status = health_services.cleanup_expired_messenger_stories()

        self.assertEqual(status, 200)
        self.assertTrue(response["ok"])
        self.assertEqual(response["messenger_url"], "https://messenger.example.test")
        self.assertEqual(response["messenger"]["result"]["expired_stories"], 2)
        self.assertEqual(
            calls,
            [
                "http://localhost:8000/stories/internal/cleanup-expired/",
                "https://messenger.example.test/stories/internal/cleanup-expired/",
            ],
        )
        self.assertEqual(timeouts, [30, 30])

    def test_cleanup_reports_unavailable_after_all_messenger_urls_fail(self):
        self.app.config["MESSENGER_SERVICE_URLS"] = [
            "http://localhost:8000",
            "https://messenger.example.test",
        ]
        calls = []
        timeouts = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            timeouts.append(timeout)
            raise URLError("connection refused")

        with patch.object(health_services, "urlopen", side_effect=fake_urlopen):
            response, status = health_services.cleanup_expired_messenger_stories()

        self.assertEqual(status, 503)
        self.assertFalse(response["ok"])
        self.assertEqual(response["message"], "Messenger cleanup service is unavailable.")
        self.assertEqual(response["messenger_urls"], calls)
        self.assertEqual(timeouts, [30, 30])


if __name__ == "__main__":
    unittest.main()
