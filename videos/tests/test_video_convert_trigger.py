import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from videos.models import MediaFile, Video
from videos.utils import ConversionAlreadyQueuedError, QueueUnavailableError, queue_conversion_for_video


class VideoConvertTriggerEndpointTests(TestCase):
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
        self.convert_url = f"/api/video/{self.video.id}/convert/"

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

    def test_trigger_returns_401_without_authentication(self):
        response = self.client.post(self.convert_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_trigger_returns_404_if_video_not_found(self):
        self._authenticate()
        response = self.client.post("/api/video/999/convert/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Video not found."})

    def test_trigger_returns_404_if_media_file_missing(self):
        self._authenticate()
        response = self.client.post(self.convert_url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source media file not found."})

    @patch("videos.views.queue_convert_all_resolutions")
    def test_trigger_queues_job_and_returns_202(self, queue_mock):
        self._authenticate()

        media_file = MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("source.mp4", b"fake-video"),
        )

        job = Mock()
        job.id = "job-123"
        queue_mock.return_value = job

        response = self.client.post(self.convert_url)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["detail"], "Video conversion queued.")
        self.assertEqual(response.json()["job_id"], "job-123")
        self.assertEqual(response.json()["video_id"], self.video.id)
        queue_mock.assert_called_once_with(media_file.file.path, self.video.id, queue_name="default")

        self.video.refresh_from_db()
        self.assertEqual(self.video.last_conversion_job_id, "job-123")
        self.assertEqual(self.video.conversion_status, "queued")
        self.assertEqual(self.video.conversion_progress, 0)

    @patch("videos.views.queue_conversion_for_video", side_effect=ConversionAlreadyQueuedError("already"))
    def test_trigger_returns_409_when_conversion_already_running(self, _):
        self._authenticate()
        MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("source.mp4", b"fake-video"),
        )

        response = self.client.post(self.convert_url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Video conversion is already in progress."})

    @patch("videos.views.queue_conversion_for_video", side_effect=QueueUnavailableError("down"))
    def test_trigger_returns_503_when_queue_unavailable(self, _):
        self._authenticate()
        MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("source.mp4", b"fake-video"),
        )

        response = self.client.post(self.convert_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Video conversion queue is unavailable."})


class QueueConversionHelperTests(TestCase):
    def setUp(self):
        self.video = Video.objects.create(
            title="Queue Helper Test",
            description="Queue helper test description",
            thumbnail_url="http://example.com/media/thumbnail/image.jpg",
            category="Drama",
            conversion_status="queued",
            last_conversion_job_id="job-old",
        )
        self.media_file = MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("source.mp4", b"fake-video"),
        )

    @patch("videos.utils.get_rq_job_status", return_value="started")
    def test_helper_blocks_requeue_when_job_is_still_active(self, _status_mock):
        with self.assertRaises(ConversionAlreadyQueuedError):
            queue_conversion_for_video(self.video, self.media_file, queue_func=Mock())

    @patch("videos.utils.get_rq_job_status", return_value="finished")
    def test_helper_requeues_when_previous_job_finished(self, _status_mock):
        new_job = Mock()
        new_job.id = "job-new"

        result = queue_conversion_for_video(self.video, self.media_file, queue_func=Mock(return_value=new_job))

        self.assertEqual(result.id, "job-new")
        self.video.refresh_from_db()
        self.assertEqual(self.video.last_conversion_job_id, "job-new")
        self.assertEqual(self.video.conversion_status, "queued")
        self.assertEqual(self.video.conversion_progress, 0)
