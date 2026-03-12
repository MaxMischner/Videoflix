import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from videos.models import Video


class VideoPlaybackEndpointTests(TestCase):
    def setUp(self):
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
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({"email": "user@example.com", "password": "securepassword"}),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.client.cookies["access_token"] = login_response.cookies["access_token"].value

    def test_playback_returns_resolutions_for_authenticated_user(self):
        self._authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/playback/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["video_id"], self.video.id)
        self.assertEqual(payload["available_resolutions"], ["480p", "720p", "1080p"])
        self.assertEqual(len(payload["qualities"]), 3)
        self.assertEqual(payload["qualities"][0]["resolution"], "480p")
        self.assertEqual(
            payload["qualities"][0]["manifest_url"],
            f"/api/video/{self.video.id}/480p/index.m3u8",
        )

    def test_playback_returns_401_without_authentication(self):
        response = self.client.get(f"/api/video/{self.video.id}/playback/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    def test_playback_returns_404_for_unknown_video(self):
        self._authenticate()

        response = self.client.get("/api/video/999/playback/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video not found."})
