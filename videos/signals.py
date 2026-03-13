import os
import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MediaFile
from .utils import ConversionAlreadyQueuedError, QueueUnavailableError, queue_conversion_for_video


logger = logging.getLogger(__name__)


def _is_valid_media_file_instance(instance) -> bool:
    return bool(instance and instance.file)


def _can_queue_video(instance) -> bool:
    if not getattr(settings, "ENABLE_VIDEO_QUEUE", True):
        return False
    if not getattr(settings, "ENABLE_DJANGO_RQ", False):
        return False
    if not instance.video_id:
        logger.warning("MediaFile %s has no video relation; skipping HLS conversion enqueue.", instance.pk)
        return False
    return True


def _remove_file_if_present(file_field) -> None:
    if file_field and os.path.isfile(file_field.path):
        os.remove(file_field.path)


@receiver(post_save, sender=MediaFile)
def queue_video_conversion(sender, instance, created, **kwargs):
    if not created or not _is_valid_media_file_instance(instance):
        return
    if not _can_queue_video(instance):
        return
    try:
        queue_conversion_for_video(instance.video, instance)
    except ConversionAlreadyQueuedError:
        logger.info("Conversion already queued for video %s; skipping duplicate enqueue.", instance.video_id)
    except QueueUnavailableError as exc:
        logger.warning("Could not enqueue video conversion task: %s", exc)
    except Exception as exc:
        logger.warning("Could not enqueue video conversion task: %s", exc)


@receiver(models.signals.post_delete, sender=MediaFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    _remove_file_if_present(instance.file)


@receiver(models.signals.pre_save, sender=MediaFile)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_file = MediaFile.objects.get(pk=instance.pk).file
    except MediaFile.DoesNotExist:
        return

    new_file = instance.file
    if old_file != new_file:
        _remove_file_if_present(old_file)