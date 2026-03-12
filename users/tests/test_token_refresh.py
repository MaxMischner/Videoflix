import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class RefreshTokenEndpointTests(TestCase):
    def setUp(self):
        self.login_url = "/api/login/"
        self.refresh_url = "/api/token/refresh/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

    def test_refresh_returns_200_sets_new_access_cookie_and_access_in_body(self):
        login_payload = {
            "email": "user@example.com",
            "password": "securepassword",
        }
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_token = login_response.cookies["refresh_token"].value
        self.client.cookies["refresh_token"] = refresh_token

        response = self.client.post(self.refresh_url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["detail"], "Token refreshed")
        self.assertIn("access", response_data)
        self.assertTrue(response_data["access"])

        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])

    def test_refresh_without_refresh_cookie_returns_400(self):
        response = self.client.post(self.refresh_url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Refresh token is missing."})

    def test_refresh_with_invalid_refresh_token_returns_401(self):
        self.client.cookies["refresh_token"] = "invalid-refresh-token"

        response = self.client.post(self.refresh_url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid refresh token."})
