import json
import unittest
from unittest.mock import patch

from app import create_app, db
from app.main.api import services as contact_services
from app.main.api.model import Contact, User


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


class ContactPrivacyPolicyTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config.update(
            INTERNAL_SERVICE_TOKEN="test-internal-token",
            MESSENGER_SERVICE_URL="https://messenger.example.test",
            MESSENGER_SERVICE_TIMEOUT_SECONDS=5,
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def create_user(self, user_id, username, account_number):
        user = User(
            id=user_id,
            username=username,
            email=f"{username}@epost.com",
            account_number=account_number,
            password_hash="test-hash",
        )
        db.session.add(user)
        return user

    def save_contact(self, owner, contact_user, blocked=False, ghosted=False):
        contact = Contact(
            owner_user_id=owner.id,
            contact_user_id=contact_user.id,
            alias_name=contact_user.username.title(),
            blocked=blocked,
            ghosted=ghosted,
        )
        db.session.add(contact)
        return contact

    def test_receipt_visibility_hides_blocked_and_ghosted_contacts(self):
        owner = self.create_user(1, "owner", "7000000001")
        blocked = self.create_user(2, "blocked", "7000000002")
        ghosted = self.create_user(3, "ghosted", "7000000003")
        visible = self.create_user(4, "visible", "7000000004")
        self.save_contact(owner, blocked, blocked=True)
        self.save_contact(owner, ghosted, ghosted=True)
        self.save_contact(owner, visible)
        db.session.commit()

        result, status = contact_services.resolve_receipt_visibility_policy(
            {
                "owner_user_id": owner.id,
                "candidate_user_ids": [blocked.id, ghosted.id, visible.id],
            }
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["hidden_user_ids"], [blocked.id, ghosted.id])
        self.assertEqual(result["visible_user_ids"], [visible.id])

    def test_story_audience_excludes_blocked_contacts_in_both_directions(self):
        owner = self.create_user(1, "owner", "7000000001")
        owner_blocked = self.create_user(2, "ownerblocked", "7000000002")
        reverse_blocked = self.create_user(3, "reverseblocked", "7000000003")
        visible = self.create_user(4, "visible", "7000000004")
        self.save_contact(owner, owner_blocked, blocked=True)
        self.save_contact(owner, reverse_blocked)
        self.save_contact(owner, visible)
        self.save_contact(reverse_blocked, owner, blocked=True)
        db.session.commit()

        result, status = contact_services.resolve_story_audience_policy(
            {"owner_user_id": owner.id}
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            [contact["user_id"] for contact in result["valid_contacts"]],
            [visible.id],
        )
        excluded = {
            contact["user_id"]: contact["reason"]
            for contact in result["excluded_contacts"]
        }
        self.assertEqual(excluded[owner_blocked.id], "owner_blocked_contact")
        self.assertEqual(excluded[reverse_blocked.id], "contact_blocked_owner")

    def test_story_visibility_denies_when_owner_blocked_viewer(self):
        owner = self.create_user(1, "owner", "7000000001")
        viewer = self.create_user(2, "viewer", "7000000002")
        self.save_contact(owner, viewer, blocked=True)
        self.save_contact(viewer, owner)
        db.session.commit()

        result, status = contact_services.authorize_story_visibility_policy(
            {
                "owner_user_id": owner.id,
                "viewer_user_id": viewer.id,
            }
        )

        self.assertEqual(status, 403)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "owner_blocked_viewer")
        self.assertTrue(result["block_context"]["owner_blocked_viewer"])

    def test_blocking_contact_refreshes_receipt_visibility_cache(self):
        owner = self.create_user(1, "owner", "7000000001")
        contact_user = self.create_user(2, "contact", "7000000002")
        self.save_contact(owner, contact_user)
        db.session.commit()

        with patch.object(contact_services, "notify_messenger_authorization_cache") as authorization_cache:
            with patch.object(contact_services, "notify_messenger_receipt_visibility_cache") as receipt_cache:
                with patch.object(contact_services, "notify_messenger_presence_visibility"):
                    result, status = contact_services.set_saved_contact_blocked(
                        owner.id,
                        {"account_number": contact_user.account_number},
                        True,
                    )

        self.assertEqual(status, 200)
        self.assertTrue(result["contact"]["blocked"])
        authorization_cache.assert_called_once_with(owner.id, contact_user.id)
        receipt_cache.assert_called_once_with(owner.id, contact_user.id)


if __name__ == "__main__":
    unittest.main()
