import subprocess
from pathlib import Path

from django.conf import settings


def get_hls_output_dir(video_id, resolution):
    """Returns the output directory path for a given video and resolution."""
    return Path(settings.MEDIA_ROOT) / 'hls' / str(video_id) / resolution


def get_thumbnail_path(video_id):
    """Returns the file path where the thumbnail should be saved."""
    return Path(settings.MEDIA_ROOT) / 'thumbnails' / f'{video_id}.jpg'


def run_ffmpeg(command):
    """Runs an FFMPEG command and raises on non-zero exit code."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg failed: {result.stderr}')


def generate_thumbnail(input_path, video_id):
    """Extracts the first frame as a thumbnail. Returns relative media path."""
    thumb_path = get_thumbnail_path(video_id)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        'ffmpeg', '-i', str(input_path),
        '-ss', '00:00:02', '-vframes', '1',
        str(thumb_path), '-y',
    ]
    run_ffmpeg(command)
    return f'thumbnails/{video_id}.jpg'


def convert_to_resolution(input_path, video_id, resolution, height):
    """Converts a video to HLS format at the given resolution."""
    output_dir = get_hls_output_dir(video_id, resolution)
    output_dir.mkdir(parents=True, exist_ok=True)
    segment_pattern = str(output_dir / '%03d.ts')
    manifest_path = str(output_dir / 'index.m3u8')
    command = [
        'ffmpeg', '-i', str(input_path),
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-hls_time', '10',
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', segment_pattern,
        manifest_path, '-y',
    ]
    run_ffmpeg(command)
