from rest_framework import serializers
from api.models import *


class VideoCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCategory
        fields = ['id', 'name', 'order', 'is_active']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'is_active']


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'is_active']


class VideoSerializer(serializers.ModelSerializer):
    country = CountrySerializer(required=False, many=True)
    category = VideoCategorySerializer(required=False, many=True)
    tags = TagSerializer(required=False, many=True)

    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'video_data',
            'base_url', 'video_type', "category",
            "tags", "country", 'is_active', 'is_delete'

        ]
