"""
Integration tests — validate generated data JSON files.

These tests run against real data files on disk (produced by `make fetch`
or checked into the repo). They catch:
  - Missing or malformed data files
  - Wrong JSON structure
  - Empty item lists (API silently returned nothing)
  - Missing required fields, null values, bad URLs, bad date formats
"""
import json
import re
import os
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATE_RE = re.compile(r"^[A-Z][a-z]{2} \d{2}, \d{4}$")   # e.g. "Jan 15, 2024"
URL_RE = re.compile(r"^https?://")


def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    assert os.path.isfile(path), f"data/{filename} does not exist — run `make fetch`"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _assert_top_level(data, filename):
    assert isinstance(data, dict), f"{filename}: root must be a JSON object"
    assert "items" in data, f"{filename}: missing top-level 'items' key"
    assert isinstance(data["items"], list), f"{filename}: 'items' must be a list"


def _assert_nonempty(data, filename):
    assert len(data["items"]) > 0, (
        f"{filename}: items list is empty — possible API failure during fetch"
    )


def _assert_url(value, field, filename):
    if value:
        assert URL_RE.match(value), (
            f"{filename}: {field}={value!r} must start with http(s)://"
        )


def _assert_date(value, field, filename):
    if value:
        assert DATE_RE.match(value), (
            f"{filename}: {field}={value!r} must match 'Mon DD, YYYY' format"
        )


# ---------------------------------------------------------------------------
# github.json
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_github_json_exists_and_valid():
    data = _load("github.json")
    _assert_top_level(data, "github.json")


@pytest.mark.integration
def test_github_json_nonempty():
    data = _load("github.json")
    _assert_nonempty(data, "github.json")


@pytest.mark.integration
def test_github_json_item_schema():
    data = _load("github.json")
    required = {"name", "description", "url", "stars", "forks",
                "language", "topics", "updatedAt", "updatedAtRaw", "pinned"}
    for item in data["items"]:
        missing = required - set(item.keys())
        assert not missing, f"github.json item missing fields: {missing}"
        assert isinstance(item["name"], str) and item["name"], \
            "github.json: 'name' must be a non-empty string"
        _assert_url(item["url"], "url", "github.json")
        _assert_date(item["updatedAt"], "updatedAt", "github.json")
        assert isinstance(item["stars"], int), "github.json: 'stars' must be an int"
        assert isinstance(item["pinned"], bool), "github.json: 'pinned' must be a bool"


# ---------------------------------------------------------------------------
# medium.json
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_medium_json_exists_and_valid():
    data = _load("medium.json")
    _assert_top_level(data, "medium.json")


@pytest.mark.integration
def test_medium_json_nonempty():
    data = _load("medium.json")
    _assert_nonempty(data, "medium.json")


@pytest.mark.integration
def test_medium_json_item_schema():
    data = _load("medium.json")
    required = {"title", "link", "pubDate", "pubDateRaw", "thumbnail", "source"}
    for item in data["items"]:
        missing = required - set(item.keys())
        assert not missing, f"medium.json item missing fields: {missing}"
        assert item["title"], "medium.json: 'title' must be non-empty"
        _assert_url(item["link"], "link", "medium.json")
        _assert_date(item["pubDate"], "pubDate", "medium.json")
        _assert_url(item.get("thumbnail", ""), "thumbnail", "medium.json")
        assert item["source"] == "Medium", "medium.json: source must be 'Medium'"


# ---------------------------------------------------------------------------
# devto.json
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_devto_json_exists_and_valid():
    data = _load("devto.json")
    _assert_top_level(data, "devto.json")


@pytest.mark.integration
def test_devto_json_item_schema():
    """Dev.to can legitimately have 0 articles; we still check the structure."""
    data = _load("devto.json")
    required = {"title", "link", "pubDate", "pubDateRaw", "thumbnail", "source"}
    for item in data["items"]:
        missing = required - set(item.keys())
        assert not missing, f"devto.json item missing fields: {missing}"
        assert item["title"], "devto.json: 'title' must be non-empty"
        _assert_url(item["link"], "link", "devto.json")
        _assert_date(item["pubDate"], "pubDate", "devto.json")
        assert item["source"] == "Dev.to", "devto.json: source must be 'Dev.to'"


# ---------------------------------------------------------------------------
# credly.json
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_credly_json_exists_and_valid():
    data = _load("credly.json")
    _assert_top_level(data, "credly.json")


@pytest.mark.integration
def test_credly_json_nonempty():
    data = _load("credly.json")
    _assert_nonempty(data, "credly.json")


@pytest.mark.integration
def test_credly_json_item_schema():
    data = _load("credly.json")
    required = {"title", "link", "issuedAt", "issuedAtRaw", "expiresAt", "thumbnail", "source"}
    for item in data["items"]:
        missing = required - set(item.keys())
        assert not missing, f"credly.json item missing fields: {missing}"
        assert item["title"], "credly.json: 'title' must be non-empty"
        _assert_url(item["link"], "link", "credly.json")
        _assert_date(item["issuedAt"], "issuedAt", "credly.json")
        _assert_url(item.get("thumbnail", ""), "thumbnail", "credly.json")
        assert item["source"] == "Credly", "credly.json: source must be 'Credly'"


# ---------------------------------------------------------------------------
# talks.json
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_talks_json_exists_and_valid():
    data = _load("talks.json")
    _assert_top_level(data, "talks.json")


@pytest.mark.integration
def test_talks_json_nonempty():
    data = _load("talks.json")
    _assert_nonempty(data, "talks.json")


@pytest.mark.integration
def test_talks_json_item_schema():
    data = _load("talks.json")
    required = {"event", "title", "date", "location", "description"}
    for item in data["items"]:
        missing = required - set(item.keys())
        assert not missing, f"talks.json item missing fields: {missing}"
        assert item["title"], "talks.json: 'title' must be non-empty"
        assert item["event"], "talks.json: 'event' must be non-empty"
        if item.get("link"):
            _assert_url(item["link"], "link", "talks.json")
