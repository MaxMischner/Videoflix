import os
import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MediaFile, Video
from .tasks import queue_convert_all_resolutions


logger = logging.getLogger(__name__)


def create_video(sender, instance, created, **kwargs):
    if created:
        print("New object created")


post_save.connect(create_video, sender=Video)


@receiver(post_save, sender=MediaFile)
def queue_video_conversion(sender, instance, created, **kwargs):
    if not created or not instance.file:
        return

    if not getattr(settings, "ENABLE_VIDEO_QUEUE", True):
        return

    if not instance.video_id:
        logger.warning("MediaFile %s has no video relation; skipping HLS conversion enqueue.", instance.pk)
        return

    try:
        queue_convert_all_resolutions(instance.file.path, instance.video_id, queue_name="default")
    except Exception as exc:
        logger.warning("Could not enqueue video conversion task: %s", exc)


@receiver(models.signals.post_delete, sender=MediaFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem when corresponding `MediaFile` object is deleted.
    """
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)


@receiver(models.signals.pre_save, sender=MediaFile)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem when corresponding `MediaFile` object is
    updated with new file.
    """
    if not instance.pk:
        return False

    try:
        old_file = MediaFile.objects.get(pk=instance.pk).file
    except MediaFile.DoesNotExist:
        return False

    new_file = instance.file
    if old_file != new_file and os.path.isfile(old_file.path):
        os.remove(old_file.path)