import json

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.utils.html import format_html

from .functions import refresh_pinterest_video_link
from .models import Country, Tag, Video, VideoCategory


# ---------------------------------------------------------------------------
# Admin branding
# ---------------------------------------------------------------------------

admin.site.site_header = "Video Scraper Control Center"
admin.site.site_title = "Video Scraper Admin"
admin.site.index_title = "Content Management Dashboard"
admin.site.empty_value_display = "—"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_nested(data, *keys, default=None):
    """Safely read nested dictionaries."""
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)

    return current if current is not None else default


# ---------------------------------------------------------------------------
# Video admin
# ---------------------------------------------------------------------------

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thumbnail_preview",
        "short_title",
        "video_type_badge",
        "source_badge",
        "duration_display",
        "active_badge",
        "failure_badge",
        "category_list",
        "created_at",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "short_title",
    )

    list_filter = (
        "video_type",
        "is_active",
        "is_delete",
        "category",
        "country",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "base_url",
    )

    readonly_fields = (
        "id",
        "large_thumbnail_preview",
        "play_video_link",
        "source_information",
        "pretty_video_data",
        "failure_count",
        "created_at",
        "updated_at",
    )

    filter_horizontal = (
        "category",
        "tags",
        "country",
    )

    fieldsets = (
        (
            "Video",
            {
                "fields": (
                    "id",
                    "title",
                    "description",
                    "video_type",
                    "base_url",
                    "play_video_link",
                    "large_thumbnail_preview",
                ),
            },
        ),
        (
            "Pinterest Source",
            {
                "fields": (
                    "source_information",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "video_data",
                    "pretty_video_data",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Organization",
            {
                "fields": (
                    "category",
                    "tags",
                    "country",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "is_delete",
                    "failure_count",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = (
        "refresh_selected_pinterest_links",
        "activate_selected",
        "deactivate_selected",
        "reset_selected_failures",
        "soft_delete_selected",
        "restore_selected",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 30
    save_on_top = True
    preserve_filters = True

    def get_queryset(self, request) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "category",
                "tags",
                "country",
            )
        )

    @admin.display(description="Preview")
    def thumbnail_preview(self, obj):
        thumbnail_url = get_nested(
            obj.video_data,
            "thumbnail",
            "url",
        )

        if not thumbnail_url:
            return format_html(
                '<span style="opacity:.65">{}</span>',
                "No image",
            )

        return format_html(
            '<img src="{}" '
            'style="width:72px;height:72px;object-fit:cover;'
            'border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.18);" '
            'loading="lazy" />',
            thumbnail_url,
        )

    @admin.display(description="Thumbnail")
    def large_thumbnail_preview(self, obj):
        thumbnail_url = get_nested(
            obj.video_data,
            "thumbnail",
            "url",
        )

        if not thumbnail_url:
            return "No thumbnail available."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" '
            'style="max-width:360px;max-height:420px;object-fit:contain;'
            'border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.2);" />'
            "</a>",
            thumbnail_url,
            thumbnail_url,
        )

    @admin.display(description="Title", ordering="title")
    def short_title(self, obj):
        title = obj.title or "Untitled video"
        return title if len(title) <= 55 else f"{title[:52]}..."

    @admin.display(description="Type", ordering="video_type")
    def video_type_badge(self, obj):
        label = obj.get_video_type_display()

        if obj.video_type == "short":
            background = "#7c3aed"
        else:
            background = "#2563eb"

        return format_html(
            '<span style="display:inline-block;padding:4px 9px;'
            'border-radius:999px;background:{};color:white;'
            'font-size:11px;font-weight:700;">{}</span>',
            background,
            label,
        )

    @admin.display(description="Source")
    def source_badge(self, obj):
        platform = get_nested(
            obj.video_data,
            "source",
            "platform",
            default="unknown",
        )
        pin_id = get_nested(
            obj.video_data,
            "source",
            "pin_id",
        )

        label = str(platform).title()

        if pin_id:
            label = f"{label} · {pin_id}"

        return format_html(
            '<span style="font-size:12px;font-weight:600;">{}</span>',
            label,
        )

    @admin.display(description="Source information")
    def source_information(self, obj):
        platform = get_nested(
            obj.video_data,
            "source",
            "platform",
            default="Unknown",
        )
        pin_id = get_nested(
            obj.video_data,
            "source",
            "pin_id",
            default="Not saved",
        )
        pin_url = get_nested(
            obj.video_data,
            "source",
            "pin_url",
        )
        refreshed_at = get_nested(
            obj.video_data,
            "source",
            "last_refreshed_at",
            default="Never",
        )

        pin_url_html = "Not saved"

        if pin_url:
            pin_url_html = format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">'
                "Open original Pin"
                "</a>",
                pin_url,
            )

        return format_html(
            "<div style='line-height:1.9'>"
            "<strong>Platform:</strong> {}<br>"
            "<strong>Pin ID:</strong> {}<br>"
            "<strong>Pin page:</strong> {}<br>"
            "<strong>Last refreshed:</strong> {}"
            "</div>",
            str(platform).title(),
            pin_id,
            pin_url_html,
            refreshed_at,
        )

    @admin.display(description="Duration")
    def duration_display(self, obj):
        duration = get_nested(
            obj.video_data,
            "video_data",
            "duration",
            default=0,
        )

        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = 0

        minutes, seconds = divmod(duration, 60)
        return f"{minutes}:{seconds:02d}"

    @admin.display(description="Status", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_delete:
            return format_html(
                '<span style="color:#dc2626;font-weight:700;">{}</span>',
                "Deleted",
            )

        if obj.is_active:
            return format_html(
                '<span style="color:#15803d;font-weight:700;">{}</span>',
                "● Active",
            )

        return format_html(
            '<span style="color:#d97706;font-weight:700;">{}</span>',
            "● Inactive",
        )

    @admin.display(description="Failures", ordering="failure_count")
    def failure_badge(self, obj):
        count = obj.failure_count or 0

        if count == 0:
            return format_html(
                '<span style="color:#15803d;font-weight:700;">{}</span>',
                0,
            )

        return format_html(
            '<span style="display:inline-block;min-width:22px;text-align:center;'
            'padding:3px 7px;border-radius:999px;background:#fee2e2;'
            'color:#b91c1c;font-weight:800;">{}</span>',
            count,
        )

    @admin.display(description="Categories")
    def category_list(self, obj):
        names = list(
            obj.category.values_list(
                "name",
                flat=True,
            )[:4]
        )

        if not names:
            return "—"

        text = ", ".join(name for name in names if name)
        return text or "—"

    @admin.display(description="Play video")
    def play_video_link(self, obj):
        if not obj.base_url:
            return "No video URL."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" '
            'style="display:inline-block;padding:8px 14px;border-radius:8px;'
            'background:#111827;color:white;font-weight:700;text-decoration:none;">'
            "▶ Open video"
            "</a>",
            obj.base_url,
        )

    @admin.display(description="Formatted video data")
    def pretty_video_data(self, obj):
        try:
            formatted = json.dumps(
                obj.video_data,
                indent=2,
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            formatted = str(obj.video_data)

        return format_html(
            '<pre style="max-width:900px;max-height:480px;overflow:auto;'
            'padding:16px;border-radius:10px;background:#111827;color:#e5e7eb;'
            'font-size:12px;line-height:1.5;">{}</pre>',
            formatted,
        )

    @admin.action(description="Refresh selected Pinterest links")
    def refresh_selected_pinterest_links(self, request, queryset):
        selected_videos = list(
            queryset
            .filter(is_delete=False)
            .order_by("id")[:20]
        )

        refreshed = 0
        active = 0
        failed = 0

        for video in selected_videos:
            try:
                result = refresh_pinterest_video_link(
                    video=video,
                    force=True,
                )

                if result.get("updated"):
                    refreshed += 1
                else:
                    active += 1

            except Exception:
                failed += 1

        if refreshed:
            self.message_user(
                request,
                f"{refreshed} Pinterest link(s) refreshed.",
                level=messages.SUCCESS,
            )

        if active:
            self.message_user(
                request,
                f"{active} link(s) were already active.",
                level=messages.INFO,
            )

        if failed:
            self.message_user(
                request,
                f"{failed} link(s) could not be refreshed.",
                level=messages.ERROR,
            )

        if queryset.count() > 20:
            self.message_user(
                request,
                "Only the first 20 selected videos were processed to avoid an admin timeout.",
                level=messages.WARNING,
            )

    @admin.action(description="Mark selected videos active")
    def activate_selected(self, request, queryset):
        updated = queryset.update(
            is_active=True,
            is_delete=False,
        )
        self.message_user(
            request,
            f"{updated} video(s) activated.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Mark selected videos inactive")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} video(s) deactivated.",
            level=messages.WARNING,
        )

    @admin.action(description="Reset selected failure counters")
    def reset_selected_failures(self, request, queryset):
        updated = queryset.update(
            failure_count=0,
            is_active=True,
        )
        self.message_user(
            request,
            f"Failure counters reset for {updated} video(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Soft-delete selected videos")
    def soft_delete_selected(self, request, queryset):
        updated = queryset.update(
            is_delete=True,
            is_active=False,
        )
        self.message_user(
            request,
            f"{updated} video(s) soft-deleted.",
            level=messages.WARNING,
        )

    @admin.action(description="Restore selected videos")
    def restore_selected(self, request, queryset):
        updated = queryset.update(
            is_delete=False,
            is_active=True,
        )
        self.message_user(
            request,
            f"{updated} video(s) restored.",
            level=messages.SUCCESS,
        )


# ---------------------------------------------------------------------------
# Category admin
# ---------------------------------------------------------------------------

@admin.register(VideoCategory)
class VideoCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "order",
        "is_active",
        "video_count",
        "created_at",
        "updated_at",
    )
    list_editable = (
        "order",
        "is_active",
    )
    list_filter = (
        "is_active",
        "created_at",
    )
    search_fields = ("name",)
    ordering = (
        "order",
        "name",
    )
    list_per_page = 30

    @admin.display(description="Videos")
    def video_count(self, obj):
        return obj.video_set.count()


# ---------------------------------------------------------------------------
# Tag admin
# ---------------------------------------------------------------------------

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_active",
        "video_count",
        "created_at",
    )
    list_editable = ("is_active",)
    list_filter = (
        "is_active",
        "created_at",
    )
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50

    @admin.display(description="Videos")
    def video_count(self, obj):
        return obj.video_set.count()


# ---------------------------------------------------------------------------
# Country admin
# ---------------------------------------------------------------------------

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "is_active",
        "video_count",
    )
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "code",
    )
    ordering = ("name",)
    list_per_page = 50

    @admin.display(description="Videos")
    def video_count(self, obj):
        return obj.video_set.count()