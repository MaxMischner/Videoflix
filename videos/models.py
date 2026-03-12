from django.db import models


class Video(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	title = models.CharField(max_length=255)
	description = models.TextField()
	thumbnail_url = models.URLField(max_length=500)
	category = models.CharField(max_length=120)
	last_conversion_job_id = models.CharField(max_length=128, null=True, blank=True)
	conversion_status = models.CharField(max_length=32, default="not_requested")
	conversion_updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.title


class MediaFile(models.Model):
	video = models.ForeignKey(
		Video,
		on_delete=models.CASCADE,
		related_name="media_files",
		null=True,
		blank=True,
	)
	file = models.FileField(upload_to="media_files/")
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.file.name
