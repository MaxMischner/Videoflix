import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from videos.models import Video


class VideoSegmentEndpointTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(VIDEO_STREAM_ROOT=self.temp_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.temp_dir.cleanup)

        self.login_url = "/api/login/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )
        self.video = Video.objects.create(
            title="Movie Title",
            description="Movie Description",
            thumbnail_url="http://example.com/media/thumbnail/image.jpg",
            category="Drama",
        )

    def _authenticate(self):
        login_payload = {
            "email": "user@example.com",
            "password": "securepassword",
        }
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.client.cookies["access_token"] = login_response.cookies["access_token"].value

    def test_segment_returns_200_for_authenticated_user(self):
        self._authenticate()
        resolution = "480p"
        segment_name = "000.ts"
        segment_dir = Path(self.temp_dir.name) / str(self.video.id) / resolution
        segment_dir.mkdir(parents=True, exist_ok=True)
        segment_path = segment_dir / segment_name
        segment_bytes = b"fake-ts-binary"
        segment_path.write_bytes(segment_bytes)

        response = self.client.get(f"/api/video/{self.video.id}/{resolution}/{segment_name}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/MP2T")
        self.assertEqual(response.content, segment_bytes)

    def test_segment_returns_401_without_authentication(self):
        response = self.client.get(f"/api/video/{self.video.id}/480p/000.ts/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_segment_returns_404_if_video_not_found(self):
        self._authenticate()

        response = self.client.get("/api/video/999/480p/000.ts/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video or segment not found."})

    def test_segment_returns_404_if_segment_not_found(self):
        self._authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/480p/000.ts/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video or segment not found."})
