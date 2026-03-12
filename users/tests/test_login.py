import json

from django.contrib.auth import get_user_model
from django.test import TestCase


GENERIC_LOGIN_ERROR = "Bitte überprüfe deine Eingaben und versuche es erneut."


class LoginEndpointTests(TestCase):
    def setUp(self):
        self.url = "/api/login/"
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

    def test_login_returns_200_and_sets_http_only_jwt_cookies(self):
        payload = {
            "email": "user@example.com",
            "password": "securepassword",
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Login successful")
        self.assertEqual(response.json()["user"]["id"], self.user.id)
        self.assertEqual(response.json()["user"]["username"], self.user.username)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_login_with_invalid_credentials_returns_400(self):
        payload = {
            "email": "user@example.com",
            "password": "wrong-password",
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": GENERIC_LOGIN_ERROR})
        self.assertNotIn("access_token", response.cookies)
        self.assertNotIn("refresh_token", response.cookies)

    def test_login_with_inactive_user_returns_generic_error(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        payload = {
            "email": "user@example.com",
            "password": "securepassword",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": GENERIC_LOGIN_ERROR})

    def test_login_with_missing_password_returns_generic_error(self):
        payload = {
            "email": "user@example.com",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": GENERIC_LOGIN_ERROR})

    def test_login_with_invalid_json_returns_generic_error(self):
        response = self.client.post(
            self.url,
            data="{",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": GENERIC_LOGIN_ERROR})
