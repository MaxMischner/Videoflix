import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


GENERIC_REGISTER_ERROR = "Bitte überprüfe deine Eingaben und versuche es erneut."
GENERIC_LOGIN_ERROR = "Bitte überprüfe deine Eingaben und versuche es erneut."
PASSWORD_RESET_RESPONSE = "Wenn ein Konto mit dieser E-Mail existiert, wurde eine Nachricht versendet."


def parse_json_body(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Invalid JSON body."}, status=400)


def parse_register_payload(payload):
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    confirmed_password = payload.get("confirmed_password", "")
    return email, password, confirmed_password


def validate_register_payload(email, password, confirmed_password):
    if not email or not password or not confirmed_password:
        return JsonResponse({"error": GENERIC_REGISTER_ERROR}, status=400)
    if password != confirmed_password:
        return JsonResponse({"error": GENERIC_REGISTER_ERROR}, status=400)
    return None


def create_inactive_user(email, password):
    user_model = get_user_model()
    if user_model.objects.filter(email=email).exists():
        return None, JsonResponse({"error": GENERIC_REGISTER_ERROR}, status=400)
    user = user_model.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=False,
    )
    return user, None


def register_response(user):
    return JsonResponse(
        {
            "detail": "Registrierung erfolgreich. Bitte bestätige deine E-Mail-Adresse.",
            "user": {"id": user.id, "email": user.email},
        },
        status=201,
    )


def build_activation_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5500").rstrip("/")
    activation_path = getattr(settings, "FRONTEND_ACTIVATION_PATH", "/pages/auth/confirm_email.html")
    return f"{frontend_base_url}{activation_path}?uid={uidb64}&token={token}"


def send_activation_email(user, activation_link):
    send_mail(
        subject="Videoflix Account aktivieren",
        message=(
            "Bitte bestätige deine Registrierung bei Videoflix über diesen Link:\n"
            f"{activation_link}"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@videoflix.local"),
        recipient_list=[user.email],
        fail_silently=False,
    )


def find_user_by_uidb64(uidb64, error_key, error_message):
    user_model = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return user_model.objects.get(pk=uid), None
    except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
        return None, JsonResponse({error_key: error_message}, status=400)


def ensure_active_user(user):
    if user.is_active:
        return
    user.is_active = True
    user.save(update_fields=["is_active"])


def parse_login_payload(payload):
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    return email, password


def authenticate_active_user(request, email, password):
    if not email or not password:
        return None, JsonResponse({"detail": GENERIC_LOGIN_ERROR}, status=400)
    user = authenticate(request, username=email, password=password)
    if not user:
        return None, JsonResponse({"detail": GENERIC_LOGIN_ERROR}, status=400)
    if not user.is_active:
        return None, JsonResponse({"detail": GENERIC_LOGIN_ERROR}, status=400)
    return user, None


def attach_auth_cookies(response, access_token, refresh_token=None):
    secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=secure,
        samesite="Lax",
    )
    if refresh_token:
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            secure=secure,
            samesite="Lax",
        )


def login_response(user):
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    response = JsonResponse(
        {
            "detail": "Login successful",
            "user": {"id": user.id, "username": user.username},
        },
        status=200,
    )
    attach_auth_cookies(response, access_token, refresh_token=refresh_token)
    return response


def read_refresh_token_from_cookie(request):
    refresh_token = request.COOKIES.get("refresh_token")
    if not refresh_token:
        return None, JsonResponse({"detail": "Refresh token is missing."}, status=400)
    return refresh_token, None


def build_refreshed_access_response(access_token):
    response = JsonResponse({"detail": "Token refreshed", "access": access_token}, status=200)
    attach_auth_cookies(response, access_token)
    return response


def find_user_by_email(email):
    user_model = get_user_model()
    try:
        return user_model.objects.get(email=email)
    except user_model.DoesNotExist:
        return None


def build_password_reset_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5500").rstrip("/")
    reset_path = getattr(settings, "FRONTEND_PASSWORD_RESET_PATH", "/pages/auth/confirm_password.html")
    return f"{frontend_base_url}{reset_path}?uid={uidb64}&token={token}"


def build_password_reset_html(reset_link):
    return (
        "<html><body style='margin:0;padding:0;background:#f7f7f7;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='background:#f7f7f7;padding:24px 0;'>"
        "<tr><td align='center'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='max-width:600px;background:#ffffff;border-radius:12px;padding:24px;font-family:Arial,sans-serif;color:#1a1a1a;'>"
        "<tr><td style='font-size:20px;font-weight:bold;padding-bottom:12px;'>Passwort zuruecksetzen</td></tr>"
        "<tr><td style='font-size:15px;line-height:1.6;padding-bottom:20px;'>"
        "Du hast eine Passwort-Zuruecksetzung angefordert. Klicke auf den Button, um ein neues Passwort festzulegen."
        "</td></tr>"
        f"<tr><td style='padding-bottom:20px;'><a href='{reset_link}' style='display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:8px;font-size:14px;'>Neues Passwort festlegen</a></td></tr>"
        f"<tr><td style='font-size:12px;color:#666;word-break:break-all;'>Falls der Button nicht funktioniert, nutze diesen Link:<br>{reset_link}</td></tr>"
        "</table></td></tr></table></body></html>"
    )


def send_password_reset_email(user, reset_link):
    html_message = build_password_reset_html(reset_link)
    send_mail(
        subject="Videoflix Password Reset",
        message=(
            "You requested a password reset. Use the following link to set a new password:\n"
            f"{reset_link}"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@videoflix.local"),
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def parse_password_confirm_payload(payload):
    new_password = payload.get("new_password", "")
    confirm_password = payload.get("confirm_password", "")
    return new_password, confirm_password


def validate_password_pair(new_password, confirm_password):
    if not new_password or not confirm_password:
        return JsonResponse(
            {"detail": "new_password and confirm_password are required."},
            status=400,
        )
    if new_password != confirm_password:
        return JsonResponse({"detail": "Passwords do not match."}, status=400)
    return None


def find_reset_user(uidb64):
    return find_user_by_uidb64(uidb64, "detail", "Invalid password reset link.")


def decode_refresh_token(refresh_token_value):
    try:
        refresh = RefreshToken(refresh_token_value)
        return str(refresh.access_token), None
    except TokenError:
        return None, JsonResponse({"detail": "Invalid refresh token."}, status=401)


def blacklist_refresh_token(refresh_token):
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return None
    except TokenError:
        return JsonResponse({"detail": "Refresh token is invalid."}, status=400)
