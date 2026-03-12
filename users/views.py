from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .utils import (
    authenticate_active_user,
    blacklist_refresh_token,
    build_activation_link,
    build_password_reset_link,
    build_refreshed_access_response,
    create_inactive_user,
    decode_refresh_token,
    ensure_active_user,
    find_reset_user,
    find_user_by_email,
    PASSWORD_RESET_RESPONSE,
    find_user_by_uidb64,
    login_response,
    GENERIC_LOGIN_ERROR,
    parse_json_body,
    parse_login_payload,
    parse_password_confirm_payload,
    parse_register_payload,
    read_refresh_token_from_cookie,
    register_response,
    send_activation_email,
    send_password_reset_email,
    validate_password_pair,
    validate_register_payload,
)


@require_POST
def register(request):
    payload, error_response = parse_json_body(request)
    if error_response:
        return JsonResponse({"error": "Bitte überprüfe deine Eingaben und versuche es erneut."}, status=400)
    email, password, confirmed_password = parse_register_payload(payload)
    validation_error = validate_register_payload(email, password, confirmed_password)
    if validation_error:
        return validation_error
    user, create_error = create_inactive_user(email, password)
    if create_error:
        return create_error
    activation_link = build_activation_link(user)
    send_activation_email(user, activation_link)
    return register_response(user)


@require_GET
def activate(request, uidb64, token):
    user, user_error = find_user_by_uidb64(uidb64, "message", "Activation failed.")
    if user_error:
        return user_error
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"message": "Activation failed."}, status=400)
    ensure_active_user(user)
    return JsonResponse({"message": "Account successfully activated."}, status=200)


@require_POST
def login(request):
    payload, error_response = parse_json_body(request)
    if error_response:
        return JsonResponse({"detail": GENERIC_LOGIN_ERROR}, status=400)
    email, password = parse_login_payload(payload)
    user, auth_error = authenticate_active_user(request, email, password)
    if auth_error:
        return auth_error
    return login_response(user)


@require_POST
def logout(request):
    refresh_token, missing_error = read_refresh_token_from_cookie(request)
    if missing_error:
        return missing_error
    blacklist_error = blacklist_refresh_token(refresh_token)
    if blacklist_error:
        return blacklist_error
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
    refresh_token_value, missing_error = read_refresh_token_from_cookie(request)
    if missing_error:
        return missing_error
    access_token, token_error = decode_refresh_token(refresh_token_value)
    if token_error:
        return token_error
    return build_refreshed_access_response(access_token)


@require_POST
def password_reset(request):
    payload, error_response = parse_json_body(request)
    if error_response:
        return error_response
    email = payload.get("email", "").strip().lower()
    if not email:
        return JsonResponse({"detail": "email is required."}, status=400)
    user = find_user_by_email(email)
    if user:
        reset_link = build_password_reset_link(user)
        send_password_reset_email(user, reset_link)
    return JsonResponse({"detail": PASSWORD_RESET_RESPONSE}, status=200)


@require_POST
def password_confirm(request, uidb64, token):
    payload, error_response = parse_json_body(request)
    if error_response:
        return error_response
    new_password, confirm_password = parse_password_confirm_payload(payload)
    validation_error = validate_password_pair(new_password, confirm_password)
    if validation_error:
        return validation_error
    user, user_error = find_reset_user(uidb64)
    if user_error:
        return user_error
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"detail": "Invalid password reset link."}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return JsonResponse(
        {"detail": "Your Password has been successfully reset."},
        status=200,
    )
