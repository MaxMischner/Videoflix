from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser — uses email instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        # entrypoint.sh passes username — keep it so filter(username=...) works
        return self.create_user(email, password, **extra_fields)
