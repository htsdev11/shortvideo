import json
import os
import re
from copy import deepcopy
from http.cookies import SimpleCookie
from urllib.parse import quote_plus, urlparse
from typing import Any, Dict, Iterable, List, Optional, Sequence
import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from api.models import (
    Country,
    Tag,
    Video,
    VideoCategory,
)


PINTEREST_SEARCH_ENDPOINT = (
    "https://www.pinterest.com/"
    "resource/BaseSearchResource/get/"
)

PINTEREST_PIN_ENDPOINT = (
    "https://www.pinterest.com/"
    "resource/PinResource/get/"
)

PINTEREST_BASE_URL = "https://www.pinterest.com"

REQUEST_TIMEOUT = (5, 15)  # Keep below common Gunicorn 30s timeout

# Direct MP4 targets for fast-start reel playback. The scraper does not
# download, transcode, mirror, or upload video files. It only saves links.
REEL_TARGET_SHORT_SIDE = 720
REEL_TARGET_LONG_SIDE = 1280
REEL_TARGET_BITRATE = 2_000_000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Pinterest authentication must be supplied by the server environment.
# Never commit a live Pinterest session cookie to source control.
# PINTEREST_COOKIE = os.environ.get("PINTEREST_COOKIE", "").strip()

PINTEREST_COOKIE = """
csrftoken=eba2d6df553f58593eaa1a207dbfa3b7; _routing_id="4634f3bc-5cbb-46da-a877-83daeaaafcf7"; sessionFunnelEventLogged=1; _b="AZYZDZZpwFBMKohlvJxroYMpwkYBCfON9CmdS5bqGzm0nR1e497NBd/BtROxRLUjMNM="; _auth=1; _pinterest_sess=TWc9PSZJZ0szcmduNFhiN1JZdjg4N1J4YXZuYWZvYXk3ejBzOXZLWjlKSzFOTHBVbkQrQjZ4clQyMjI1NXNPck1LOVoyeDB4S0o3dW5yd1JuQ1lPZTNuak81ZzNSZ3JjTVFhUTJseHg2cDBQNVVBa250ZnhZNmtvYTMrTVQzUGZxbjAvMVVHKy9DTFBQMWZlcDk4QXNGNzM3bjRLem4wa2RRcS9iYm5GVEI1cERwVHgyR2NQZVk2MDFNYXlZWnpQK3FVemF4T21wa0JFUGZ1cExiZUZ5SWF4eUltSFMyeTQ4Q3hHUy91UWtlSkJtQ25PUVVEY0krSGZOQ1lMYkorSkkreGJPdWpLSzQ3akZvMzNHUkpwNmY3VDc5TThmb1h4cnZ2cno1aWR1REpXd1BsbUFIWEZhcnlJcFk2NlhIc1crWDRieGVUWXlSbU9sbE43Z2NPdkpGQzN5NjBBeWkvckhUblo1em80R21Za0VhdVR2eUdEVmxkbzdSRCtZeFl4ZmpQNDYwb3VVTkRXd2dPNjVmV096NTJ6ZDUreElhVno3M3VndUorMUdtQXpYOURlNlg4RnpoN05GdEd5ZmtuaGVoS1F1ODBWOW5oWkdLTHFEUkNPUmNRU3V3VkFaN0IzbmVUMWtESGdXdXl1NUl2MjZYYjRnOUFQUnhoOU81Y1BEUzNaeEFrYTlDTUdiRDVtcnY1RWo0Q1k0WGJmcnU4TnRxNG1RYWNvNklsRTNoY20xUkZNN2RvU2F5SDlscVlmS0s4WXJ6VmVUYlQzSGw5SVdIOVpBYXhuQ3F6and6QlpITzFXNUVpMVRlNWUvSXYycFh3cktOZmx2NGtzdEozYzVyZWcwQ2s4Q3lzU0xiVkpUMG56cjVHNllvTzVtYjR1OEZueFJSQkVaRUVSSTIrOTR3MTVXaysyTzdLRCtoZkxNczNadU1rSGZlNVJFQ3ZxMVRxV1VZSmJJb0x5V1VHeDZncS9SdHVGV28yZjgwYVhabCt2TllwWTV5dnozNTZSM01vSTRVWktPcTdXZTVQTDNEVzZwT0FDbmcvNUdCYnQrdHpMZnZJL2FKaEZDLzc4ZVpUaDBsbnhCMFJ0Z0dBbktEM3QwNGJwck5DMGZ5dWovMVQ0aktvUk11STV6MHRMa3JUR1htRmVTOTRJR200L0s3emR1QnVtQUFJZVVaNXYra1ZMYTFVWTVIN1lDZ2JNc2hZTVc1WjRuZUlRVk5OanFPMzZrYWUvM0MyaTVuWWhwdmE1QVRYbm9GcGthTDFDYVVIbUM5YzY5NTBrR3ZqeHhhSFVsUUNnY244VzE1TXpvM25IMDRYUU01UVRlamN5THkzR1VIaW4rbVpDd1g2N2FoWmlWU1BmUFVpK1JsZllwSWM2OXNCOGhkSHhXZnc1RkcrWTRUR3FSS05GWHRQeGdvb1VjOXIxaEtaSzBsRFhTRWpIcVhvR1BvbndsRkxHbkYyRWZML2VoQVl2cGkwUG91WlBCKzErQm5vUzhYWjBJTWdKT1FPaHhxYzF5eFgrV25xQTVSOU5kM0JzRFNSVTZjNW5Fczl3RmR2S0hhS2RZS09nblhqWlFhc0FublJLQkVXQ0xJdVFDRkFGSDAxaktlZDBLWTJNZkcxWXlOcjFzNmMvbnVBQXl1QmVnbC9ta2FWRDZKNUI3V1NFREZWOTVjZW1WcWEwY1BXNDdjTjkzbDlPZEdWNk9PUnlKQ1hQTHNUbXZKVmVrQ2pVOUNLMVN5RWR2bGlWS1JDeGxwcTZmaUtkTzg2THdRVUNUUzNKSE82TFgmclNWTTRoVkVGOHIrRmpiSTRuVC9CV1paNHFRPQ==; __Secure-s_a=aEZMd0VZN2xLbTlvaFFKNFlWaGozVUgrL0s4QmlITEM1Ym8wOE5LSHZoTnMvL09Rb0NjVUpLNkp2eWo4K2dyOXRjWFdQNG9QSzJ1Z2xUVmFCSFlBZk9tclNOd0x3NXFLaEZLNWkxWnFmemVxakV0SVowa2JIZ3lQOUpEc21SUmk2UytwUWFCSU9qNnduK2ZDelJvaUxiR3YzWERXZTdlR08wRVdtWEpEaXdyeGFrWTdLYk84eVQ0YXJZUTFGeHFuQ3prd3ZObmtXSmU2YWl6L01iOXZKd3JHc1VmUHVhaTdBWklzUGRRaXZaaExYMEt2ZFBQWTZUdjk3cjZYeVBGeWFWdlVsbVdYbmlsSEZqVmRqcjVUN2hlNHJsSldPUUtvMG1aaURhdnFlemZLUWZ1VXdHMWlXMFo0SUNrL2ZUSXZjT2ZVS1VMSmUzVXNUZ0Z3OGthc3U2eTE4dzRiR3NtaVB1bHdJYUNjVDFPUDhVRFpJTmp0L0JPWk44LzMxVEhMQmxKUUVPNmx0dWRLTWhlNGVhRElkNVFMSWVlVXZqTkdMb3dJQUF3ck1tTFYwWFFQNVBEOWJ4c0ZlbC8wMDJybTlzQnpnRVdRdksxSDZEdkphYjhyK3BXQUMxbmtqbGpBeVlCeEFma1hyTlFtbzU2aEpUdkJkb0RzZEZ2QUwzRStzSEQyWk9wUjlzakUreUVPcTg3dVpjZWlNbzIyQTJUZGZNdnBPZENDVWwrdUFvQkk5ZVZUcXhzamIwQk9BSnFPMTE1T2RTclgzNm80YkMybTBDOHhjRG1ocSt4dkxsdGltUGg3STIvWkRGWkpqVEMzSWVyTU1ITklWVFNSeTdEL3pvM1NYQlNua0J2YVp0ZmFLbElnUW1HbGU2Z2xHSEhVWTg2TFRVaWFNY2IzeGhRR0xLRFY2ZTNISHZJOWNNMEJtbW1qV3k5WENvL3JTTlA1d2lXR0VRQ0FkeWJETjJ0UzBQdnREbUJsU1Y4aHRVcHk2dm5KbEx5c1RTLytvV053UzFJNVNOeVZ4MU9RLzhNVXIvK1JSZ0EvNjNZQ1pNaklBWXlidWs1M2dLdUY3RmF3T1ZKa01PNjBxMWZ3UGRJaURaNWFWSXk3cUs3dVlMcE9GbXViMm5YM2hMeGg2RTJvOGp4QnFlYmJJTG5aUmVIeE55Q3pPTDlGM1FTTFJhbFVMK3B4ZEF0aVlTWHlUMGdZeXA0UGZ2RXp3ZEJQaUFubHRDVDlSY2RsM2ltMlcwNm54YXVWRmpHeHoybTFQb0RJdmVsYUx6UlVKcFRjU09OZGpMVytma0IzbG03dGYybGtQSDk1cm80T1ZWND0mODE1c2FlMHZTUEhPMW5jZUVyeWdTTG95N1RrPQ==; ujr=1; usersync=%7B%22magnite%22%3A%7B%22id%22%3A%22MS0NUIR2-B-80UE%22%2C%22ts%22%3A1785001573603%7D%7D; g_state={"i_l":0,"i_ll":1785004576954,"i_b":"bRcl0GuTmmqUyDrE9XuGr18ll3skO31o5sGh1SC9SJY","i_e":{"enable_itp_optimization":24},"i_et":1785004576954}""".strip()

