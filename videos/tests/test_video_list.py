import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from videos.models import Video


class VideoListEndpointTests(TestCase):
    def setUp(self):
        self.login_url = "/api/login/"
        self.video_url = "/api/video/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

        Video.objects.create(
            title="Movie Title",
            description="Movie Description",
            thumbnail_url="http://example.com/media/thumbnail/image.jpg",
            category="Drama",
        )
        Video.objects.create(
            title="Another Movie",
            description="Another Description",
            thumbnail_url="http://example.com/media/thumbnail/image2.jpg",
            category="Romance",
        )

    def test_video_list_returns_200_for_authenticated_user(self):
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

        access_token = login_response.cookies["access_token"].value
        self.client.cookies["access_token"] = access_token

        response = self.client.get(self.video_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["title"], "Movie Title")
        self.assertEqual(data[0]["description"], "Movie Description")
        self.assertEqual(data[0]["thumbnail_url"], "http://example.com/media/thumbnail/image.jpg")
        self.assertEqual(data[0]["category"], "Drama")
        self.assertIn("created_at", data[0])

    def test_video_list_returns_401_without_authentication(self):
        response = self.client.get(self.video_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})
