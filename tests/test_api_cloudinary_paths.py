import unittest

from app import create_app
from app.main.api.model import User
from app.main.api.services import build_user_cloudinary_folder


class CloudinaryPathTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_user_cloudinary_folder_uses_username_and_account_number(self):
        user = User(id=1, username="Prabhas", account_number="786435123")

        self.assertEqual(
            build_user_cloudinary_folder(user),
            "Parrot/Prabhas-786435123",
        )


if __name__ == "__main__":
    unittest.main()
