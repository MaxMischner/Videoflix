from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer
from .utils import (
    activate_user,
    clear_auth_cookies,
    confirm_password_reset,
    rotate_refresh_token,
    send_activation_email,
    send_password_reset_email,
    set_auth_cookies,
)


class RegisterView(APIView):
    """Creates a new inactive user and sends an activation email."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        try:
            send_activation_email(user, request)
        except Exception:
            pass
        token = str(RefreshToken.for_user(user).access_token)
        return Response({'user': UserSerializer(user).data, 'token': token}, status=status.HTTP_201_CREATED)


class ActivateAccountView(APIView):
    """Activates a user account via uid and token from the email link."""

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = activate_user(uidb64, token)
        if not user:
            return Response({'message': 'Activation failed.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Account successfully activated.'})


class LoginView(APIView):
    """Authenticates a user and sets HttpOnly JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'detail': 'Please check your inputs and try again.'}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)
        response = Response({'detail': 'Login successful', 'user': {'id': user.pk, 'username': user.email}})
        set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LogoutView(APIView):
    """Blacklists the refresh token and clears all auth cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass
        response = Response({'detail': 'Logout successful! All tokens will be deleted. Refresh token is now invalid.'})
        clear_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Issues a new access token using the refresh token cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            new_access, new_refresh = rotate_refresh_token(refresh_token)
        except TokenError:
            return Response({'detail': 'Invalid refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response({'detail': 'Token refreshed', 'access': new_access})
        set_auth_cookies(response, new_access, new_refresh)
        return response


class PasswordResetView(APIView):
    """Sends a password reset email if the email is registered."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '')
        send_password_reset_email(email, request)
        return Response({'detail': 'An email has been sent to reset your password.'})


class PasswordConfirmView(APIView):
    """Confirms the password reset and saves the new password."""

    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        if new_password != confirm_password:
            return Response({'detail': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
        success = confirm_password_reset(uidb64, token, new_password)
        if not success:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Your Password has been successfully reset.'})
