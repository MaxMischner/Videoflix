from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class ActivateEndpointTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="inactive@example.com",
            email="inactive@example.com",
            password="securepassword",
            is_active=False,
        )

    def test_activate_with_valid_uid_and_token_returns_200_and_activates_user(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(f"/api/activate/{uidb64}/{token}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Account successfully activated."})

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_activate_with_invalid_token_returns_400(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(f"/api/activate/{uidb64}/invalid-token/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"message": "Activation failed."})

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
