"""
URL configuration for Videoflix backend.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('videos.urls')),
]

if os.environ.get('USE_SQLITE', 'False') != 'True':
    urlpatterns += [path('django-rq/', include('django_rq.urls'))]

# Serve media files (works in both dev and Docker single-server setup)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
