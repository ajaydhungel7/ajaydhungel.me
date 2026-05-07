"""Unit tests for fetch_github.py — all I/O is mocked."""
import json
import pytest
import sys
import urllib.error
from argparse import Namespace
from unittest.mock import patch, MagicMock

import fetch_github
from fetch_github import build_items, format_date, iso_date
from tests.conftest import make_urllib_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(name, stars=0, fork=False, archived=False, language="Python",
          updated_at="2024-01-15T12:00:00Z", description="A repo",
          topics=None):
    return {
        "name": name,
        "description": description,
        "html_url": f"https://github.com/user/{name}",
        "stargazers_count": stars,
        "forks_count": 0,
        "language": language,
        "topics": topics or [],
        "updated_at": updated_at,
        "fork": fork,
        "archived": archived,
    }


# ---------------------------------------------------------------------------
# Schema / happy-path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_happy_path_output_schema():
    """build_items returns list of dicts with all required fields."""
    repos = [_repo("myrepo", stars=5)]
    items = build_items(repos, limit=10, pinned=[])
    assert len(items) == 1
    item = items[0]
    required = {"name", "description", "url", "stars", "forks",
                "language", "topics", "updatedAt", "updatedAtRaw", "pinned"}
    assert required <= set(item.keys())


@pytest.mark.unit
def test_happy_path_field_values():
    repos = [_repo("myrepo", stars=3, language="Go", topics=["k8s"])]
    items = build_items(repos, limit=10, pinned=[])
    item = items[0]
    assert item["name"] == "myrepo"
    assert item["url"] == "https://github.com/user/myrepo"
    assert item["stars"] == 3
    assert item["language"] == "Go"
    assert item["topics"] == ["k8s"]
    assert item["pinned"] is False


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_forked_repos_excluded():
    repos = [_repo("forked", fork=True), _repo("normal")]
    items = build_items(repos, limit=10, pinned=[])
    names = [i["name"] for i in items]
    assert "forked" not in names
    assert "normal" in names


@pytest.mark.unit
def test_archived_repos_excluded():
    repos = [_repo("archived", archived=True), _repo("active")]
    items = build_items(repos, limit=10, pinned=[])
    names = [i["name"] for i in items]
    assert "archived" not in names
    assert "active" in names


@pytest.mark.unit
def test_limit_respected():
    repos = [_repo(f"repo{i}", stars=i) for i in range(20)]
    items = build_items(repos, limit=5, pinned=[])
    assert len(items) == 5


# ---------------------------------------------------------------------------
# Pinning
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_pinned_repos_appear_first_in_declared_order():
    repos = [
        _repo("a", stars=10),
        _repo("b", stars=5),
        _repo("c", stars=1),
    ]
    items = build_items(repos, limit=10, pinned=["c", "b"])
    names = [i["name"] for i in items]
    assert names[0] == "c"
    assert names[1] == "b"
    assert names[2] == "a"


@pytest.mark.unit
def test_pinned_flag_set_correctly():
    repos = [_repo("pinned"), _repo("normal")]
    items = build_items(repos, limit=10, pinned=["pinned"])
    by_name = {i["name"]: i for i in items}
    assert by_name["pinned"]["pinned"] is True
    assert by_name["normal"]["pinned"] is False


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_date_formatted_correctly():
    assert format_date("2024-03-15T00:00:00Z") == "Mar 15, 2024"


@pytest.mark.unit
def test_date_missing_returns_empty():
    assert format_date("") == ""
    assert format_date(None) == ""


@pytest.mark.unit
def test_date_parse_failure_returns_raw():
    """Unparseable date must not crash — return raw string."""
    assert format_date("not-a-date") == "not-a-date"


@pytest.mark.unit
def test_iso_date_formats_correctly():
    result = iso_date("2024-03-15T00:00:00Z")
    assert result.startswith("2024-03-15")


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_repo_list_returns_empty_items():
    items = build_items([], limit=10, pinned=[])
    assert items == []


@pytest.mark.unit
def test_all_repos_filtered_returns_empty():
    repos = [_repo("a", fork=True), _repo("b", archived=True)]
    items = build_items(repos, limit=10, pinned=[])
    assert items == []


# ---------------------------------------------------------------------------
# Error handling — fetch_json raises on bad HTTP status
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_http_403_raises_exception():
    """A 403 (rate limit) must propagate as an exception so main() exits non-zero."""
    err = urllib.error.HTTPError(url="", code=403, msg="Forbidden", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.HTTPError):
            fetch_github.fetch_json("https://api.github.com/users/x/repos")


@pytest.mark.unit
def test_http_404_raises_exception():
    err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.HTTPError):
            fetch_github.fetch_json("https://api.github.com/users/x/repos")


@pytest.mark.unit
def test_network_timeout_raises_exception():
    err = urllib.error.URLError(reason="timed out")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.URLError):
            fetch_github.fetch_json("https://api.github.com/users/x/repos")


# ---------------------------------------------------------------------------
# fetch_json happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fetch_json_returns_parsed_data():
    payload = [{"name": "myrepo"}]
    mock_resp = make_urllib_response(payload)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_github.fetch_json("https://api.github.com/users/x/repos")
    assert result == payload


# ---------------------------------------------------------------------------
# main() error path — exits nonzero on any failure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_main_exits_nonzero_on_http_error():
    """main() must catch HTTPError and exit(1), not propagate."""
    err = urllib.error.HTTPError(url="", code=403, msg="Forbidden", hdrs=None, fp=None)
    fake_args = Namespace(user="testuser", out="/dev/null", limit=12, pin=[])
    with patch("fetch_github.fetch_json", side_effect=err), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_github.main()
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_main_exits_nonzero_on_non_list_response():
    """main() must raise ValueError and exit(1) when API returns non-list."""
    fake_args = Namespace(user="testuser", out="/dev/null", limit=12, pin=[])
    with patch("fetch_github.fetch_json", return_value={"message": "Bad credentials"}), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_github.main()
    assert exc_info.value.code == 1
