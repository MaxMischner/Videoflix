import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from videos.models import Video


class VideoDashboardEndpointTests(TestCase):
    def setUp(self):
        self.login_url = "/api/login/"
        self.dashboard_url = "/api/video/dashboard/"
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="securepassword",
            is_active=True,
        )

        Video.objects.create(
            title="Drama One",
            description="Drama Description",
            thumbnail_url="http://example.com/media/thumbnail/drama.jpg",
            category="Drama",
        )
        Video.objects.create(
            title="Action One",
            description="Action Description",
            thumbnail_url="http://example.com/media/thumbnail/action.jpg",
            category="Action",
        )
        Video.objects.create(
            title="Drama Two",
            description="Drama Description 2",
            thumbnail_url="http://example.com/media/thumbnail/drama2.jpg",
            category="Drama",
        )

    def _authenticate(self):
        response = self.client.post(
            self.login_url,
            data=json.dumps({"email": "user@example.com", "password": "securepassword"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.cookies["access_token"] = response.cookies["access_token"].value

    def test_dashboard_returns_hero_and_genre_groups_for_authenticated_user(self):
        self._authenticate()

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("hero", data)
        self.assertIn("genres", data)

        self.assertEqual(data["hero"]["title"], "Drama Two")
        self.assertEqual(data["hero"]["category"], "Drama")

        genres = {entry["genre"]: entry["videos"] for entry in data["genres"]}
        self.assertIn("Drama", genres)
        self.assertIn("Action", genres)
        self.assertEqual(len(genres["Drama"]), 2)
        self.assertEqual(genres["Drama"][0]["title"], "Drama Two")
        self.assertEqual(genres["Drama"][1]["title"], "Drama One")

    def test_dashboard_returns_401_without_authentication(self):
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )
