import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from videos.models import Video


class VideoManifestEndpointTests(TestCase):
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
        self.client.cookies["refresh_token"] = login_response.cookies["refresh_token"].value

    def test_manifest_returns_200_for_authenticated_user(self):
        self._authenticate()
        resolution = "480p"
        manifest_dir = Path(self.temp_dir.name) / str(self.video.id) / resolution
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "index.m3u8"
        manifest_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
        manifest_path.write_text(manifest_content, encoding="utf-8")

        response = self.client.get(f"/api/video/{self.video.id}/{resolution}/index.m3u8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.apple.mpegurl")
        self.assertEqual(response.content.decode("utf-8"), manifest_content)

    def test_manifest_returns_401_without_authentication(self):
        response = self.client.get(f"/api/video/{self.video.id}/480p/index.m3u8")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_manifest_returns_404_if_video_not_found(self):
        self._authenticate()

        response = self.client.get("/api/video/999/480p/index.m3u8")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video or manifest not found."})

    def test_manifest_returns_404_if_file_not_found(self):
        self._authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/720p/index.m3u8")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video or manifest not found."})

    def test_manifest_allows_valid_refresh_token_without_access_token(self):
        self._authenticate()
        self.client.cookies.pop("access_token", None)

        resolution = "480p"
        manifest_dir = Path(self.temp_dir.name) / str(self.video.id) / resolution
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
        (manifest_dir / "index.m3u8").write_text(manifest_content, encoding="utf-8")

        response = self.client.get(f"/api/video/{self.video.id}/{resolution}/index.m3u8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), manifest_content)
