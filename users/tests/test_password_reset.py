import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase


class PasswordResetEndpointTests(TestCase):
    def setUp(self):
        self.url = "/api/password_reset/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

    def test_password_reset_sends_email_for_existing_user(self):
        payload = {"email": "user@example.com"}

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": "An email has been sent to reset your password."})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("confirm_password", mail.outbox[0].body)

    def test_password_reset_with_unknown_email_returns_400(self):
        payload = {"email": "unknown@example.com"}

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "User with this email does not exist."})
        self.assertEqual(len(mail.outbox), 0)
