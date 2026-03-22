"""
Tests for all authentication API endpoints.
Checks exact response bodies as specified in the API documentation.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

REGISTER_URL = '/api/register/'
ACTIVATE_URL = '/api/activate/{uid}/{token}/'
LOGIN_URL = '/api/login/'
LOGOUT_URL = '/api/logout/'
REFRESH_URL = '/api/token/refresh/'
PASSWORD_RESET_URL = '/api/password_reset/'
PASSWORD_CONFIRM_URL = '/api/password_confirm/{uid}/{token}/'

DUMMY_EMAIL = 'django.core.mail.backends.dummy.EmailBackend'


def make_uid_and_token(user):
    """Helper: returns base64 uid and one-time token for a user."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def create_active_user(email='active@test.com', password='Test1234!'):
    """Helper: creates and returns an active user."""
    return User.objects.create_user(email=email, password=password, is_active=True)


def create_inactive_user(email='inactive@test.com', password='Test1234!'):
    """Helper: creates and returns an inactive user."""
    return User.objects.create_user(email=email, password=password, is_active=False)


@override_settings(EMAIL_BACKEND=DUMMY_EMAIL)
class RegisterViewTests(APITestCase):
    """POST /api/register/"""

    def test_success_returns_201_with_user_and_token(self):
        data = {'email': 'new@test.com', 'password': 'Test1234!', 'confirmed_password': 'Test1234!'}
        response = self.client.post(REGISTER_URL, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], 'new@test.com')

    def test_created_user_is_inactive(self):
        data = {'email': 'new@test.com', 'password': 'Test1234!', 'confirmed_password': 'Test1234!'}
        self.client.post(REGISTER_URL, data, format='json')
        self.assertFalse(User.objects.get(email='new@test.com').is_active)

    def test_password_mismatch_returns_400_with_detail(self):
        data = {'email': 'fail@test.com', 'password': 'Test1234!', 'confirmed_password': 'Wrong!'}
        response = self.client.post(REGISTER_URL, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_duplicate_email_returns_400_with_detail(self):
        create_active_user(email='dup@test.com')
        data = {'email': 'dup@test.com', 'password': 'Test1234!', 'confirmed_password': 'Test1234!'}
        response = self.client.post(REGISTER_URL, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_missing_fields_returns_400(self):
        response = self.client.post(REGISTER_URL, {'email': 'x@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(EMAIL_BACKEND=DUMMY_EMAIL)
class ActivateAccountViewTests(APITestCase):
    """GET /api/activate/<uidb64>/<token>/"""

    def setUp(self):
        self.user = create_inactive_user(email='activate@test.com')

    def test_valid_token_returns_200_with_message(self):
        uid, token = make_uid_and_token(self.user)
        response = self.client.get(ACTIVATE_URL.format(uid=uid, token=token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Account successfully activated.')

    def test_valid_token_sets_user_active(self):
        uid, token = make_uid_and_token(self.user)
        self.client.get(ACTIVATE_URL.format(uid=uid, token=token))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_invalid_token_returns_400_with_message(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(ACTIVATE_URL.format(uid=uid, token='invalid-token'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)

    def test_invalid_uid_returns_400(self):
        response = self.client.get(ACTIVATE_URL.format(uid='invalid-uid', token='invalid-token'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(APITestCase):
    """POST /api/login/"""

    def setUp(self):
        self.user = create_active_user(email='login@test.com')
        self.credentials = {'email': 'login@test.com', 'password': 'Test1234!'}

    def test_success_returns_200_with_detail_and_user(self):
        response = self.client.post(LOGIN_URL, self.credentials, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Login successful')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'login@test.com')

    def test_success_sets_access_token_cookie(self):
        response = self.client.post(LOGIN_URL, self.credentials, format='json')
        self.assertIn('access_token', response.cookies)

    def test_success_sets_refresh_token_cookie(self):
        response = self.client.post(LOGIN_URL, self.credentials, format='json')
        self.assertIn('refresh_token', response.cookies)

    def test_cookies_are_httponly(self):
        response = self.client.post(LOGIN_URL, self.credentials, format='json')
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_inactive_user_returns_400_with_detail(self):
        inactive = create_inactive_user(email='inactive@test.com')
        response = self.client.post(LOGIN_URL, {'email': inactive.email, 'password': 'Test1234!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_wrong_password_returns_400_with_detail(self):
        response = self.client.post(LOGIN_URL, {'email': 'login@test.com', 'password': 'Wrong!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)


class LogoutViewTests(APITestCase):
    """POST /api/logout/"""

    def setUp(self):
        self.user = create_active_user(email='logout@test.com')
        self.refresh = RefreshToken.for_user(self.user)

    def test_success_returns_200_with_detail(self):
        self.client.cookies['refresh_token'] = str(self.refresh)
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Logout successful', response.data['detail'])

    def test_refresh_token_missing_returns_400(self):
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_logout_clears_access_token_cookie(self):
        self.client.cookies['refresh_token'] = str(self.refresh)
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.cookies['access_token'].value, '')

    def test_logout_clears_refresh_token_cookie(self):
        self.client.cookies['refresh_token'] = str(self.refresh)
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.cookies['refresh_token'].value, '')


class TokenRefreshViewTests(APITestCase):
    """POST /api/token/refresh/"""

    def setUp(self):
        self.user = create_active_user(email='refresh@test.com')
        self.refresh = RefreshToken.for_user(self.user)

    def test_success_returns_200_with_detail_and_access(self):
        self.client.cookies['refresh_token'] = str(self.refresh)
        response = self.client.post(REFRESH_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access', response.data)

    def test_success_sets_new_access_token_cookie(self):
        self.client.cookies['refresh_token'] = str(self.refresh)
        response = self.client.post(REFRESH_URL)
        self.assertIn('access_token', response.cookies)

    def test_missing_refresh_token_returns_400(self):
        response = self.client.post(REFRESH_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_invalid_refresh_token_returns_401(self):
        self.client.cookies['refresh_token'] = 'invalid.token.here'
        response = self.client.post(REFRESH_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)


@override_settings(EMAIL_BACKEND=DUMMY_EMAIL)
class PasswordResetViewTests(APITestCase):
    """POST /api/password_reset/"""

    def setUp(self):
        self.user = create_active_user(email='reset@test.com')

    def test_active_user_returns_200_with_detail(self):
        response = self.client.post(PASSWORD_RESET_URL, {'email': 'reset@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'An email has been sent to reset your password.')

    def test_inactive_user_still_returns_200(self):
        """Returns 200 regardless — security: never reveal account existence."""
        create_inactive_user(email='noreply@test.com')
        response = self.client.post(PASSWORD_RESET_URL, {'email': 'noreply@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nonexistent_email_still_returns_200(self):
        """Returns 200 regardless — security: never reveal account existence."""
        response = self.client.post(PASSWORD_RESET_URL, {'email': 'ghost@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordConfirmViewTests(APITestCase):
    """POST /api/password_confirm/<uidb64>/<token>/"""

    def setUp(self):
        self.user = create_active_user(email='confirm@test.com')
        self.uid, self.token = make_uid_and_token(self.user)
        self.url = PASSWORD_CONFIRM_URL.format(uid=self.uid, token=self.token)

    def test_success_returns_200_with_detail(self):
        data = {'new_password': 'NewPass1234!', 'confirm_password': 'NewPass1234!'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Your Password has been successfully reset.')

    def test_success_updates_password_in_db(self):
        data = {'new_password': 'NewPass1234!', 'confirm_password': 'NewPass1234!'}
        self.client.post(self.url, data, format='json')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass1234!'))

    def test_passwords_mismatch_returns_400(self):
        data = {'new_password': 'NewPass1234!', 'confirm_password': 'Different!'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_invalid_token_returns_400(self):
        url = PASSWORD_CONFIRM_URL.format(uid=self.uid, token='invalid-token')
        data = {'new_password': 'NewPass1234!', 'confirm_password': 'NewPass1234!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_token_is_invalid_after_use(self):
        """Token can only be used once — password change invalidates it."""
        data = {'new_password': 'NewPass1234!', 'confirm_password': 'NewPass1234!'}
        self.client.post(self.url, data, format='json')
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
