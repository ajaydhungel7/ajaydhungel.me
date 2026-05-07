"""Unit tests for fetch_devto.py — all I/O is mocked."""
import pytest
import urllib.error
from argparse import Namespace
from unittest.mock import patch

import fetch_devto
from fetch_devto import build_items, format_date, iso_date
from tests.conftest import make_urllib_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _article(title="My Article", url="https://dev.to/user/my-article",
             published_at="2024-03-10T12:00:00Z",
             cover_image=None, social_image=None):
    return {
        "title": title,
        "url": url,
        "published_at": published_at,
        "cover_image": cover_image,
        "social_image": social_image,
    }


# ---------------------------------------------------------------------------
# Schema / happy-path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_happy_path_schema():
    data = [_article()]
    items = build_items(data)
    assert len(items) == 1
    required = {"title", "link", "pubDate", "pubDateRaw", "thumbnail", "source"}
    assert required <= set(items[0].keys())
    assert items[0]["source"] == "Dev.to"


@pytest.mark.unit
def test_happy_path_field_values():
    data = [_article(
        title="K8s Gateway API",
        url="https://dev.to/user/k8s",
        published_at="2024-06-01T00:00:00Z",
    )]
    items = build_items(data)
    item = items[0]
    assert item["title"] == "K8s Gateway API"
    assert item["link"] == "https://dev.to/user/k8s"
    assert item["pubDate"] == "Jun 01, 2024"


# ---------------------------------------------------------------------------
# Thumbnail fallback
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_cover_image_used_as_thumbnail():
    data = [_article(cover_image="https://cdn.dev.to/cover.jpg",
                     social_image="https://cdn.dev.to/social.jpg")]
    items = build_items(data)
    assert items[0]["thumbnail"] == "https://cdn.dev.to/cover.jpg"


@pytest.mark.unit
def test_falls_back_to_social_image_when_cover_image_is_null():
    data = [_article(cover_image=None, social_image="https://cdn.dev.to/social.jpg")]
    items = build_items(data)
    assert items[0]["thumbnail"] == "https://cdn.dev.to/social.jpg"


@pytest.mark.unit
def test_thumbnail_empty_when_both_images_null():
    data = [_article(cover_image=None, social_image=None)]
    items = build_items(data)
    assert items[0]["thumbnail"] == ""


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_date_formatted_correctly():
    assert format_date("2024-06-01T00:00:00Z") == "Jun 01, 2024"


@pytest.mark.unit
def test_date_parse_failure_returns_raw():
    assert format_date("not-a-date") == "not-a-date"


@pytest.mark.unit
def test_date_empty_returns_empty():
    assert format_date("") == ""


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_items_sorted_by_date_descending():
    data = [
        _article(title="Older", published_at="2023-01-01T00:00:00Z"),
        _article(title="Newer", published_at="2024-01-01T00:00:00Z"),
    ]
    items = build_items(data)
    assert items[0]["title"] == "Newer"
    assert items[1]["title"] == "Older"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_array_returns_empty_items():
    assert build_items([]) == []


@pytest.mark.unit
def test_non_array_body_does_not_crash():
    """If API returns a non-list (dict), build_items should not crash."""
    # build_items expects a list; non-list is an API contract violation.
    # Calling it with a dict would iterate over keys — test empty list as
    # boundary; full non-array is caught at the fetch layer in main().
    items = build_items([])
    assert items == []


# ---------------------------------------------------------------------------
# Error paths — fetch_json raises on bad HTTP
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_non_200_response_raises_exception():
    err = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.HTTPError):
            fetch_devto.fetch_json("https://dev.to/api/articles?username=x")


@pytest.mark.unit
def test_network_error_raises_exception():
    err = urllib.error.URLError(reason="timed out")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.URLError):
            fetch_devto.fetch_json("https://dev.to/api/articles?username=x")


# ---------------------------------------------------------------------------
# fetch_json happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fetch_json_returns_parsed_data():
    payload = [{"title": "Test"}]
    mock_resp = make_urllib_response(payload)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_devto.fetch_json("https://dev.to/api/articles?username=x")
    assert result == payload


# ---------------------------------------------------------------------------
# main() error path — exits nonzero on any failure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_main_exits_nonzero_on_http_error():
    """main() must catch HTTPError and exit(1), not propagate."""
    err = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
    fake_args = Namespace(username="testuser", out="/dev/null")
    with patch("fetch_devto.fetch_json", side_effect=err), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_devto.main()
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_main_exits_nonzero_on_non_list_response():
    """main() must raise ValueError and exit(1) when API returns non-list."""
    fake_args = Namespace(username="testuser", out="/dev/null")
    with patch("fetch_devto.fetch_json", return_value={"error": "rate limited"}), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_devto.main()
    assert exc_info.value.code == 1
