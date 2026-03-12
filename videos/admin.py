from django.contrib import admin, messages

from .models import MediaFile, Video
from .tasks import queue_convert_all_resolutions


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"title",
		"category",
		"conversion_status",
		"last_conversion_job_id",
		"conversion_updated_at",
		"created_at",
	)
	search_fields = ("title", "category", "last_conversion_job_id")
	list_filter = ("category", "conversion_status", "created_at")
	actions = ("queue_hls_conversion",)

	@admin.action(description="Queue HLS conversion for selected videos")
	def queue_hls_conversion(self, request, queryset):
		queued_count = 0
		skipped_count = 0

		for video in queryset:
			media_file = MediaFile.objects.filter(video=video).order_by("-created_at").first()
			if not media_file or not media_file.file:
				skipped_count += 1
				continue

			try:
				job = queue_convert_all_resolutions(media_file.file.path, video.id, queue_name="default")
				video.last_conversion_job_id = job.id
				video.conversion_status = "queued"
				video.save(update_fields=["last_conversion_job_id", "conversion_status", "conversion_updated_at"])
				queued_count += 1
			except Exception:
				skipped_count += 1

		if queued_count:
			self.message_user(request, f"Queued conversion for {queued_count} video(s).", level=messages.SUCCESS)
		if skipped_count:
			self.message_user(
				request,
				f"Skipped {skipped_count} video(s) without source file or queue availability.",
				level=messages.WARNING,
			)


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
	list_display = ("id", "video", "file", "created_at")
	search_fields = ("file",)
	list_filter = ("created_at",)
