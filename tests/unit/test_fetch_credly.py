"""Unit tests for fetch_credly.py — all I/O is mocked.

Includes the Prove-It pattern for the silent exit(0) bug:
  the test_api_error_exits_nonzero test must FAIL before the bug is fixed.
"""
import json
import pytest
import urllib.error
from unittest.mock import patch

import fetch_credly
from fetch_credly import build_items, format_date, iso_date
from tests.conftest import make_urllib_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _badge(name="AWS Solutions Architect", badge_id="abc-123",
           issued_at="2024-01-16T00:00:00.000Z", expires_at=None,
           public=True, state="accepted",
           image_url="https://images.credly.com/badge.png",
           template_image_url="https://images.credly.com/template.png"):
    return {
        "id": badge_id,
        "public": public,
        "state": state,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "badge_template": {
            "name": name,
            "image_url": template_image_url,
        },
        "image_url": image_url,
    }


def _api_response(badges):
    return {"data": badges, "metadata": {"count": len(badges)}}


# ---------------------------------------------------------------------------
# Prove-It: fetch_credly exits non-zero on API error (bug was exit 0)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_api_error_exits_nonzero(tmp_path):
    """
    When fetch_credly encounters an API error, main() must call sys.exit(1).

    The original bug was sys.exit(0) in the exception handler, which made
    CI treat failures as success and silently drop badges from production.
    Error handling was moved into main() so this can be tested without
    subprocess or network access.
    """
    from argparse import Namespace
    err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    fake_args = Namespace(user="testuser", out="/dev/null")
    with patch("fetch_credly.fetch_json", side_effect=err), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_credly.main()
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Schema / happy-path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_happy_path_schema():
    data = _api_response([_badge()])
    items = build_items(data)
    assert len(items) == 1
    required = {"title", "link", "issuedAt", "issuedAtRaw", "expiresAt", "thumbnail", "source"}
    assert required <= set(items[0].keys())
    assert items[0]["source"] == "Credly"


@pytest.mark.unit
def test_happy_path_field_values():
    data = _api_response([_badge(
        name="AWS Developer",
        badge_id="dev-123",
        issued_at="2024-03-10T00:00:00.000Z",
    )])
    items = build_items(data)
    item = items[0]
    assert item["title"] == "AWS Developer"
    assert item["link"] == "https://www.credly.com/badges/dev-123"
    assert item["issuedAt"] == "Mar 10, 2024"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_only_public_and_accepted_badges_included():
    data = _api_response([
        _badge(name="Good", public=True, state="accepted"),
        _badge(name="Private", public=False, state="accepted"),
        _badge(name="Pending", public=True, state="pending"),
        _badge(name="PrivatePending", public=False, state="pending"),
    ])
    items = build_items(data)
    assert len(items) == 1
    assert items[0]["title"] == "Good"


@pytest.mark.unit
def test_expired_badges_still_included():
    """Expiry is display info, not a filter criterion."""
    data = _api_response([_badge(expires_at="2023-01-01T00:00:00.000Z")])
    items = build_items(data)
    assert len(items) == 1


# ---------------------------------------------------------------------------
# Thumbnail priority
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_template_image_url_preferred():
    data = _api_response([_badge(
        template_image_url="https://img.credly.com/template.png",
        image_url="https://img.credly.com/badge.png",
    )])
    items = build_items(data)
    assert items[0]["thumbnail"] == "https://img.credly.com/template.png"


@pytest.mark.unit
def test_falls_back_to_badge_image_url():
    """If badge_template.image_url is empty, use badge.image_url."""
    badge = _badge(image_url="https://img.credly.com/badge.png")
    badge["badge_template"]["image_url"] = ""
    data = _api_response([badge])
    items = build_items(data)
    assert items[0]["thumbnail"] == "https://img.credly.com/badge.png"


# ---------------------------------------------------------------------------
# Date handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_issued_at_formatted():
    assert format_date("2024-01-16T00:00:00.000Z") == "Jan 16, 2024"


@pytest.mark.unit
def test_expires_at_null_returns_empty():
    data = _api_response([_badge(expires_at=None)])
    items = build_items(data)
    assert items[0]["expiresAt"] == ""


@pytest.mark.unit
def test_expires_at_formatted_when_present():
    data = _api_response([_badge(expires_at="2025-12-31T00:00:00.000Z")])
    items = build_items(data)
    assert items[0]["expiresAt"] == "Dec 31, 2025"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_badge_list_returns_empty_items():
    data = _api_response([])
    items = build_items(data)
    assert items == []


@pytest.mark.unit
def test_items_sorted_by_issued_at_descending():
    data = _api_response([
        _badge(name="Older", issued_at="2022-01-01T00:00:00Z"),
        _badge(name="Newer", issued_at="2024-01-01T00:00:00Z"),
    ])
    items = build_items(data)
    assert items[0]["title"] == "Newer"


# ---------------------------------------------------------------------------
# fetch_json happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fetch_json_returns_parsed_data():
    payload = {"data": []}
    mock_resp = make_urllib_response(payload)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_credly.fetch_json("https://www.credly.com/users/x/badges.json")
    assert result == payload
