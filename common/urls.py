from django.urls import path

from .views import imprint, legal_overview, privacy_policy

urlpatterns = [
    path("legal/", legal_overview, name="legal-overview"),
    path("legal/privacy/", privacy_policy, name="legal-privacy"),
    path("legal/imprint/", imprint, name="legal-imprint"),
]
