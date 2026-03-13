from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Video
from .tasks import queue_convert_all_resolutions
from .utils import (
    AVAILABLE_RESOLUTIONS,
    ConversionAlreadyQueuedError,
    QueueUnavailableError,
    auth_error_response,
    auth_error_response_for_streaming,
    build_manifest_path,
    build_segment_path,
    dashboard_payload,
    find_video,
    get_rq_job_status,
    latest_media_file,
    list_videos_payload,
    ordered_videos_desc,
    playback_payload,
    queue_conversion_for_video,
)


_get_rq_job_status = get_rq_job_status


@require_GET
def video_list(request):
    auth_error = auth_error_response(request)
    if auth_error:
        return auth_error
    try:
        videos = ordered_videos_desc()
        payload = list_videos_payload(videos)
        return JsonResponse(payload, status=200, safe=False)
    except Exception:
        return JsonResponse({"detail": "Internal server error."}, status=500)


@require_GET
def video_dashboard(request):
    auth_error = auth_error_response(request)
    if auth_error:
        return auth_error
    try:
        videos = ordered_videos_desc()
        payload = dashboard_payload(videos)
        return JsonResponse(payload, status=200)
    except Exception:
        return JsonResponse({"detail": "Internal server error."}, status=500)


@require_GET
def video_playback(request, movie_id):
    auth_error = auth_error_response(request)
    if auth_error:
        return auth_error
    video = find_video(movie_id)
    if not video:
        return JsonResponse({"detail": "Video not found."}, status=404)
    payload = playback_payload(video.id)
    payload["available_resolutions"] = AVAILABLE_RESOLUTIONS
    return JsonResponse(payload, status=200)


@require_GET
def video_manifest(request, movie_id, resolution):
    auth_error = auth_error_response_for_streaming(request)
    if auth_error:
        return auth_error
    if not Video.objects.filter(pk=movie_id).exists():
        return JsonResponse({"detail": "Video or manifest not found."}, status=404)
    manifest_path = build_manifest_path(movie_id, resolution)
    if not manifest_path.exists() or not manifest_path.is_file():
        return JsonResponse({"detail": "Video or manifest not found."}, status=404)
    manifest_content = manifest_path.read_text(encoding="utf-8")
    return HttpResponse(
        manifest_content,
        status=200,
        content_type="application/vnd.apple.mpegurl",
    )


@require_GET
def video_segment(request, movie_id, resolution, segment):
    auth_error = auth_error_response_for_streaming(request)
    if auth_error:
        return auth_error
    if not Video.objects.filter(pk=movie_id).exists():
        return JsonResponse({"detail": "Video or segment not found."}, status=404)
    segment_path = build_segment_path(movie_id, resolution, segment)
    if not segment_path.exists() or not segment_path.is_file():
        return JsonResponse({"detail": "Video or segment not found."}, status=404)
    segment_bytes = segment_path.read_bytes()
    return HttpResponse(segment_bytes, status=200, content_type="video/MP2T")


@require_POST
def trigger_video_conversion(request, movie_id):
    auth_error = auth_error_response(request)
    if auth_error:
        return auth_error
    video = find_video(movie_id)
    if not video:
        return JsonResponse({"detail": "Video not found."}, status=404)
    media_file = latest_media_file(video)
    if not media_file or not media_file.file:
        return JsonResponse({"detail": "Source media file not found."}, status=404)
    try:
        job = queue_conversion_for_video(
            video,
            media_file,
            queue_func=queue_convert_all_resolutions,
        )
    except ConversionAlreadyQueuedError:
        return JsonResponse({"detail": "Video conversion is already in progress."}, status=409)
    except QueueUnavailableError:
        return JsonResponse({"detail": "Video conversion queue is unavailable."}, status=503)

    return JsonResponse(
        {"detail": "Video conversion queued.", "job_id": job.id, "video_id": video.id},
        status=202,
    )


@require_GET
def video_conversion_status(request, movie_id):
    auth_error = auth_error_response(request)
    if auth_error:
        return auth_error
    video = find_video(movie_id)
    if not video:
        return JsonResponse({"detail": "Video not found."}, status=404)
    if not video.last_conversion_job_id:
        return JsonResponse(
            {
                "video_id": video.id,
                "job_id": None,
                "status": video.conversion_status,
                "progress": video.conversion_progress,
            },
            status=200,
        )
    job_status = _get_rq_job_status(video.last_conversion_job_id)
    if job_status != video.conversion_status:
        video.conversion_status = job_status
        video.save(update_fields=["conversion_status", "conversion_updated_at"])
    return JsonResponse(
        {
            "video_id": video.id,
            "job_id": video.last_conversion_job_id,
            "status": job_status,
            "progress": video.conversion_progress,
        },
        status=200,
    )
