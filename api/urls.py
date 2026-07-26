from django.urls import path

from api.views import (
    RefreshPinterestVideos,
    ResolvePinterestVideoLink,
    ScrapePinterestVideos, LatestVideo, CategoryList, TagList,
)


urlpatterns = [
    path("pinterest/scrape/",ScrapePinterestVideos.as_view(),name="pinterest-scrape",),
    path("pinterest/refresh/",RefreshPinterestVideos.as_view(),name="pinterest-refresh",),
    path("pinterest/videos/<int:video_id>/resolve/",ResolvePinterestVideoLink.as_view(),name="pinterest-video-resolve",),

    path('videos/latest', LatestVideo.as_view()),
    path('categories', CategoryList.as_view()),
    path('tags', TagList.as_view()),

]