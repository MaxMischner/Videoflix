from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


def get_uid_and_token(user):
    """Returns base64-encoded user ID and a one-time token."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def decode_user_from_uid(uidb64):
    """Decodes a base64 user ID and returns the corresponding user."""
    uid = force_str(urlsafe_base64_decode(uidb64))
    return User.objects.get(pk=uid)


def send_activation_email(user, request):
    """Sends an account activation email with a one-time link."""
    uid, token = get_uid_and_token(user)
    activation_url = f'{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uid}&token={token}'
    html_message = render_to_string('emails/activation_email.html', {
        'user': user,
        'activation_url': activation_url,
    })
    send_mail(
        subject='Activate your Videoflix account',
        message=f'Activate your account: {activation_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


def activate_user(uidb64, token):
    """Validates token and activates the user account. Returns user or None."""
    try:
        user = decode_user_from_uid(uidb64)
        if not default_token_generator.check_token(user, token):
            return None
        user.is_active = True
        user.save(update_fields=['is_active'])
        return user
    except Exception:
        return None


def send_password_reset_email(email, request):
    """Sends a password reset email if the email belongs to an active user."""
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return
    uid, token = get_uid_and_token(user)
    reset_url = f'{settings.FRONTEND_URL}/pages/auth/confirm_password.html?uid={uid}&token={token}'
    html_message = render_to_string('emails/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
    })
    send_mail(
        subject='Reset your Videoflix password',
        message=f'Reset your password: {reset_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


def confirm_password_reset(uidb64, token, new_password):
    """Validates token and sets a new password. Returns True on success."""
    try:
        user = decode_user_from_uid(uidb64)
        if not default_token_generator.check_token(user, token):
            return False
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return True
    except Exception:
        return False


def set_auth_cookies(response, access_token, refresh_token):
    """Sets HttpOnly JWT cookies on the response."""
    cookie_kwargs = {
        'httponly': settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        'secure': settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        'samesite': settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
    }
    access_max_age = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
    refresh_max_age = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
    response.set_cookie('access_token', access_token, max_age=access_max_age, **cookie_kwargs)
    response.set_cookie('refresh_token', refresh_token, max_age=refresh_max_age, **cookie_kwargs)


def clear_auth_cookies(response):
    """Deletes both JWT cookies from the response."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')


def rotate_refresh_token(refresh_token_str):
    """Blacklists old refresh token and returns new access + refresh token strings."""
    from rest_framework_simplejwt.tokens import RefreshToken
    old_refresh = RefreshToken(refresh_token_str)
    old_refresh.blacklist()
    user = User.objects.get(pk=old_refresh['user_id'])
    new_refresh = RefreshToken.for_user(user)
    return str(new_refresh.access_token), str(new_refresh)
