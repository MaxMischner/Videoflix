import django_rq

RESOLUTIONS = [('480p', 480), ('720p', 720), ('1080p', 1080)]


def process_video(video_id):
    """Entry point for the RQ background worker. Orchestrates FFMPEG conversion."""
    from .models import Video
    video = Video.objects.get(pk=video_id)
    _mark_processing(video)
    try:
        thumbnail_path, final_status = _run_conversion(video)
    except Exception:
        thumbnail_path, final_status = None, 'failed'
    _save_result(video, thumbnail_path, final_status)


def _mark_processing(video):
    """Sets processing_status to 'processing' before conversion starts."""
    video.processing_status = 'processing'
    video.save(update_fields=['processing_status'])


def _run_conversion(video):
    """Generates thumbnail and converts video to all HLS resolutions."""
    from .utils import convert_to_resolution, generate_thumbnail
    input_path = video.video_file.path
    thumbnail_path = generate_thumbnail(input_path, video.pk)
    for resolution, height in RESOLUTIONS:
        convert_to_resolution(input_path, video.pk, resolution, height)
    return thumbnail_path, 'done'


def _save_result(video, thumbnail_path, processing_status):
    """Saves the final processing result back to the database."""
    if thumbnail_path:
        video.thumbnail = thumbnail_path
    video.processing_status = processing_status
    video.save(update_fields=['thumbnail', 'processing_status'])
