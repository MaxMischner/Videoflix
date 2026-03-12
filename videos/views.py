from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import MediaFile, Video
from .tasks import queue_convert_all_resolutions


def _get_rq_job_status(job_id):
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


def _get_access_token_status(request):
	access_token = request.COOKIES.get("access_token")
	if not access_token:
		return "missing"

	try:
		AccessToken(access_token)
		return "valid"
	except TokenError:
		return "invalid"


@require_GET
def video_list(request):
	access_token_status = _get_access_token_status(request)
	if access_token_status == "missing":
		return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
	if access_token_status == "invalid":
		return JsonResponse({"detail": "Invalid access token."}, status=401)

	try:
		videos = Video.objects.all().order_by("id")
		payload = [
			{
				"id": video.id,
				"created_at": video.created_at.isoformat().replace("+00:00", "Z"),
				"title": video.title,
				"description": video.description,
				"thumbnail_url": video.thumbnail_url,
				"category": video.category,
			}
			for video in videos
		]
		return JsonResponse(payload, status=200, safe=False)
	except Exception:
		return JsonResponse({"detail": "Internal server error."}, status=500)


@require_GET
def video_manifest(request, movie_id, resolution):
	access_token_status = _get_access_token_status(request)
	if access_token_status == "missing":
		return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
	if access_token_status == "invalid":
		return JsonResponse({"detail": "Invalid access token."}, status=401)

	if not Video.objects.filter(pk=movie_id).exists():
		return JsonResponse({"detail": "Video or manifest not found."}, status=404)

	stream_root = Path(getattr(settings, "VIDEO_STREAM_ROOT", settings.BASE_DIR / "media" / "video"))
	manifest_path = stream_root / str(movie_id) / resolution / "index.m3u8"

	if not manifest_path.exists() or not manifest_path.is_file():
		return JsonResponse({"detail": "Video or manifest not found."}, status=404)

	manifest_content = manifest_path.read_text(encoding="utf-8")
	return HttpResponse(manifest_content, status=200, content_type="application/vnd.apple.mpegurl")


@require_GET
def video_segment(request, movie_id, resolution, segment):
	access_token_status = _get_access_token_status(request)
	if access_token_status == "missing":
		return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
	if access_token_status == "invalid":
		return JsonResponse({"detail": "Invalid access token."}, status=401)

	if not Video.objects.filter(pk=movie_id).exists():
		return JsonResponse({"detail": "Video or segment not found."}, status=404)

	stream_root = Path(getattr(settings, "VIDEO_STREAM_ROOT", settings.BASE_DIR / "media" / "video"))
	segment_path = stream_root / str(movie_id) / resolution / segment

	if not segment_path.exists() or not segment_path.is_file():
		return JsonResponse({"detail": "Video or segment not found."}, status=404)

	segment_bytes = segment_path.read_bytes()
	return HttpResponse(segment_bytes, status=200, content_type="video/MP2T")


@require_POST
def trigger_video_conversion(request, movie_id):
	access_token_status = _get_access_token_status(request)
	if access_token_status == "missing":
		return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
	if access_token_status == "invalid":
		return JsonResponse({"detail": "Invalid access token."}, status=401)

	video = Video.objects.filter(pk=movie_id).first()
	if not video:
		return JsonResponse({"detail": "Video not found."}, status=404)

	media_file = MediaFile.objects.filter(video=video).order_by("-created_at").first()
	if not media_file or not media_file.file:
		return JsonResponse({"detail": "Source media file not found."}, status=404)

	job = queue_convert_all_resolutions(media_file.file.path, video.id, queue_name="default")
	video.last_conversion_job_id = job.id
	video.conversion_status = "queued"
	video.save(update_fields=["last_conversion_job_id", "conversion_status", "conversion_updated_at"])

	return JsonResponse(
		{
			"detail": "Video conversion queued.",
			"job_id": job.id,
			"video_id": video.id,
		},
		status=202,
	)


@require_GET
def video_conversion_status(request, movie_id):
	access_token_status = _get_access_token_status(request)
	if access_token_status == "missing":
		return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
	if access_token_status == "invalid":
		return JsonResponse({"detail": "Invalid access token."}, status=401)

	video = Video.objects.filter(pk=movie_id).first()
	if not video:
		return JsonResponse({"detail": "Video not found."}, status=404)

	if not video.last_conversion_job_id:
		return JsonResponse(
			{
				"video_id": video.id,
				"job_id": None,
				"status": video.conversion_status,
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
		},
		status=200,
	)
