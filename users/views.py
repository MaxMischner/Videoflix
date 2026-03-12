import json
import secrets

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.views.decorators.http import require_GET, require_POST
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


@require_POST
def register(request):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON body."}, status=400)

	email = payload.get("email", "").strip().lower()
	password = payload.get("password", "")
	confirmed_password = payload.get("confirmed_password", "")

	if not email or not password or not confirmed_password:
		return JsonResponse({"error": "email, password and confirmed_password are required."}, status=400)

	if password != confirmed_password:
		return JsonResponse({"error": "Passwords do not match."}, status=400)

	user_model = get_user_model()
	if user_model.objects.filter(email=email).exists():
		return JsonResponse({"error": "User with this email already exists."}, status=400)

	user = user_model.objects.create_user(
		username=email,
		email=email,
		password=password,
		is_active=False,
	)

	return JsonResponse(
		{
			"user": {
				"id": user.id,
				"email": user.email,
			},
			"token": secrets.token_urlsafe(32),
		},
		status=201,
	)


@require_GET
def activate(request, uidb64, token):
	user_model = get_user_model()

	try:
		uid = force_str(urlsafe_base64_decode(uidb64))
		user = user_model.objects.get(pk=uid)
	except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
		return JsonResponse({"message": "Activation failed."}, status=400)

	if not default_token_generator.check_token(user, token):
		return JsonResponse({"message": "Activation failed."}, status=400)

	if not user.is_active:
		user.is_active = True
		user.save(update_fields=["is_active"])

	return JsonResponse({"message": "Account successfully activated."}, status=200)


@require_POST
def login(request):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"detail": "Invalid JSON body."}, status=400)

	email = payload.get("email", "").strip().lower()
	password = payload.get("password", "")

	if not email or not password:
		return JsonResponse({"detail": "email and password are required."}, status=400)

	user = authenticate(request, username=email, password=password)
	if not user:
		return JsonResponse({"detail": "Invalid credentials"}, status=400)

	if not user.is_active:
		return JsonResponse({"detail": "Account is not activated"}, status=400)

	refresh = RefreshToken.for_user(user)
	access_token = str(refresh.access_token)
	refresh_token = str(refresh)

	response = JsonResponse(
		{
			"detail": "Login successful",
			"user": {
				"id": user.id,
				"username": user.username,
			},
		},
		status=200,
	)

	secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
	response.set_cookie(
		"access_token",
		access_token,
		httponly=True,
		secure=secure,
		samesite="Lax",
	)
	response.set_cookie(
		"refresh_token",
		refresh_token,
		httponly=True,
		secure=secure,
		samesite="Lax",
	)

	return response


@require_POST
def logout(request):
	refresh_token = request.COOKIES.get("refresh_token")
	if not refresh_token:
		return JsonResponse({"detail": "Refresh token is missing."}, status=400)

	try:
		token = RefreshToken(refresh_token)
		token.blacklist()
	except TokenError:
		return JsonResponse({"detail": "Refresh token is invalid."}, status=400)

	response = JsonResponse(
		{
			"detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid.",
		},
		status=200,
	)

	response.delete_cookie("access_token", samesite="Lax")
	response.delete_cookie("refresh_token", samesite="Lax")

	return response


@require_POST
def refresh_token(request):
	refresh_token_value = request.COOKIES.get("refresh_token")
	if not refresh_token_value:
		return JsonResponse({"detail": "Refresh token is missing."}, status=400)

	try:
		refresh = RefreshToken(refresh_token_value)
		access_token = str(refresh.access_token)
	except TokenError:
		return JsonResponse({"detail": "Invalid refresh token."}, status=401)

	response = JsonResponse(
		{
			"detail": "Token refreshed",
			"access": access_token,
		},
		status=200,
	)

	secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
	response.set_cookie(
		"access_token",
		access_token,
		httponly=True,
		secure=secure,
		samesite="Lax",
	)

	return response


@require_POST
def password_reset(request):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"detail": "Invalid JSON body."}, status=400)

	email = payload.get("email", "").strip().lower()
	if not email:
		return JsonResponse({"detail": "email is required."}, status=400)

	user_model = get_user_model()
	try:
		user = user_model.objects.get(email=email)
	except user_model.DoesNotExist:
		return JsonResponse({"detail": "User with this email does not exist."}, status=400)

	uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
	token = default_token_generator.make_token(user)
	reset_link = f"/pages/auth/confirm_password.html?uid={uidb64}&token={token}"

	send_mail(
		subject="Videoflix Password Reset",
		message=(
			"You requested a password reset. Use the following link to set a new password:\n"
			f"{reset_link}"
		),
		from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@videoflix.local"),
		recipient_list=[user.email],
		fail_silently=False,
	)

	return JsonResponse({"detail": "An email has been sent to reset your password."}, status=200)


@require_POST
def password_confirm(request, uidb64, token):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"detail": "Invalid JSON body."}, status=400)

	new_password = payload.get("new_password", "")
	confirm_password = payload.get("confirm_password", "")

	if not new_password or not confirm_password:
		return JsonResponse({"detail": "new_password and confirm_password are required."}, status=400)

	if new_password != confirm_password:
		return JsonResponse({"detail": "Passwords do not match."}, status=400)

	user_model = get_user_model()
	try:
		uid = force_str(urlsafe_base64_decode(uidb64))
		user = user_model.objects.get(pk=uid)
	except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
		return JsonResponse({"detail": "Invalid password reset link."}, status=400)

	if not default_token_generator.check_token(user, token):
		return JsonResponse({"detail": "Invalid password reset link."}, status=400)

	user.set_password(new_password)
	user.save(update_fields=["password"])

	return JsonResponse({"detail": "Your Password has been successfully reset."}, status=200)
