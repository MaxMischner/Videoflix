import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


class LogoutEndpointTests(TestCase):
    def setUp(self):
        self.login_url = "/api/login/"
        self.logout_url = "/api/logout/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

    def test_logout_without_refresh_cookie_returns_400(self):
        response = self.client.post(self.logout_url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Refresh token is missing."})

    def test_logout_blacklists_refresh_token_and_deletes_cookies(self):
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

        response = self.client.post(self.logout_url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid.",
            },
        )

        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")
        self.assertTrue(BlacklistedToken.objects.filter(token__token=refresh_token).exists())
