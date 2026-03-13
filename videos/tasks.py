import subprocess
from pathlib import Path

from django.conf import settings


class QueueUnavailableError(RuntimeError):
    """Raised when RQ queueing is not available in current runtime."""


HLS_PROFILES = {
    "480p": {
        "height": 480,
        "bandwidth": 1200000,
        "maxrate": "1400k",
        "bufsize": "2100k",
    },
    "720p": {
        "height": 720,
        "bandwidth": 2800000,
        "maxrate": "3200k",
        "bufsize": "4800k",
    },
    "1080p": {
        "height": 1080,
        "bandwidth": 5000000,
        "maxrate": "5700k",
        "bufsize": "8550k",
    },
}

def _hls_shared_args() -> list[str]:
    preset = str(getattr(settings, "VIDEO_FFMPEG_PRESET", "veryfast"))
    crf = str(getattr(settings, "VIDEO_FFMPEG_CRF", 23))
    threads = int(getattr(settings, "VIDEO_FFMPEG_THREADS", 0))
    args = [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        crf,
        "-g",
        "48",
        "-keyint_min",
        "48",
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "48000",
        "-hls_time",
        "10",
        "-hls_playlist_type",
        "vod",
        "-hls_list_size",
        "0",
    ]
    if threads > 0:
        args.extend(["-threads", str(threads)])
    return args


