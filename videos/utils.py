from pathlib import Path
from collections import OrderedDict

from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import MediaFile, Video
from .tasks import QueueUnavailableError as TaskQueueUnavailableError
from .tasks import queue_convert_all_resolutions


AVAILABLE_RESOLUTIONS = ["480p", "720p", "1080p"]


class QueueUnavailableError(RuntimeError):
    """Raised when conversion jobs cannot be enqueued."""


class ConversionAlreadyQueuedError(RuntimeError):
    """Raised when a conversion is already active for a video."""


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


def _has_valid_refresh_token(request) -> bool:
    refresh_token = request.COOKIES.get("refresh_token")
    if not refresh_token:
        return False
    try:
        RefreshToken(refresh_token)
        return True
    except TokenError:
        return False


def auth_error_response_for_streaming(request):
    """Allow HLS chunk requests to continue when access token expires but refresh token is still valid."""
    access_status = get_access_token_status(request)
    if access_status == "valid":
        return None
    if _has_valid_refresh_token(request):
        return None
    if access_status == "missing":
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )
    return JsonResponse({"detail": "Invalid access token."}, status=401)


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


def _is_active_job_status(status: str) -> bool:
    return status in {"queued", "started", "deferred", "scheduled"}


def _refresh_conversion_status_from_rq(video) -> str:
    if not video.last_conversion_job_id:
        return video.conversion_status
    job_status = get_rq_job_status(video.last_conversion_job_id)
    if job_status != video.conversion_status:
        video.conversion_status = job_status
        video.save(update_fields=["conversion_status", "conversion_updated_at"])
    return job_status


def queue_conversion_for_video(video, media_file, queue_func=queue_convert_all_resolutions):
    if video.conversion_status in {"queued", "started"}:
        current_status = _refresh_conversion_status_from_rq(video)
        if _is_active_job_status(current_status):
            raise ConversionAlreadyQueuedError("Video conversion is already in progress.")

    try:
        job = queue_func(
            media_file.file.path,
            video.id,
            queue_name="default",
        )
    except TaskQueueUnavailableError as exc:
        raise QueueUnavailableError(str(exc)) from exc
    except Exception as exc:
        raise QueueUnavailableError("Video queue is unavailable.") from exc

    if not getattr(job, "id", None):
        raise QueueUnavailableError("Video queue did not return a valid job id.")

    video.last_conversion_job_id = job.id
    video.conversion_status = "queued"
    video.conversion_progress = 0
    video.save(
        update_fields=[
            "last_conversion_job_id",
            "conversion_status",
            "conversion_progress",
            "conversion_updated_at",
        ]
    )
    return job
