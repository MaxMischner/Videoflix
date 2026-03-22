"""
Tests for all video API endpoints.
Checks exact response bodies as specified in the API documentation.
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Video

User = get_user_model()

VIDEO_LIST_URL = '/api/video/'
HLS_MANIFEST_URL = '/api/video/{id}/{resolution}/index.m3u8'
HLS_SEGMENT_URL = '/api/video/{id}/{resolution}/{segment}/'


def create_active_user(email='video@test.com', password='Test1234!'):
    """Helper: creates and returns an active user."""
    return User.objects.create_user(email=email, password=password, is_active=True)


def set_auth_cookie(client, user):
    """Helper: sets JWT access_token cookie on the test client."""
    refresh = RefreshToken.for_user(user)
    client.cookies['access_token'] = str(refresh.access_token)


class VideoListViewTests(APITestCase):
    """GET /api/video/"""

    def setUp(self):
        self.user = create_active_user()

    def test_unauthenticated_returns_401(self):
        response = self.client.get(VIDEO_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_returns_200_with_list(self):
        set_auth_cookie(self.client, self.user)
        response = self.client.get(VIDEO_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_response_contains_required_fields(self):
        Video.objects.create(title='Test', description='Desc', category='Drama', video_file='uploads/test.mp4')
        set_auth_cookie(self.client, self.user)
        response = self.client.get(VIDEO_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        video = response.data[0]
        self.assertIn('id', video)
        self.assertIn('created_at', video)
        self.assertIn('title', video)
        self.assertIn('description', video)
        self.assertIn('thumbnail_url', video)
        self.assertIn('category', video)

    def test_videos_ordered_by_created_at_desc(self):
        Video.objects.create(title='First', category='Drama', video_file='uploads/a.mp4')
        Video.objects.create(title='Second', category='Action', video_file='uploads/b.mp4')
        set_auth_cookie(self.client, self.user)
        response = self.client.get(VIDEO_LIST_URL)
        self.assertEqual(response.data[0]['title'], 'Second')
        self.assertEqual(response.data[1]['title'], 'First')

    def test_empty_list_returns_200_with_empty_array(self):
        set_auth_cookie(self.client, self.user)
        response = self.client.get(VIDEO_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class HLSManifestViewTests(APITestCase):
    """GET /api/video/<int:movie_id>/<str:resolution>/index.m3u8"""

    def setUp(self):
        self.user = create_active_user()
        self.video = Video.objects.create(title='Test', category='Drama', video_file='uploads/test.mp4')

    def test_unauthenticated_returns_401(self):
        url = HLS_MANIFEST_URL.format(id=self.video.pk, resolution='480p')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_file_returns_404(self):
        set_auth_cookie(self.client, self.user)
        url = HLS_MANIFEST_URL.format(id=self.video.pk, resolution='480p')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_manifest_returns_200_with_correct_content_type(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            hls_dir = Path(tmp_dir) / 'hls' / str(self.video.pk) / '480p'
            hls_dir.mkdir(parents=True)
            manifest = hls_dir / 'index.m3u8'
            manifest.write_text('#EXTM3U\n#EXT-X-VERSION:3\n')
            with override_settings(MEDIA_ROOT=tmp_dir):
                set_auth_cookie(self.client, self.user)
                url = HLS_MANIFEST_URL.format(id=self.video.pk, resolution='480p')
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response['Content-Type'], 'application/vnd.apple.mpegurl')

    def test_all_resolutions_accessible(self):
        for resolution in ['480p', '720p', '1080p']:
            set_auth_cookie(self.client, self.user)
            url = HLS_MANIFEST_URL.format(id=self.video.pk, resolution=resolution)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HLSSegmentViewTests(APITestCase):
    """GET /api/video/<int:movie_id>/<str:resolution>/<str:segment>/"""

    def setUp(self):
        self.user = create_active_user()
        self.video = Video.objects.create(title='Test', category='Drama', video_file='uploads/test.mp4')

    def test_unauthenticated_returns_401(self):
        url = HLS_SEGMENT_URL.format(id=self.video.pk, resolution='480p', segment='000.ts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_segment_returns_404(self):
        set_auth_cookie(self.client, self.user)
        url = HLS_SEGMENT_URL.format(id=self.video.pk, resolution='480p', segment='000.ts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_segment_returns_200_with_correct_content_type(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            hls_dir = Path(tmp_dir) / 'hls' / str(self.video.pk) / '480p'
            hls_dir.mkdir(parents=True)
            segment = hls_dir / '000.ts'
            segment.write_bytes(b'\x00' * 100)
            with override_settings(MEDIA_ROOT=tmp_dir):
                set_auth_cookie(self.client, self.user)
                url = HLS_SEGMENT_URL.format(id=self.video.pk, resolution='480p', segment='000.ts')
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response['Content-Type'], 'video/MP2T')
