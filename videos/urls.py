from django.urls import path

from .views import (
    trigger_video_conversion,
    video_conversion_status,
    video_dashboard,
    video_list,
    video_manifest,
    video_playback,
    video_segment,
)

urlpatterns = [
    path("video/", video_list, name="video-list"),
    path("video/dashboard/", video_dashboard, name="video-dashboard"),
    path("video/<int:movie_id>/playback/", video_playback, name="video-playback"),
    path("video/<int:movie_id>/convert/", trigger_video_conversion, name="video-convert-trigger"),
    path("video/<int:movie_id>/convert/status/", video_conversion_status, name="video-convert-status"),
    path("video/<int:movie_id>/<str:resolution>/index.m3u8", video_manifest, name="video-manifest"),
    path("video/<int:movie_id>/<str:resolution>/<str:segment>/", video_segment, name="video-segment"),
]