# Valid static equivalents of the browser request headers.
#
# The following captured browser fields are NOT normal Python requests headers:
#   :authority -> derived automatically from www.pinterest.com
#   :method    -> determined by session.get()/session.post()
#   :path      -> determined by the endpoint URL
#   :scheme    -> determined by the https:// URL
#
# requests also calculates Content-Length automatically from the payload.
# It negotiates Accept-Encoding according to the compression formats supported
# by the installed requests/urllib3 environment. Forcing "br" or "zstd" when
# their decoder packages are unavailable can make response decoding fail.
PINTEREST_COMMON_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": PINTEREST_BASE_URL,
    "Referer": f"{PINTEREST_BASE_URL}/",
    "User-Agent": USER_AGENT,
    "X-Requested-With": "XMLHttpRequest",
}

PINTEREST_FORM_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
}

PINTEREST_HTML_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
}


class PinterestScraperError(Exception):
    """Pinterest scraper-specific exception."""


def extract_csrf_token(
    cookie_header: Optional[str],
) -> Optional[str]:
    """
    Extract csrftoken from a browser Cookie header.
    """

    if not cookie_header:
        return None

    try:
        parsed_cookie = SimpleCookie()
        parsed_cookie.load(cookie_header)

        if "csrftoken" in parsed_cookie:
            return parsed_cookie["csrftoken"].value

    except Exception:
        pass

    match = re.search(
        r"(?:^|;\s*)csrftoken=([^;]+)",
        cookie_header,
    )

    if match:
        return match.group(1)

    return None


