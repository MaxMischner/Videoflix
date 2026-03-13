import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from videos.models import Video


class VideoConvertStatusEndpointTests(TestCase):
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
        self.status_url = f"/api/video/{self.video.id}/convert/status/"

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

    def test_status_returns_401_without_authentication(self):
        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_status_returns_404_for_missing_video(self):
        self._authenticate()

        response = self.client.get("/api/video/999/convert/status/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video not found."})

    def test_status_returns_not_requested_when_no_job_exists(self):
        self._authenticate()

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["video_id"], self.video.id)
        self.assertIsNone(response.json()["job_id"])
        self.assertEqual(response.json()["status"], "not_requested")
        self.assertEqual(response.json()["progress"], 0)

    @patch("videos.views._get_rq_job_status")
    def test_status_updates_video_status_from_rq(self, rq_status_mock):
        self._authenticate()
        self.video.last_conversion_job_id = "job-123"
        self.video.conversion_status = "queued"
        self.video.save(update_fields=["last_conversion_job_id", "conversion_status", "conversion_updated_at"])

        rq_status_mock.return_value = "finished"

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], "job-123")
        self.assertEqual(response.json()["status"], "finished")
        self.assertEqual(response.json()["progress"], 0)

        self.video.refresh_from_db()
        self.assertEqual(self.video.conversion_status, "finished")
