from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model that uses email as the primary identifier."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, default='')  # required by entrypoint.sh
    is_active = models.BooleanField(default=False)  # inactive until email confirmed
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