def get_pinterest_cookie(
    cookie_header: Optional[str] = None,
) -> str:
    """
    Return an explicitly supplied cookie or PINTEREST_COOKIE
    from the server environment.
    """

    resolved_cookie = str(
        cookie_header or PINTEREST_COOKIE or ""
    ).strip()

    if (
        not resolved_cookie
        or "PASTE_A_NEW_COMPLETE_" in resolved_cookie
    ):
        raise PinterestScraperError(
            "PINTEREST_COOKIE environment variable is not configured."
        )

    return resolved_cookie


def get_safe_header_summary() -> Dict[str, str]:
    """
    Return non-secret headers for debugging.

    The Cookie and X-Csrftoken values are intentionally omitted.
    """

    return {
        **PINTEREST_COMMON_HEADERS,
        **PINTEREST_FORM_HEADERS,
        "Host": "www.pinterest.com (set automatically)",
        "Content-Length": "set automatically",
        "Accept-Encoding": "set automatically",
    }


def create_pinterest_session(
    cookie_header: Optional[str] = None,
) -> requests.Session:
    """
    Create a reusable Pinterest HTTP session.

    Browser-managed pseudo-headers such as :authority, :method,
    :path and :scheme must not be added to requests headers.
    """

    resolved_cookie = get_pinterest_cookie(cookie_header)

    session = requests.Session()
    session.headers.update(PINTEREST_COMMON_HEADERS)
    session.headers["Cookie"] = resolved_cookie

    csrf_token = extract_csrf_token(resolved_cookie)

    if csrf_token:
        session.headers["X-Csrftoken"] = csrf_token

    return session


def parse_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower().strip() in {
            "true",
            "1",
            "yes",
            "on",
        }

    return bool(value)


