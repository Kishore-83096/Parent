import json
import unittest
from unittest.mock import patch

from app import create_app
from app.main.api import services as contact_services


class FakeMessengerResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class ContactMessengerNotificationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config.update(
            INTERNAL_SERVICE_TOKEN="test-internal-token",
            MESSENGER_SERVICE_URL="https://messenger.example.test",
            MESSENGER_SERVICE_TIMEOUT_SECONDS=5,
        )
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_direct_room_visibility_notification_sends_expected_payload(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return FakeMessengerResponse()

        with patch.object(contact_services, "urlopen", side_effect=fake_urlopen):
            contact_services.notify_messenger_direct_room_visibility(
                owner_user_id=1,
                contact_user_id=2,
                hidden=True,
            )

        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(
            request.full_url,
            "https://messenger.example.test/rooms/internal/direct-visibility/",
        )
        self.assertEqual(timeout, 2)
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "owner_user_id": 1,
                "peer_user_id": 2,
                "hidden": True,
            },
        )
        self.assertEqual(
            request.get_header("X-internal-service-token"),
            "test-internal-token",
        )


if __name__ == "__main__":
    unittest.main()