def _get_hls_base_dir(movie_id: int) -> Path:
    base_dir = Path(getattr(settings, "VIDEO_STREAM_ROOT", settings.BASE_DIR / "media" / "video"))
    output_dir = base_dir / str(movie_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _build_resolution_output_dir(movie_id: int, resolution: str) -> Path:
    output_dir = _get_hls_base_dir(movie_id) / resolution
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _update_video_tracking(
    movie_id: int,
    status: str,
    thumbnail_url: str | None = None,
    progress: int | None = None,
) -> None:
    video = _find_video_for_tracking(movie_id)
    if not video:
        return
    update_fields = _tracking_update_fields(video, status, thumbnail_url, progress)
    video.save(update_fields=update_fields)


def _find_video_for_tracking(movie_id: int):
    from .models import Video

    return Video.objects.filter(pk=movie_id).first()


def _tracking_update_fields(video, status: str, thumbnail_url: str | None, progress: int | None) -> list[str]:
    video.conversion_status = status
    fields = ["conversion_status", "conversion_updated_at"]
    if progress is not None:
        video.conversion_progress = max(0, min(100, int(progress)))
        fields.append("conversion_progress")
    if thumbnail_url is not None:
        video.thumbnail_url = thumbnail_url
        fields.append("thumbnail_url")
    return fields


def _run_ffmpeg_hls(source: str, output_dir: Path, height: int, maxrate: str, bufsize: str) -> subprocess.CompletedProcess:
    cmd = _build_hls_command(source, output_dir, height, maxrate, bufsize)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _build_hls_command(source: str, output_dir: Path, height: int, maxrate: str, bufsize: str) -> list[str]:
    segment_pattern = str(output_dir / "%03d.ts")
    playlist_path = str(output_dir / "index.m3u8")
    return _hls_input_args(source, height) + _hls_encoding_args(maxrate, bufsize) + _hls_output_args(segment_pattern, playlist_path)


def _hls_input_args(source: str, height: int) -> list[str]:
    return ["ffmpeg", "-y", "-i", source, "-vf", f"scale=-2:{height}"]


def _hls_encoding_args(maxrate: str, bufsize: str) -> list[str]:
    shared_args = _hls_shared_args()
    return shared_args[:12] + ["-maxrate", maxrate, "-bufsize", bufsize] + shared_args[12:]


def _hls_output_args(segment_pattern: str, playlist_path: str) -> list[str]:
    return ["-hls_segment_filename", segment_pattern, "-f", "hls", playlist_path]


def _run_ffmpeg_thumbnail(source: str, target: Path) -> subprocess.CompletedProcess:
    cmd = _build_thumbnail_command(source, target)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _build_thumbnail_command(source: str, target: Path) -> list[str]:
    return ["ffmpeg", "-y", "-ss", "00:00:03", "-i", source, "-frames:v", "1", "-q:v", "2", str(target)]


def convert_resolution_to_hls(source: str, movie_id: int, resolution: str) -> str:
    profile = _profile_for_resolution(resolution)
    output_dir = _build_resolution_output_dir(movie_id, resolution)
    run = _run_ffmpeg_hls(
        source=source,
        output_dir=output_dir,
        height=profile["height"],
        maxrate=profile["maxrate"],
        bufsize=profile["bufsize"],
    )
    if run.returncode != 0:
        raise RuntimeError(f"FFMPEG {resolution} HLS conversion failed: {run.stderr}")
    return str(output_dir / "index.m3u8")


def _profile_for_resolution(resolution: str) -> dict[str, int | str]:
    if resolution not in HLS_PROFILES:
        raise ValueError(f"Unsupported resolution: {resolution}")
    return HLS_PROFILES[resolution]


def _write_master_playlist(movie_id: int, generated: dict[str, str]) -> str:
    base_dir = _get_hls_base_dir(movie_id)
    master_path = base_dir / "master.m3u8"
    lines = _build_master_playlist_lines(generated)
    master_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(master_path)


def _build_master_playlist_lines(generated: dict[str, str]) -> list[str]:
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for resolution in ["480p", "720p", "1080p"]:
        if resolution in generated:
            lines.extend(_resolution_playlist_lines(resolution))
    return lines


def _resolution_playlist_lines(resolution: str) -> list[str]:
    profile = HLS_PROFILES[resolution]
    width = int(round(profile["height"] * 16 / 9))
    stream_line = f"#EXT-X-STREAM-INF:BANDWIDTH={profile['bandwidth']},RESOLUTION={width}x{profile['height']}"
    return [stream_line, f"{resolution}/index.m3u8"]


def _build_public_media_url(file_path: Path) -> str:
    media_root = Path(settings.MEDIA_ROOT)
    try:
        relative = file_path.relative_to(media_root).as_posix()
        media_url = settings.MEDIA_URL.rstrip("/")
    except ValueError:
        relative = file_path.name
        media_url = settings.MEDIA_URL.rstrip("/")

    base_url = getattr(settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base_url}{media_url}/{relative}"


def generate_thumbnail(source: str, movie_id: int) -> str:
    thumbnail_path = _get_hls_base_dir(movie_id) / "thumbnail.jpg"
    run = _run_ffmpeg_thumbnail(source, thumbnail_path)

    if run.returncode != 0:
        raise RuntimeError(f"FFMPEG thumbnail generation failed: {run.stderr}")

    return _build_public_media_url(thumbnail_path)


def convert_480p(source: str, movie_id: int) -> str:
    return convert_resolution_to_hls(source, movie_id, "480p")


def convert_720p(source: str, movie_id: int) -> str:
    return convert_resolution_to_hls(source, movie_id, "720p")


def convert_1080p(source: str, movie_id: int) -> str:
    return convert_resolution_to_hls(source, movie_id, "1080p")


def convert_all_resolutions(source: str, movie_id: int) -> dict[str, str]:
    _update_video_tracking(movie_id, "started", progress=5)
    try:
        generated = {}
        generated["480p"] = convert_480p(source, movie_id)
        _update_video_tracking(movie_id, "started", progress=30)
        generated["720p"] = convert_720p(source, movie_id)
        _update_video_tracking(movie_id, "started", progress=55)
        generated["1080p"] = convert_1080p(source, movie_id)
        _update_video_tracking(movie_id, "started", progress=80)
        generated["master"] = _write_master_playlist(movie_id, generated)
        _update_video_tracking(movie_id, "started", progress=90)
        generated["thumbnail"] = generate_thumbnail(source, movie_id)
        _update_video_tracking(movie_id, "finished", thumbnail_url=generated["thumbnail"], progress=100)
        return generated
    except Exception:
        _update_video_tracking(movie_id, "failed")
        raise


def queue_convert_all_resolutions(source: str, movie_id: int, queue_name: str = "default") -> object:
    """
    Enqueue the transcoding task so the web request thread is not blocked.
    Returns the RQ job instance.
    """
    if not getattr(settings, "ENABLE_DJANGO_RQ", False):
        raise QueueUnavailableError("Video queue is disabled.")

    try:
        import django_rq
    except ImportError as exc:
        raise QueueUnavailableError("django_rq is not installed.") from exc

    queue = django_rq.get_queue(queue_name)
    job_timeout = int(getattr(settings, "VIDEO_CONVERSION_JOB_TIMEOUT", 7200))
    try:
        return queue.enqueue(
            convert_all_resolutions,
            source,
            movie_id,
            job_timeout=job_timeout,
        )
    except Exception as exc:
        raise QueueUnavailableError("Video queue is unavailable.") from exc
