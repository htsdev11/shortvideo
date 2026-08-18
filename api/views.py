from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .service import (
    PinterestScraperError,
    parse_boolean,
    refresh_expired_pinterest_videos,
    refresh_pinterest_video_link,
    scrape_and_save_pinterest_videos,
)
from .models import Video, VideoCategory, Tag
from .pagination import CustomPagination
from .serializers import VideoSerializer, VideoCategorySerializer, TagSerializer


# class ScrapePinterestVideos(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         try:
#             query = (
#                 request.data.get("query")
#                 or request.data.get("secondary")
#             )
#
#             num_scrape = request.data.get("to_scrape", 10)
#
#             category_name = (
#                 request.data.get("category")
#                 or request.data.get("video_type")
#                 or "Video"
#             )
#
#             category, _ = VideoCategory.objects.get_or_create(
#                 name=str(category_name).capitalize()
#             )
#
#             # Do not read the Pinterest cookie from request.data or settings.
#             # functions.py will use its internal PINTEREST_COOKIE constant.
#             result = scrape_and_save_pinterest_videos(
#                 query=query,
#                 num_scrape=num_scrape,
#                 cookie_header=None,
#                 category=category,
#                 assign_all_countries=parse_boolean(
#                     request.data.get(
#                         "assign_all_countries",
#                         True,
#                     )
#                 ),
#                 verify_urls=parse_boolean(
#                     request.data.get(
#                         "verify_urls",
#                         False,
#                     )
#                 ),
#             )
#
#             return Response(
#                 {
#                     "status": "success",
#                     "message": None,
#                     "data": result,
#                 },
#                 status=status.HTTP_201_CREATED,
#             )
#
#         except PinterestScraperError as exc:
#             return Response(
#                 {
#                     "status": "failed",
#                     "message": str(exc),
#                     "data": None,
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#
#         except Exception as exc:
#             return Response(
#                 {
#                     "status": "failed",
#                     "message": str(exc),
#                     "data": None,
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

class ScrapePinterestVideos(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            query = (
                request.data.get("query")
                or request.data.get("secondary")
            )

            if not query:
                return Response(
                    {
                        "status": "failed",
                        "message": "query is required.",
                        "data": None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                num_scrape = int(
                    request.data.get("to_scrape", 10)
                )
            except (TypeError, ValueError):
                num_scrape = 10

            # Optional safety limit
            num_scrape = max(1, min(num_scrape, 100))

            category_name = (
                request.data.get("category")
                or request.data.get("video_type")
                or "Video"
            )

            category, _ = VideoCategory.objects.get_or_create(
                name=str(category_name).capitalize()
            )

            result = scrape_and_save_pinterest_videos(
                query=query,
                num_scrape=num_scrape,
                cookie_header=None,
                category=category,

                assign_all_countries=parse_boolean(
                    request.data.get(
                        "assign_all_countries",
                        True,
                    )
                ),

                verify_urls=parse_boolean(
                    request.data.get(
                        "verify_urls",
                        False,
                    )
                ),

                allow_hls_fallback=True,
            )

            return Response(
                {
                    "status": "success",
                    "message": None,
                    "data": result,
                },
                status=status.HTTP_201_CREATED,
            )

        except PinterestScraperError as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class RefreshPinterestVideos(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            video_id = request.data.get("video_id")
            force = parse_boolean(
                request.data.get("force", False)
            )

            # Refresh one video.
            if video_id:
                video = get_object_or_404(
                    Video,
                    pk=video_id,
                    is_delete=False,
                )

                result = refresh_pinterest_video_link(
                    video=video,
                    cookie_header=None,
                    force=force,
                )

                return Response(
                    {
                        "status": "success",
                        "message": None,
                        "data": result,
                    },
                    status=status.HTTP_200_OK,
                )

            # Refresh all Pinterest videos.
            result = refresh_expired_pinterest_videos(
                cookie_header=None,
                limit=request.data.get("limit"),
                force=force,
            )

            return Response(
                {
                    "status": "success",
                    "message": None,
                    "data": result,
                },
                status=status.HTTP_200_OK,
            )

        except PinterestScraperError as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResolvePinterestVideoLink(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, video_id):
        try:
            video = get_object_or_404(
                Video,
                pk=video_id,
                is_delete=False,
            )

            result = refresh_pinterest_video_link(
                video=video,
                cookie_header=None,
                force=False,
            )

            current_url = (
                result.get("new_url")
                or result.get("url")
                or video.base_url
            )

            return Response(
                {
                    "status": "success",
                    "message": None,
                    "data": {
                        "video_id": video.pk,
                        "video_url": current_url,
                        "was_refreshed": result.get(
                            "updated",
                            False,
                        ),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except PinterestScraperError as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            return Response(
                {
                    "status": "failed",
                    "message": str(exc),
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CategoryList(APIView, CustomPagination):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        try:
            data = request.GET

            categories = VideoCategory.objects.filter(is_active=True, video__gte=1).order_by("order").distinct()
            paginated_categories = self.paginate_queryset(categories, request)
            serializer = VideoCategorySerializer(paginated_categories, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            print(f"{e}")
            return self.get_failed_paginated_response("Something went wrong!", status.HTTP_400_BAD_REQUEST)


class TagList(APIView, CustomPagination):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        try:
            data = request.GET

            tags = Tag.objects.filter(is_active=True)
            paginated_tags = self.paginate_queryset(tags, request)
            serializer = TagSerializer(paginated_tags, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            print(f"{e}")
            return self.get_failed_paginated_response("Something went wrong!", status.HTTP_400_BAD_REQUEST)



class LatestVideo(APIView, CustomPagination):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        try:
            # data = request.GET

            videos = Video.objects.filter(is_delete=False, is_active=True).order_by('?')
            paginated_videos = self.paginate_queryset(videos, request)
            serializer = VideoSerializer(paginated_videos, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            print(f"{e}")
            return self.get_failed_paginated_response("Something went wrong!", status.HTTP_400_BAD_REQUEST)