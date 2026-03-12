import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class PasswordConfirmEndpointTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="oldsecurepassword",
            is_active=True,
        )
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)
        self.url = f"/api/password_confirm/{self.uidb64}/{self.token}/"

    def test_password_confirm_resets_password_and_returns_200(self):
        payload = {
            "new_password": "newsecurepassword",
            "confirm_password": "newsecurepassword",
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": "Your Password has been successfully reset."})

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepassword"))

    def test_password_confirm_with_mismatched_passwords_returns_400(self):
        payload = {
            "new_password": "newsecurepassword",
            "confirm_password": "differentpassword",
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Passwords do not match."})

    def test_password_confirm_with_invalid_token_returns_400(self):
        payload = {
            "new_password": "newsecurepassword",
            "confirm_password": "newsecurepassword",
        }
        response = self.client.post(
            f"/api/password_confirm/{self.uidb64}/invalid-token/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid password reset link."})
