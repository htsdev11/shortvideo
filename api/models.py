from django.db import models

# Create your models here.
from django.db import models
from django.db.models import F
from django.utils import timezone


class VideoCategory(models.Model):
    name = models.CharField(max_length=300,blank=True,null=True,)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now,blank=True,null=True,)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or ""


class Country(models.Model):
    name = models.CharField(max_length=300, blank=True)
    code = models.CharField(max_length=4, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name or ""


class Tag(models.Model):
    name = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now,blank=True,null=True,)

    def __str__(self):
        return self.name or ""


class Video(models.Model):
    STATUS_CHOICES = (
        ("short", "Short"),
        ("video", "Video"),
    )

    title = models.CharField(max_length=500,blank=True,)
    description = models.TextField(blank=True,null=True,)
    video_data = models.JSONField(default=dict,blank=True,)
    # Pinterest CDN URLs can be longer than Django's
    # default URLField length of 200.
    base_url = models.URLField(max_length=2048, blank=True,null=True,)
    video_type = models.CharField(max_length=20,choices=STATUS_CHOICES,default="short",)
    category = models.ManyToManyField(VideoCategory,blank=True,)
    tags = models.ManyToManyField(Tag,blank=True,)
    country = models.ManyToManyField(Country,blank=True,)
    failure_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now,blank=True,null=True,)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Video {self.pk}"

    def increment_failure(self):
        """
        Atomically increment failure_count.
        """
        Video.objects.filter(pk=self.pk).update(
            failure_count=F("failure_count") + 1,
            updated_at=timezone.now(),
        )

        self.refresh_from_db(
            fields=["failure_count"]
        )

        return self.failure_count

    def get_pinterest_pin_id(self):
        """
        Return the Pinterest Pin ID saved in video_data.
        """
        source = (
            self.video_data.get("source", {})
            if isinstance(self.video_data, dict)
            else {}
        )

        return source.get("pin_id")

    def get_pinterest_pin_url(self):
        source = (
            self.video_data.get("source", {})
            if isinstance(self.video_data, dict)
            else {}
        )

        return source.get("pin_url")