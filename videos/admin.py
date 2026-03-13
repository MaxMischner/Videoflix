from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from .models import MediaFile, Video
from .utils import (
	ConversionAlreadyQueuedError,
	QueueUnavailableError,
	queue_conversion_for_video,
)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
	change_list_template = "admin/videos/video/change_list.html"
	exclude = ("thumbnail_url",)
	list_display = (
		"id",
		"title",
		"category",
		"conversion_status",
		"conversion_progress_display",
		"last_conversion_job_id",
		"conversion_updated_at",
		"created_at",
	)
	search_fields = ("title", "category", "last_conversion_job_id")
	list_filter = ("category", "conversion_status", "created_at")
	actions = ("queue_hls_conversion",)

	@admin.display(description="Progress", ordering="conversion_progress")
	def conversion_progress_display(self, obj):
		progress = max(0, min(100, int(getattr(obj, "conversion_progress", 0))))
		bar_color = "#2563eb"
		if obj.conversion_status == "started":
			bar_color = "#f59e0b"
		elif obj.conversion_status == "finished":
			bar_color = "#16a34a"
		elif obj.conversion_status == "failed":
			bar_color = "#dc2626"

		return format_html(
			'<div style="min-width:170px;"><div style="height:10px;background:#e5e7eb;border-radius:999px;overflow:hidden;"><div style="height:10px;width:{}%;background:{};"></div></div><div style="font-size:11px;margin-top:2px;">{}%</div></div>',
			progress,
			bar_color,
			progress,
		)

	def _registry_count(self, registry) -> int:
		count = getattr(registry, "count", 0)
		return int(count() if callable(count) else count)

	def _queue_metrics(self):
		if not getattr(settings, "ENABLE_DJANGO_RQ", False):
			return {
				"available": False,
				"reason": "Queue disabled (ENABLE_DJANGO_RQ=False).",
			}

		try:
			import django_rq

			queue = django_rq.get_queue("default")
			queued = len(queue)
			started = self._registry_count(queue.started_job_registry)
			deferred = self._registry_count(queue.deferred_job_registry)
			scheduled = self._registry_count(queue.scheduled_job_registry)
			failed = self._registry_count(queue.failed_job_registry)
			pending_total = queued + started + deferred + scheduled
			tracked_total = pending_total + failed

			def pct(value: int) -> int:
				if tracked_total <= 0:
					return 0
				return int(round((value / tracked_total) * 100))

			return {
				"available": True,
				"pending_total": pending_total,
				"tracked_total": tracked_total,
				"has_jobs": tracked_total > 0,
				"queued": queued,
				"queued_pct": pct(queued),
				"started": started,
				"started_pct": pct(started),
				"deferred": deferred,
				"deferred_pct": pct(deferred),
				"scheduled": scheduled,
				"scheduled_pct": pct(scheduled),
				"failed": failed,
				"failed_pct": pct(failed),
			}
		except Exception as exc:
			return {
				"available": False,
				"reason": f"Queue unavailable: {exc}",
			}

	def changelist_view(self, request, extra_context=None):
		context = dict(extra_context or {})
		context["worker_queue_metrics"] = self._queue_metrics()
		return super().changelist_view(request, extra_context=context)

	def _latest_media_file(self, video):
		return MediaFile.objects.filter(video=video).order_by("-created_at").first()

	def _queue_video_job(self, video, media_file):
		queue_conversion_for_video(video, media_file)

	def _queue_selected_videos(self, queryset):
		queued_count = 0
		missing_source_count = 0
		queue_unavailable_count = 0
		already_queued_count = 0
		error_count = 0
		for video in queryset:
			media_file = self._latest_media_file(video)
			if not media_file or not media_file.file:
				missing_source_count += 1
				continue
			try:
				self._queue_video_job(video, media_file)
				queued_count += 1
			except ConversionAlreadyQueuedError:
				already_queued_count += 1
			except QueueUnavailableError:
				queue_unavailable_count += 1
			except Exception:
				error_count += 1
		return {
			"queued": queued_count,
			"missing_source": missing_source_count,
			"queue_unavailable": queue_unavailable_count,
			"already_queued": already_queued_count,
			"errors": error_count,
		}

	def _send_queue_messages(self, request, result):
		queued_count = result["queued"]
		if queued_count:
			self.message_user(request, f"Queued conversion for {queued_count} video(s).", level=messages.SUCCESS)

		if result["missing_source"]:
			self.message_user(
				request,
				f"Skipped {result['missing_source']} video(s) without source media file.",
				level=messages.WARNING,
			)

		if result["queue_unavailable"]:
			self.message_user(
				request,
				f"Skipped {result['queue_unavailable']} video(s) because queue is unavailable (check ENABLE_DJANGO_RQ/Redis/worker).",
				level=messages.WARNING,
			)

		if result["already_queued"]:
			self.message_user(
				request,
				f"Skipped {result['already_queued']} video(s) because conversion is already queued or running.",
				level=messages.INFO,
			)

		if result["errors"]:
			self.message_user(
				request,
				f"Skipped {result['errors']} video(s) due to unexpected errors. Check backend logs.",
				level=messages.ERROR,
			)

	@admin.action(description="Queue HLS conversion for selected videos")
	def queue_hls_conversion(self, request, queryset):
		result = self._queue_selected_videos(queryset)
		self._send_queue_messages(request, result)


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
	list_display = ("id", "video", "file", "created_at")
	search_fields = ("file",)
	list_filter = ("created_at",)
