import subprocess
from pathlib import Path

from django.conf import settings


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


def _get_hls_base_dir(movie_id: int) -> Path:
    base_dir = Path(getattr(settings, "VIDEO_STREAM_ROOT", settings.BASE_DIR / "media" / "video"))
    output_dir = base_dir / str(movie_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _build_resolution_output_dir(movie_id: int, resolution: str) -> Path:
    output_dir = _get_hls_base_dir(movie_id) / resolution
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _update_video_tracking(movie_id: int, status: str, thumbnail_url: str | None = None) -> None:
    from .models import Video

    video = Video.objects.filter(pk=movie_id).first()
    if not video:
        return

    video.conversion_status = status
    update_fields = ["conversion_status", "conversion_updated_at"]

    if thumbnail_url is not None:
        video.thumbnail_url = thumbnail_url
        update_fields.append("thumbnail_url")

    video.save(update_fields=update_fields)


def _run_ffmpeg_hls(source: str, output_dir: Path, height: int, maxrate: str, bufsize: str) -> subprocess.CompletedProcess:
    segment_pattern = str(output_dir / "%03d.ts")
    playlist_path = str(output_dir / "index.m3u8")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        source,
        "-vf",
        f"scale=-2:{height}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-g",
        "48",
        "-keyint_min",
        "48",
        "-sc_threshold",
        "0",
        "-maxrate",
        maxrate,
        "-bufsize",
        bufsize,
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
        "-hls_segment_filename",
        segment_pattern,
        "-f",
        "hls",
        playlist_path,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _run_ffmpeg_thumbnail(source: str, target: Path) -> subprocess.CompletedProcess:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:03",
        "-i",
        source,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(target),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def convert_resolution_to_hls(source: str, movie_id: int, resolution: str) -> str:
    if resolution not in HLS_PROFILES:
        raise ValueError(f"Unsupported resolution: {resolution}")

    profile = HLS_PROFILES[resolution]
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


def _write_master_playlist(movie_id: int, generated: dict[str, str]) -> str:
    base_dir = _get_hls_base_dir(movie_id)
    master_path = base_dir / "master.m3u8"

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for resolution in ["480p", "720p", "1080p"]:
        if resolution not in generated:
            continue

        profile = HLS_PROFILES[resolution]
        width = int(round(profile["height"] * 16 / 9))
        lines.append(
            f"#EXT-X-STREAM-INF:BANDWIDTH={profile['bandwidth']},RESOLUTION={width}x{profile['height']}"
        )
        lines.append(f"{resolution}/index.m3u8")

    master_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(master_path)


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
    _update_video_tracking(movie_id, "started")
    try:
        generated = {
            "480p": convert_480p(source, movie_id),
            "720p": convert_720p(source, movie_id),
            "1080p": convert_1080p(source, movie_id),
        }
        generated["master"] = _write_master_playlist(movie_id, generated)
        generated["thumbnail"] = generate_thumbnail(source, movie_id)
        _update_video_tracking(movie_id, "finished", thumbnail_url=generated["thumbnail"])
        return generated
    except Exception:
        _update_video_tracking(movie_id, "failed")
        raise

def queue_convert_all_resolutions(source: str, movie_id: int, queue_name: str = "default"):
    """
    Enqueue the transcoding task so the web request thread is not blocked.
    Returns the RQ job instance.
    """
    import django_rq

    queue = django_rq.get_queue(queue_name)
    return queue.enqueue(convert_all_resolutions, source, movie_id)
