from pathlib import Path
from collections import OrderedDict

from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import MediaFile, Video
from .tasks import queue_convert_all_resolutions


AVAILABLE_RESOLUTIONS = ["480p", "720p", "1080p"]


def get_rq_job_status(job_id):
    if not getattr(settings, "ENABLE_DJANGO_RQ", False):
        return "rq_disabled"
    try:
        import django_rq

        queue = django_rq.get_queue("default")
        job = queue.fetch_job(job_id)
        if not job:
            return "not_found"
        return job.get_status()
    except Exception:
        return "unknown"


def get_access_token_status(request):
    access_token = request.COOKIES.get("access_token")
    if not access_token:
        return "missing"
    try:
        AccessToken(access_token)
        return "valid"
    except TokenError:
        return "invalid"


def auth_error_response(request):
    status_value = get_access_token_status(request)
    if status_value == "missing":
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )
    if status_value == "invalid":
        return JsonResponse({"detail": "Invalid access token."}, status=401)
    return None


def stream_root() -> Path:
    return Path(
        getattr(settings, "VIDEO_STREAM_ROOT", settings.BASE_DIR / "media" / "video")
    )


def build_manifest_path(movie_id, resolution) -> Path:
    return stream_root() / str(movie_id) / resolution / "index.m3u8"


def build_segment_path(movie_id, resolution, segment) -> Path:
    return stream_root() / str(movie_id) / resolution / segment


def find_video(movie_id):
    return Video.objects.filter(pk=movie_id).first()


def ordered_videos_desc():
    return Video.objects.all().order_by("-created_at")


def serialize_video(video):
    return {
        "id": video.id,
        "created_at": video.created_at.isoformat().replace("+00:00", "Z"),
        "title": video.title,
        "description": video.description,
        "thumbnail_url": video.thumbnail_url,
        "category": video.category,
    }


def list_videos_payload(videos):
    return [serialize_video(video) for video in videos]


def group_videos_by_category(videos):
    grouped = OrderedDict()
    for video in videos:
        grouped.setdefault(video.category, []).append(serialize_video(video))
    return [{"genre": genre, "videos": genre_videos} for genre, genre_videos in grouped.items()]


def dashboard_payload(videos):
    video_items = list(videos)
    hero = serialize_video(video_items[0]) if video_items else None
    genres = group_videos_by_category(video_items)
    return {"hero": hero, "genres": genres}


def playback_payload(video_id):
    qualities = [
        {
            "resolution": resolution,
            "manifest_url": f"/api/video/{video_id}/{resolution}/index.m3u8",
        }
        for resolution in AVAILABLE_RESOLUTIONS
    ]
    return {
        "video_id": video_id,
        "qualities": qualities,
        "master_manifest_url": f"/media/video/{video_id}/master.m3u8",
    }


def latest_media_file(video):
    return MediaFile.objects.filter(video=video).order_by("-created_at").first()


def queue_conversion_for_video(video, media_file, queue_func=queue_convert_all_resolutions):
    job = queue_func(
        media_file.file.path,
        video.id,
        queue_name="default",
    )
    video.last_conversion_job_id = job.id
    video.conversion_status = "queued"
    video.save(
        update_fields=[
            "last_conversion_job_id",
            "conversion_status",
            "conversion_updated_at",
        ]
    )
    return job
