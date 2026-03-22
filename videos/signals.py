from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Video


def _enqueue_video_processing(video_id):
    """Adds the video processing job to the default RQ queue."""
    try:
        import django_rq
        from .tasks import process_video
        django_rq.enqueue(process_video, video_id)
    except Exception as e:
        print(f'[RQ] Could not enqueue video {video_id}: {e}')


@receiver(post_save, sender=Video)
def handle_video_upload(sender, instance, created, **kwargs):
    """Triggers FFMPEG processing when a new video is uploaded."""
    if created and instance.video_file:
        _enqueue_video_processing(instance.pk)
