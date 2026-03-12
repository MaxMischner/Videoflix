import json
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase


GENERIC_REGISTER_ERROR = "Bitte überprüfe deine Eingaben und versuche es erneut."


class RegisterEndpointTests(TestCase):
    def setUp(self):
        self.url = "/api/register/"
        self.valid_payload = {
            "email": "user@example.com",
            "password": "securepassword",
            "confirmed_password": "securepassword",
        }

    def test_register_creates_inactive_user_and_sends_activation_mail(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertIn("detail", response_data)
        self.assertIn("user", response_data)
        self.assertEqual(response_data["user"]["email"], self.valid_payload["email"])

        user = get_user_model().objects.get(email=self.valid_payload["email"])
        self.assertFalse(user.is_active)

        self.assertEqual(len(mail.outbox), 1)
        activation_mail = mail.outbox[0]
        self.assertIn(self.valid_payload["email"], activation_mail.to)
        self.assertTrue(activation_mail.alternatives)

        first_link = activation_mail.body.strip().splitlines()[-1]
        parsed_link = urlparse(first_link)
        query = parse_qs(parsed_link.query)
        self.assertIn("uid", query)
        self.assertIn("token", query)

    def test_register_with_mismatched_passwords_returns_400(self):
        payload = {
            **self.valid_payload,
            "confirmed_password": "differentpassword",
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": GENERIC_REGISTER_ERROR})
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_register_with_duplicate_email_returns_generic_error(self):
        get_user_model().objects.create_user(
            username=self.valid_payload["email"],
            email=self.valid_payload["email"],
            password="securepassword",
            is_active=False,
        )

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": GENERIC_REGISTER_ERROR})
