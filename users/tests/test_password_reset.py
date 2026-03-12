import json
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase


PASSWORD_RESET_RESPONSE = "Wenn ein Konto mit dieser E-Mail existiert, wurde eine Nachricht versendet."


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
        self.assertEqual(response.json(), {"detail": PASSWORD_RESET_RESPONSE})
        self.assertEqual(len(mail.outbox), 1)
        first_link = mail.outbox[0].body.strip().splitlines()[-1]
        parsed_link = urlparse(first_link)
        query = parse_qs(parsed_link.query)
        self.assertIn("uid", query)
        self.assertIn("token", query)
        self.assertIn("confirm_password", parsed_link.path)
        self.assertTrue(mail.outbox[0].alternatives)

    def test_password_reset_with_unknown_email_returns_generic_response(self):
        payload = {"email": "unknown@example.com"}

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": PASSWORD_RESET_RESPONSE})
        self.assertEqual(len(mail.outbox), 0)
