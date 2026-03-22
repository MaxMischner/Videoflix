from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Video
from .serializers import VideoSerializer

HLS_CONTENT_TYPE = 'application/vnd.apple.mpegurl'
TS_CONTENT_TYPE = 'video/MP2T'


def get_hls_file_path(movie_id, resolution, filename):
    """Returns the absolute path to an HLS file."""
    return Path(settings.MEDIA_ROOT) / 'hls' / str(movie_id) / resolution / filename


class VideoListView(APIView):
    """Returns a list of all videos ordered by creation date (newest first)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)


class HLSManifestView(APIView):
    """Serves the HLS master playlist (.m3u8) for a specific video and resolution."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        file_path = get_hls_file_path(movie_id, resolution, 'index.m3u8')
        if not file_path.exists():
            return Response({'detail': 'Video or manifest not found.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(file_path, 'rb'), content_type=HLS_CONTENT_TYPE)


class HLSSegmentView(APIView):
    """Serves a single HLS video segment (.ts) for a specific video and resolution."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        file_path = get_hls_file_path(movie_id, resolution, segment)
        if not file_path.exists():
            return Response({'detail': 'Video or segment not found.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(file_path, 'rb'), content_type=TS_CONTENT_TYPE)
