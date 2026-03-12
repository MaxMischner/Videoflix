import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class RegisterEndpointTests(TestCase):
    def setUp(self):
        self.url = "/api/register/"
        self.valid_payload = {
            "email": "user@example.com",
            "password": "securepassword",
            "confirmed_password": "securepassword",
        }

    def test_register_creates_inactive_user_and_returns_expected_payload(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertIn("user", response_data)
        self.assertIn("token", response_data)
        self.assertEqual(response_data["user"]["email"], self.valid_payload["email"])
        self.assertIsInstance(response_data["token"], str)
        self.assertTrue(response_data["token"])

        user = get_user_model().objects.get(email=self.valid_payload["email"])
        self.assertFalse(user.is_active)

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
        self.assertEqual(get_user_model().objects.count(), 0)
