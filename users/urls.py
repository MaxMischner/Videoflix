from django.urls import path

from .views import activate, login, logout, password_confirm, password_reset, refresh_token, register

urlpatterns = [
    path("register/", register, name="register"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("login/", login, name="login"),
    path("logout/", logout, name="logout"),
    path("token/refresh/", refresh_token, name="token-refresh"),
    path("password_reset/", password_reset, name="password-reset"),
    path("password_confirm/<uidb64>/<token>/", password_confirm, name="password-confirm"),
]
