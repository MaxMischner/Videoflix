from django.db import models

PROCESSING_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('done', 'Done'),
    ('failed', 'Failed'),
]


class Video(models.Model):
    """Stores video metadata and tracks FFMPEG processing status."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='uploads/videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
