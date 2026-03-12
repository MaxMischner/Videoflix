import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from videos.models import Video
from videos.tasks import convert_all_resolutions


class VideoTasksTests(TestCase):
    @override_settings(
        VIDEO_STREAM_ROOT=tempfile.gettempdir(),
        MEDIA_ROOT=tempfile.gettempdir(),
        MEDIA_URL="/media/",
        PUBLIC_BASE_URL="http://127.0.0.1:8000",
    )
    @patch("videos.tasks.subprocess.run")
    def test_convert_all_resolutions_updates_status_and_thumbnail_url(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr="")

        video = Video.objects.create(
            title="Task Test Movie",
            description="Task test description",
            thumbnail_url="http://example.com/old-thumb.jpg",
            category="Drama",
        )

        source = str(Path(tempfile.gettempdir()) / "source.mp4")
        result = convert_all_resolutions(source, video.id)

        self.assertIn("master", result)
        self.assertIn("thumbnail", result)

        video.refresh_from_db()
        self.assertEqual(video.conversion_status, "finished")
        self.assertIn(f"/media/{video.id}/thumbnail.jpg", video.thumbnail_url)

    @override_settings(VIDEO_STREAM_ROOT=tempfile.gettempdir())
    @patch("videos.tasks.convert_480p", side_effect=RuntimeError("ffmpeg failed"))
    def test_convert_all_resolutions_marks_failed_on_error(self, _):
        video = Video.objects.create(
            title="Task Fail Movie",
            description="Task fail description",
            thumbnail_url="http://example.com/old-thumb.jpg",
            category="Drama",
        )

        with self.assertRaises(RuntimeError):
            convert_all_resolutions("broken.mp4", video.id)

        video.refresh_from_db()
        self.assertEqual(video.conversion_status, "failed")