def get_pinterest_videos(
    query: str,
    num_scrape: int,
    cookie_header: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for Pinterest videos.
    """

    query = str(query or "").strip()

    if not query:
        raise PinterestScraperError(
            "Pinterest search query is required."
        )

    try:
        page_size = int(num_scrape)
    except (TypeError, ValueError):
        page_size = 10

    page_size = max(1, min(page_size, 100))

    search_query = f"{query} videos"

    options = {
        "article": None,
        "applied_filters": None,
        "appliedProductFilters": "---",
        "auto_correction_disabled": False,
        "corpus": None,
        "customized_rerank_type": None,
        "domains": None,
        "filters": None,
        "page_size": page_size,
        "price_max": None,
        "price_min": None,
        "query": search_query,
        "query_pin_sigs": None,
        "redux_normalize_feed": True,
        "rs": "video",
        "scope": "videos",
        "source_id": None,
        "top_pin_id": "",
        "bookmarks": [""],
    }

    payload = {
        "source_url": (
            "/search/videos/"
            f"?q={quote_plus(search_query)}"
            "&rs=video"
        ),
        "data": json.dumps({
            "options": options,
            "context": {},
        }),
    }

    session = create_pinterest_session(
        cookie_header
    )

    try:
        response = session.post(
            PINTEREST_SEARCH_ENDPOINT,
            data=payload,
            headers=PINTEREST_FORM_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise PinterestScraperError(
            f"Pinterest search request failed: {exc}"
        ) from exc

    try:
        response_data = response.json()
    except ValueError as exc:
        raise PinterestScraperError(
            "Pinterest search returned invalid JSON."
        ) from exc

    resource_response = response_data.get(
        "resource_response",
        {},
    )

    if resource_response.get("error"):
        raise PinterestScraperError(
            str(resource_response["error"])
        )

    return response_data


def extract_search_results(
    response_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    results = (
        response_data
        .get("resource_response", {})
        .get("data", {})
        .get("results", [])
    )

    if not isinstance(results, list):
        return []

    return [
        item
        for item in results
        if isinstance(item, dict)
    ]


def normalize_duration_seconds(
    duration: Any,
) -> int:
    """
    Pinterest normally returns duration in milliseconds.
    """

    try:
        value = float(duration or 0)
    except (TypeError, ValueError):
        return 0

    if value > 1000:
        value = value / 1000

    return max(0, int(value))


def extract_video_variants(
    video_list: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract actual MP4 and HLS variants.

    This function does not replace:
        hls -> 720p
        m3u8 -> mp4
    """

    if not isinstance(video_list, dict):
        return []

    variants = []

    for variant_name, variant in video_list.items():
        if not isinstance(variant, dict):
            continue

        video_url = variant.get("url")

        if not video_url:
            continue

        path = urlparse(video_url).path.lower()

        if path.endswith(".mp4"):
            stream_type = "mp4"
            stream_score = 2

        elif path.endswith(".m3u8"):
            stream_type = "hls"
            stream_score = 1

        else:
            continue

        variants.append({
            "name": variant_name,
            "url": video_url,
            "stream_type": stream_type,
            "width": variant.get("width") or 0,
            "height": variant.get("height") or 0,
            "bitrate": variant.get("bitrate") or 0,
            "duration": variant.get("duration") or 0,
            "_stream_score": stream_score,
        })

    variants.sort(
        key=lambda item: (
            item["_stream_score"],
            item["height"],
            item["width"],
            item["bitrate"],
        ),
        reverse=True,
    )

    return variants


def extract_video_variants_recursive(
    value: Any,
) -> List[Dict[str, Any]]:
    """
    Recursively find Pinterest video variants anywhere in a Pin payload.

    Search responses and Pin detail responses do not always expose media under
    exactly ``videos.video_list``. This collector accepts any nested mapping or
    list and records dictionaries that contain a direct .mp4 or HLS .m3u8 URL.
    """
    variants: List[Dict[str, Any]] = []
    seen_urls = set()

    def walk(node: Any, name_hint: str = "") -> None:
        if isinstance(node, dict):
            video_url = node.get("url")

            if isinstance(video_url, str) and video_url:
                path = urlparse(video_url).path.lower()

                if path.endswith(".mp4"):
                    stream_type = "mp4"
                    stream_score = 2
                elif path.endswith(".m3u8"):
                    stream_type = "hls"
                    stream_score = 1
                else:
                    stream_type = None
                    stream_score = 0

                if stream_type and video_url not in seen_urls:
                    variants.append({
                        "name": (
                            node.get("name")
                            or node.get("quality")
                            or node.get("format")
                            or name_hint
                            or "unknown"
                        ),
                        "url": video_url,
                        "stream_type": stream_type,
                        "width": node.get("width") or 0,
                        "height": node.get("height") or 0,
                        "bitrate": (
                            node.get("bitrate")
                            or node.get("bit_rate")
                            or 0
                        ),
                        "duration": (
                            node.get("duration")
                            or node.get("duration_ms")
                            or 0
                        ),
                        "_stream_score": stream_score,
                    })
                    seen_urls.add(video_url)

            for key, nested in node.items():
                walk(nested, str(key))

        elif isinstance(node, (list, tuple)):
            for index, nested in enumerate(node):
                walk(nested, f"{name_hint}[{index}]")

    walk(value)

    variants.sort(
        key=lambda item: (
            item["_stream_score"],
            item.get("height") or 0,
            item.get("width") or 0,
            item.get("bitrate") or 0,
        ),
        reverse=True,
    )

    return variants


def _select_reel_variant_from_variants(
    variants: List[Dict[str, Any]],
    verify: bool = False,
    allow_hls_fallback: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Return only a direct MP4 near 720x1280 and ~2 Mbps.

    ``allow_hls_fallback`` is retained only for backward compatibility with
    older view code and is intentionally ignored. HLS URLs are never returned
    by the normal MP4-only scraping path.
    """
    mp4_variants = [
        variant
        for variant in variants
        if variant.get("stream_type") == "mp4"
        and variant.get("url")
    ]

    def reel_score(variant: Dict[str, Any]):
        try:
            width = int(variant.get("width") or 0)
        except (TypeError, ValueError):
            width = 0

        try:
            height = int(variant.get("height") or 0)
        except (TypeError, ValueError):
            height = 0

        try:
            bitrate = int(variant.get("bitrate") or 0)
        except (TypeError, ValueError):
            bitrate = 0

        if width > 0 and height > 0:
            short_side = min(width, height)
            long_side = max(width, height)
            resolution_penalty = (
                abs(short_side - REEL_TARGET_SHORT_SIDE)
                + abs(long_side - REEL_TARGET_LONG_SIDE)
            )
        else:
            resolution_penalty = 10_000

        bitrate_penalty = (
            abs(bitrate - REEL_TARGET_BITRATE)
            if bitrate > 0
            else REEL_TARGET_BITRATE
        )

        return (
            0 if width > 0 and height > 0 else 1,
            resolution_penalty,
            bitrate_penalty,
            bitrate if bitrate > 0 else REEL_TARGET_BITRATE,
        )

    mp4_variants.sort(key=reel_score)

    for variant in mp4_variants:
        if not verify or video_url_is_working(variant["url"]):
            return variant

    # Strict MP4-only mode. Never return Pinterest HLS manifests.
    return None


def select_best_video_variant_from_pin_data(
    pin_data: Dict[str, Any],
    verify: bool = False,
    allow_hls_fallback: bool = False,
) -> Optional[Dict[str, Any]]:
    """Find the best playable video link anywhere in a Pin payload."""
    return _select_reel_variant_from_variants(
        extract_video_variants_recursive(pin_data),
        verify=verify,
        allow_hls_fallback=allow_hls_fallback,
    )


def video_url_is_working(
    video_url: Optional[str],
) -> bool:
    """
    Check a video URL without downloading the whole file.
    """

    if not video_url:
        return False

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"{PINTEREST_BASE_URL}/",
        "Accept": "*/*",
        "Range": "bytes=0-4095",
    }

    try:
        with requests.get(
            video_url,
            headers=headers,
            stream=True,
            allow_redirects=True,
            timeout=(3, 5),
        ) as response:

            if response.status_code not in {
                200,
                206,
            }:
                return False

            content_type = (
                response.headers
                .get("Content-Type", "")
                .lower()
            )

            first_chunk = next(
                response.iter_content(
                    chunk_size=4096
                ),
                b"",
            )

            body_start = first_chunk.lower()

            error_markers = (
                b"<error>",
                b"accessdenied",
                b"access denied",
                b"expiredtoken",
                b"request has expired",
                b"signaturedoesnotmatch",
                b"authorizationqueryparameterserror",
            )

            if any(
                marker in body_start
                for marker in error_markers
            ):
                return False

            if (
                "application/xml" in content_type
                or "text/xml" in content_type
                or "text/html" in content_type
            ):
                return False

            # HLS manifest
            if urlparse(video_url).path.lower().endswith(
                ".m3u8"
            ):
                return bool(first_chunk)

            valid_content_types = (
                "video/",
                "application/octet-stream",
                "binary/octet-stream",
            )

            if any(
                content_type.startswith(prefix)
                for prefix in valid_content_types
            ):
                return True

            # Some CDNs omit a useful content type.
            return bool(first_chunk)

    except requests.RequestException:
        return False


def select_best_video_variant(
    video_list: Dict[str, Any],
    verify: bool = False,
    allow_hls_fallback: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return the best direct MP4; never return HLS."""
    return _select_reel_variant_from_variants(
        extract_video_variants(video_list),
        verify=verify,
        allow_hls_fallback=allow_hls_fallback,
    )


def extract_thumbnail(
    pin_data: Dict[str, Any],
) -> Dict[str, Any]:
    images = pin_data.get("images") or {}

    if not isinstance(images, dict):
        images = {}

    thumbnail = (
        images.get("736x")
        or images.get("564x")
        or images.get("474x")
        or images.get("236x")
        or images.get("170x")
        or images.get("orig")
        or {}
    )

    if not isinstance(thumbnail, dict):
        thumbnail = {}

    return {
        "url": thumbnail.get("url"),
        "width": thumbnail.get("width"),
        "height": thumbnail.get("height"),
    }


def find_pin_data_recursively(
    value: Any,
    pin_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find the Pin object even if Pinterest changes
    the response nesting.
    """

    if isinstance(value, dict):
        current_id = value.get("id")

        if (
            str(current_id) == str(pin_id)
            and isinstance(
                value.get("videos"),
                dict,
            )
        ):
            return value

        for nested_value in value.values():
            result = find_pin_data_recursively(
                nested_value,
                pin_id,
            )

            if result:
                return result

    elif isinstance(value, list):
        for item in value:
            result = find_pin_data_recursively(
                item,
                pin_id,
            )

            if result:
                return result

    return None


def fetch_pin_from_resource(
    pin_id: str,
    cookie_header: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Try Pinterest's internal PinResource endpoint.
    """

    session = create_pinterest_session(
        cookie_header
    )

    option_variants = [
        {
            "id": str(pin_id),
            "field_set_key": (
                "unauth_react_main_pin"
            ),
        },
        {
            "id": str(pin_id),
            "field_set_key": (
                "auth_web_main_pin"
            ),
        },
        {
            "id": str(pin_id),
        },
    ]

    for options in option_variants:
        params = {
            "source_url": f"/pin/{pin_id}/",
            "data": json.dumps({
                "options": options,
                "context": {},
            }),
        }

        try:
            response = session.get(
                PINTEREST_PIN_ENDPOINT,
                params=params,
                headers={
                    "Accept": (
                        "application/json, "
                        "text/javascript, "
                        "*/*; q=0.01"
                    ),
                },
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()
            response_data = response.json()

        except (
            requests.RequestException,
            ValueError,
        ):
            continue

        pin_data = find_pin_data_recursively(
            response_data,
            str(pin_id),
        )

        if pin_data:
            return pin_data

        resource_data = (
            response_data
            .get("resource_response", {})
            .get("data")
        )

        if (
            isinstance(resource_data, dict)
            and resource_data.get("videos")
        ):
            return resource_data

    return None


def fetch_pin_from_page(
    pin_id: str,
    cookie_header: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fallback: inspect JSON embedded in the Pin page.
    """

    session = create_pinterest_session(
        cookie_header
    )

    pin_url = (
        f"{PINTEREST_BASE_URL}/pin/{pin_id}/"
    )

    try:
        response = session.get(
            pin_url,
            headers=PINTEREST_HTML_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException:
        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for script in soup.find_all("script"):
        script_type = (
            script.get("type") or ""
        ).lower()

        if (
            "json" not in script_type
            and not script.get("data-relay-response")
        ):
            continue

        raw_json = script.string or script.get_text()

        if not raw_json:
            continue

        try:
            parsed = json.loads(raw_json)
        except (ValueError, TypeError):
            continue

        pin_data = find_pin_data_recursively(
            parsed,
            str(pin_id),
        )

        if pin_data:
            return pin_data

    return None


def fetch_fresh_pin_data(
    pin_id: str,
    cookie_header: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve current Pin metadata.

    First try PinResource, then fall back to the Pin page.
    """

    pin_data = fetch_pin_from_resource(
        pin_id=pin_id,
        cookie_header=cookie_header,
    )

    if pin_data:
        return pin_data

    pin_data = fetch_pin_from_page(
        pin_id=pin_id,
        cookie_header=cookie_header,
    )

    if pin_data:
        return pin_data

    raise PinterestScraperError(
        f"Could not retrieve fresh data "
        f"for Pinterest Pin {pin_id}."
    )


def normalize_tag_name(value: Any) -> Optional[str]:
    """
    Normalize one Pinterest tag value for the Tag model.
    """

    if value is None:
        return None

    name = str(value).strip()

    if not name:
        return None

    # Pinterest can return hashtags with the leading #.
    name = name.lstrip("#").strip()

    if not name:
        return None

    # Keep within Tag.name max_length.
    return name[:300]


def _collect_tag_names(
    value: Any,
    output: List[str],
    seen_lower: set,
) -> None:
    """
    Recursively collect tag-like values from Pinterest metadata.
    """

    if value is None:
        return

    if isinstance(value, str):
        name = normalize_tag_name(value)

        if name and name.casefold() not in seen_lower:
            output.append(name)
            seen_lower.add(name.casefold())

        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_tag_names(
                item,
                output,
                seen_lower,
            )
        return

    if not isinstance(value, dict):
        return

    # Common Pinterest annotation/tag object fields.
    direct_name = (
        value.get("name")
        or value.get("label")
        or value.get("key")
        or value.get("tag")
        or value.get("title")
        or value.get("display_name")
    )

    if direct_name:
        _collect_tag_names(
            direct_name,
            output,
            seen_lower,
        )

    # Common nested containers in Pinterest responses.
    nested_keys = (
        "interests",
        "annotation_tags",
        "annotations",
        "hashtags",
        "visual_annotations",
        "aggregated_pin_data",
        "entities",
        "items",
        "results",
    )

    for key in nested_keys:
        if key in value:
            _collect_tag_names(
                value.get(key),
                output,
                seen_lower,
            )


def extract_tag_names(
    pin_data: Dict[str, Any],
    fallback_tag_names: Optional[
        Iterable[str]
    ] = None,
) -> List[str]:
    """
    Extract unique tags from Pinterest metadata.

    When Pinterest returns no annotations, fallback_tag_names
    ensures that the search query/category can still be saved
    as a useful tag.
    """

    tag_names: List[str] = []
    seen_lower = set()

    candidate_values = (
        pin_data.get("interests"),
        pin_data.get("annotation_tags"),
        pin_data.get("annotations"),
        pin_data.get("hashtags"),
        pin_data.get("visual_annotations"),
        pin_data.get("aggregated_pin_data"),
    )

    for value in candidate_values:
        _collect_tag_names(
            value,
            tag_names,
            seen_lower,
        )

    for fallback_name in fallback_tag_names or []:
        _collect_tag_names(
            fallback_name,
            tag_names,
            seen_lower,
        )

    return tag_names


def get_or_create_tag(
    tag_name: str,
) -> Tag:
    """
    Avoid duplicate Tag rows that differ only by letter case.
    """

    existing_tag = (
        Tag.objects
        .filter(name__iexact=tag_name)
        .first()
    )

    if existing_tag:
        if not existing_tag.is_active:
            existing_tag.is_active = True
            existing_tag.save(
                update_fields=["is_active"]
            )

        return existing_tag

    return Tag.objects.create(
        name=tag_name,
        is_active=True,
    )


def assign_video_tags(
    video: Video,
    pin_data: Dict[str, Any],
    fallback_tag_names: Optional[
        Iterable[str]
    ] = None,
    replace_existing: bool = False,
) -> List[str]:
    """
    Assign Pinterest tags to a video.

    replace_existing=False preserves tags manually assigned
    through Django admin and only adds newly scraped tags.
    """

    tag_names = extract_tag_names(
        pin_data=pin_data,
        fallback_tag_names=fallback_tag_names,
    )

    tag_objects = [
        get_or_create_tag(tag_name)
        for tag_name in tag_names
    ]

    if tag_objects:
        if replace_existing:
            video.tags.set(tag_objects)
        else:
            video.tags.add(*tag_objects)

    return tag_names


def normalize_country_codes(
    country_codes: Optional[Sequence[str]],
) -> List[str]:
    """
    Normalize unique country codes such as US, GB and PK.
    """

    normalized_codes: List[str] = []
    seen_codes = set()

    for value in country_codes or []:
        code = str(value or "").strip().upper()

        if not code:
            continue

        # Country.code allows up to four characters.
        code = code[:4]

        if code not in seen_codes:
            normalized_codes.append(code)
            seen_codes.add(code)

    return normalized_codes


def get_selected_countries(
    assign_all_countries: bool = True,
    country_codes: Optional[
        Sequence[str]
    ] = None,
):
    """
    Return active Country rows for either all countries or
    a selected list of country codes.
    """

    active_countries = Country.objects.filter(
        is_active=True
    )

    if assign_all_countries:
        return active_countries.order_by("name")

    normalized_codes = normalize_country_codes(
        country_codes
    )

    if not normalized_codes:
        return Country.objects.none()

    country_query = Q()

    for code in normalized_codes:
        country_query |= Q(code__iexact=code)

    return (
        active_countries
        .filter(country_query)
        .order_by("name")
    )


def assign_video_countries(
    video: Video,
    assign_all_countries: bool = True,
    country_codes: Optional[
        Sequence[str]
    ] = None,
    replace_existing: bool = True,
) -> List[str]:
    """
    Assign active countries to a video.

    Rules:
      * assign_all_countries=True assigns every active Country.
      * assign_all_countries=False with country_codes assigns
        only matching active countries.
      * assign_all_countries=False without codes leaves existing
        countries unchanged.
    """

    if (
        not assign_all_countries
        and not normalize_country_codes(
            country_codes
        )
    ):
        return list(
            video.country.values_list(
                "code",
                flat=True,
            )
        )

    country_objects = list(
        get_selected_countries(
            assign_all_countries=(
                assign_all_countries
            ),
            country_codes=country_codes,
        )
    )

    if replace_existing:
        video.country.set(country_objects)
    elif country_objects:
        video.country.add(*country_objects)

    return [
        country.code
        for country in country_objects
    ]


def build_video_data(
    pin_data: Dict[str, Any],
    variant: Dict[str, Any],
    existing_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pin_id = str(
        pin_data.get("id") or ""
    )

    duration_seconds = (
        normalize_duration_seconds(
            variant.get("duration")
        )
    )

    video_data = deepcopy(
        existing_data
        if isinstance(existing_data, dict)
        else {}
    )

    video_data["thumbnail"] = (
        extract_thumbnail(pin_data)
    )

    video_data["video_data"] = {
        "duration": duration_seconds,
        "video_width": (
            variant.get("width")
        ),
        "video_height": (
            variant.get("height")
        ),
        "audio_included": True,
        "stream_type": (
            variant.get("stream_type")
        ),
        "variant_name": variant.get("name"),
    }

    video_data["source"] = {
        "platform": "pinterest",
        "pin_id": pin_id,
        "pin_url": (
            f"{PINTEREST_BASE_URL}/pin/{pin_id}/"
        ),
        "last_refreshed_at": (
            timezone.now().isoformat()
        ),
    }

    return video_data


def find_existing_pinterest_video(
    pin_id: str,
) -> Optional[Video]:
    """
    Find a previously scraped Pin using JSONField lookup.
    """

    return (
        Video.objects
        .filter(
            video_data__source__platform=(
                "pinterest"
            ),
            video_data__source__pin_id=(
                str(pin_id)
            ),
        )
        .first()
    )


@transaction.atomic
def save_pinterest_pin(
    pin_data: Dict[str, Any],
    cookie_header: Optional[str] = None,
    category: Optional[VideoCategory] = None,
    assign_all_countries: bool = True,
    country_codes: Optional[
        Sequence[str]
    ] = None,
    fallback_tag_names: Optional[
        Sequence[str]
    ] = None,
    replace_existing_tags: bool = False,
    replace_existing_countries: bool = True,
    verify_url: bool = False,
    allow_hls_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Create or update one Pinterest video using a direct MP4 URL only.

    No HLS fallback, Pin detail request, media download, FFmpeg conversion,
    or storage upload is performed. ``allow_hls_fallback`` is accepted only
    so older API view code does not break; it is intentionally ignored.
    """

    pin_id = str(
        pin_data.get("id") or ""
    )

    if not pin_id:
        raise PinterestScraperError(
            "Pinterest result has no Pin ID."
        )

    # IMPORTANT FOR API SPEED:
    # Only use links already present in the Pinterest search response.
    # Do NOT call fetch_fresh_pin_data() here. Doing a PinResource/page
    # request for every search result can easily exceed Gunicorn's request
    # timeout when scraping 20+ videos.
    effective_pin_data = pin_data

    # Strict MP4-only selection from the search payload.
    # Never fetch PinResource / Pin HTML here: that per-Pin fallback was the
    # cause of the Gunicorn worker timeout.
    variant = select_best_video_variant_from_pin_data(
        pin_data,
        verify=verify_url,
        allow_hls_fallback=False,
    )

    if not variant:
        raise PinterestScraperError(
            f"No direct MP4 variant in Pinterest search response for Pin {pin_id}."
        )

    existing_video = (
        find_existing_pinterest_video(pin_id)
    )

    duration_seconds = (
        normalize_duration_seconds(
            variant.get("duration")
        )
    )

    title = (
        effective_pin_data.get("title")
        or effective_pin_data.get("grid_title")
        or effective_pin_data.get("seo_title")
        or f"Pinterest video {pin_id}"
    )

    description = (
        effective_pin_data.get("description")
        or effective_pin_data.get("seo_description")
        or ""
    )

    generated_video_data = build_video_data(
        pin_data=effective_pin_data,
        variant=variant,
        existing_data=(
            existing_video.video_data
            if existing_video
            else None
        ),
    )

    if existing_video:
        video = existing_video
        created = False

        video.title = str(title)[:500]
        video.description = description
        video.base_url = variant["url"]
        video.video_data = generated_video_data
        video.video_type = (
            "short"
            if duration_seconds <= 90
            else "video"
        )
        video.failure_count = 0
        video.is_active = True
        video.is_delete = False
        video.save()

    else:
        created = True

        video = Video.objects.create(
            title=str(title)[:500],
            description=description,
            base_url=variant["url"],
            video_data=generated_video_data,
            video_type=(
                "short"
                if duration_seconds <= 90
                else "video"
            ),
            failure_count=0,
            is_active=True,
            is_delete=False,
        )

    if category:
        video.category.add(category)

    assigned_tags = assign_video_tags(
        video=video,
        pin_data=effective_pin_data,
        fallback_tag_names=(
            fallback_tag_names
        ),
        replace_existing=(
            replace_existing_tags
        ),
    )

    assigned_countries = assign_video_countries(
        video=video,
        assign_all_countries=(
            assign_all_countries
        ),
        country_codes=country_codes,
        replace_existing=(
            replace_existing_countries
        ),
    )

    return {
        "video": video,
        "created": created,
        "pin_id": pin_id,
        "tags": assigned_tags,
        "countries": assigned_countries,
        "stream_type": variant.get("stream_type"),
        "url": variant.get("url"),
    }


def scrape_and_save_pinterest_videos(
    query: str,
    num_scrape: int,
    cookie_header: Optional[str] = None,
    category: Optional[VideoCategory] = None,
    assign_all_countries: bool = True,
    country_codes: Optional[
        Sequence[str]
    ] = None,
    default_tag_names: Optional[
        Sequence[str]
    ] = None,
    replace_existing_tags: bool = False,
    replace_existing_countries: bool = True,
    verify_urls: bool = False,
    allow_hls_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Search Pinterest and save direct-MP4 videos with tags and countries.

    The search query is automatically used as a fallback tag
    when Pinterest does not return annotations.
    """

    try:
        requested_limit = max(1, min(int(num_scrape), 100))
    except (TypeError, ValueError):
        requested_limit = 10

    # Pinterest search payloads often expose HLS only. To improve the chance
    # of finding the requested number of direct MP4 links without making
    # per-Pin requests, ask for a larger candidate pool in this ONE search.
    candidate_limit = min(100, max(requested_limit, requested_limit * 4))

    response_data = get_pinterest_videos(
        query=query,
        num_scrape=candidate_limit,
        cookie_header=cookie_header,
    )

    search_results = extract_search_results(
        response_data
    )[:candidate_limit]

    fallback_tag_names = [
        str(query).strip()
    ]

    for tag_name in default_tag_names or []:
        normalized_tag = normalize_tag_name(
            tag_name
        )

        if (
            normalized_tag
            and normalized_tag.casefold()
            not in {
                value.casefold()
                for value in fallback_tag_names
            }
        ):
            fallback_tag_names.append(
                normalized_tag
            )

    created_count = 0
    updated_count = 0
    skipped_count = 0
    mp4_count = 0
    errors = []
    all_assigned_tags = set()
    all_assigned_countries = set()

    mp4_candidates = 0

    for pin_data in search_results:
        # Stop as soon as the requested number of MP4 records is saved.
        if created_count + updated_count >= requested_limit:
            break

        # Local-only prefilter: skip HLS-only results immediately. No network
        # request is made here.
        local_variant = select_best_video_variant_from_pin_data(
            pin_data,
            verify=False,
            allow_hls_fallback=False,
        )
        if not local_variant:
            skipped_count += 1
            errors.append({
                "pin_id": pin_data.get("id"),
                "error": "No direct MP4 in Pinterest search response.",
            })
            continue

        mp4_candidates += 1

        try:
            result = save_pinterest_pin(
                pin_data=pin_data,
                cookie_header=cookie_header,
                category=category,
                assign_all_countries=(
                    assign_all_countries
                ),
                country_codes=country_codes,
                fallback_tag_names=(
                    fallback_tag_names
                ),
                replace_existing_tags=(
                    replace_existing_tags
                ),
                replace_existing_countries=(
                    replace_existing_countries
                ),
                verify_url=verify_urls,
                allow_hls_fallback=False,
            )

            all_assigned_tags.update(
                result.get("tags", [])
            )
            all_assigned_countries.update(
                result.get("countries", [])
            )

            if result["created"]:
                created_count += 1
            else:
                updated_count += 1

            if result.get("stream_type") == "mp4":
                mp4_count += 1

        except Exception as exc:
            skipped_count += 1

            errors.append({
                "pin_id": pin_data.get("id"),
                "error": str(exc),
            })

    return {
        "status": "success",
        "requested": requested_limit,
        "candidate_pool": len(search_results),
        "mp4_candidates": mp4_candidates,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total_saved": (
            created_count + updated_count
        ),
        "mp4_saved": mp4_count,
        "hls_saved": 0,
        "tags": sorted(all_assigned_tags),
        "countries": sorted(
            all_assigned_countries
        ),
        "errors": errors,
    }


def mark_refresh_failure(
    video: Video,
) -> int:
    failure_count = (
        video.increment_failure()
    )

    # Disable the record after three failures.
    if failure_count >= 3:
        video.is_active = False
        video.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    return failure_count


def refresh_pinterest_video_link(
    video: Video,
    cookie_header: Optional[str] = None,
    force: bool = False,
    refresh_tags: bool = True,
) -> Dict[str, Any]:
    """
    Refresh one video's expired Pinterest URL.
    """

    old_url = video.base_url

    if (
        not force
        and video_url_is_working(old_url)
    ):
        return {
            "status": "active",
            "updated": False,
            "video_id": video.pk,
            "pin_id": (
                video.get_pinterest_pin_id()
            ),
            "url": old_url,
        }

    pin_id = video.get_pinterest_pin_id()

    if not pin_id:
        failure_count = mark_refresh_failure(
            video
        )

        raise PinterestScraperError(
            f"Video {video.pk} has no Pinterest "
            f"Pin ID. Current failure count: "
            f"{failure_count}."
        )

    try:
        pin_data = fetch_fresh_pin_data(
            pin_id=str(pin_id),
            cookie_header=cookie_header,
        )

        fresh_variant = (
            select_best_video_variant_from_pin_data(
                pin_data,
                verify=True,
                allow_hls_fallback=True,
            )
        )

        if not fresh_variant:
            raise PinterestScraperError(
                f"Pinterest returned no working video "
                f"URL for Pin {pin_id}."
            )

        video.base_url = fresh_variant["url"]

        video.video_data = build_video_data(
            pin_data=pin_data,
            variant=fresh_variant,
            existing_data=video.video_data,
        )

        duration_seconds = (
            normalize_duration_seconds(
                fresh_variant.get("duration")
            )
        )

        video.video_type = (
            "short"
            if duration_seconds <= 90
            else "video"
        )

        video.failure_count = 0
        video.is_active = True
        video.is_delete = False

        video.save(
            update_fields=[
                "base_url",
                "video_data",
                "video_type",
                "failure_count",
                "is_active",
                "is_delete",
                "updated_at",
            ]
        )

        refreshed_tags = []

        if refresh_tags:
            refreshed_tags = assign_video_tags(
                video=video,
                pin_data=pin_data,
                replace_existing=False,
            )

        return {
            "status": "refreshed",
            "updated": True,
            "video_id": video.pk,
            "pin_id": str(pin_id),
            "old_url": old_url,
            "new_url": video.base_url,
            "tags": refreshed_tags,
        }

    except Exception:
        mark_refresh_failure(video)
        raise


def refresh_expired_pinterest_videos(
    cookie_header: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False,
    refresh_tags: bool = True,
) -> Dict[str, Any]:
    """
    Check all Pinterest videos and refresh expired links.
    """

    queryset = (
        Video.objects
        .filter(
            is_delete=False,
            video_data__source__platform=(
                "pinterest"
            ),
        )
        .order_by("id")
    )

    if limit is not None:
        try:
            limit_value = max(
                1,
                int(limit),
            )
            videos = list(
                queryset[:limit_value]
            )
        except (TypeError, ValueError):
            videos = list(queryset)
    else:
        videos = list(queryset)

    active_count = 0
    refreshed_count = 0
    failed_count = 0
    results = []

    for video in videos:
        try:
            result = (
                refresh_pinterest_video_link(
                    video=video,
                    cookie_header=(
                        cookie_header
                    ),
                    force=force,
                    refresh_tags=refresh_tags,
                )
            )

            if result["updated"]:
                refreshed_count += 1
            else:
                active_count += 1

            results.append(result)

        except Exception as exc:
            failed_count += 1

            video.refresh_from_db(
                fields=[
                    "failure_count",
                    "is_active",
                ]
            )

            results.append({
                "status": "failed",
                "updated": False,
                "video_id": video.pk,
                "pin_id": (
                    video.get_pinterest_pin_id()
                ),
                "failure_count": (
                    video.failure_count
                ),
                "is_active": video.is_active,
                "error": str(exc),
            })

    return {
        "status": "success",
        "checked": len(videos),
        "active": active_count,
        "refreshed": refreshed_count,
        "failed": failed_count,
        "results": results,
    }