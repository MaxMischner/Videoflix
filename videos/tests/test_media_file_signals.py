import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from videos.models import MediaFile, Video


class MediaFileSignalsTests(TestCase):
    def setUp(self):
        self.video = Video.objects.create(
            title="Signal Test Movie",
            description="Signal test description",
            thumbnail_url="http://example.com/thumb.jpg",
            category="Drama",
        )

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_delete_removes_file_from_filesystem(self):
        media = MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("delete_me.txt", b"to be deleted"),
        )
        file_path = Path(media.file.path)
        self.assertTrue(file_path.exists())

        media.delete()

        self.assertFalse(file_path.exists())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_pre_save_removes_old_file_when_file_changes(self):
        media = MediaFile.objects.create(
            video=self.video,
            file=SimpleUploadedFile("old_file.txt", b"old content"),
        )
        old_path = Path(media.file.path)
        self.assertTrue(old_path.exists())

        media.file = SimpleUploadedFile("new_file.txt", b"new content")
        media.save()

        self.assertFalse(old_path.exists())
        self.assertTrue(Path(media.file.path).exists())
