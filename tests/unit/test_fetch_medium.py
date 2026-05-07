"""Unit tests for fetch_medium.py — all I/O is mocked."""
import pytest
import urllib.error
from argparse import Namespace
from unittest.mock import patch

import fetch_medium
from fetch_medium import parse_rss, format_date, iso_date, extract_thumbnail
from tests.conftest import make_urllib_response


# ---------------------------------------------------------------------------
# RSS fixture builders
# ---------------------------------------------------------------------------

def _rss(items_xml="", extra_ns=""):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:media="http://search.yahoo.com/mrss/"
     xmlns:atom="http://www.w3.org/2005/Atom"
     {extra_ns}>
  <channel>
    <title>Test Feed</title>
    {items_xml}
  </channel>
</rss>""".encode("utf-8")


def _item(title="My Post", link="https://medium.com/p/123",
          pub_date="Mon, 15 Jan 2024 12:00:00 GMT",
          media_thumbnail="", media_content="", enclosure="",
          content="<p>Hello world</p>"):
    thumb_xml = ""
    if media_thumbnail:
        thumb_xml += f'<media:thumbnail url="{media_thumbnail}"/>'
    if media_content:
        thumb_xml += f'<media:content url="{media_content}"/>'
    if enclosure:
        thumb_xml += f'<enclosure url="{enclosure}" type="image/jpeg"/>'
    return f"""
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <pubDate>{pub_date}</pubDate>
      <content:encoded><![CDATA[{content}]]></content:encoded>
      {thumb_xml}
    </item>"""


def _atom(entries_xml=""):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  {entries_xml}
</feed>""".encode("utf-8")


def _entry(title="Atom Post", href="https://medium.com/p/atom",
           updated="2024-02-10T00:00:00Z",
           content='<img src="https://img.example.com/thumb.jpg"/>'):
    return f"""
    <entry xmlns="http://www.w3.org/2005/Atom">
      <title>{title}</title>
      <link href="{href}"/>
      <updated>{updated}</updated>
      <content type="html"><![CDATA[{content}]]></content>
    </entry>"""


# ---------------------------------------------------------------------------
# Schema / happy-path (RSS format)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_rss_happy_path_schema():
    xml = _rss(_item())
    items = parse_rss(xml)
    assert len(items) == 1
    item = items[0]
    required = {"title", "link", "pubDate", "pubDateRaw", "thumbnail", "source"}
    assert required <= set(item.keys())
    assert item["source"] == "Medium"


@pytest.mark.unit
def test_rss_happy_path_field_values():
    xml = _rss(_item(
        title="My Great Post",
        link="https://medium.com/p/abc",
        pub_date="Mon, 15 Jan 2024 12:00:00 GMT",
    ))
    items = parse_rss(xml)
    item = items[0]
    assert item["title"] == "My Great Post"
    assert item["link"] == "https://medium.com/p/abc"
    assert item["pubDate"] == "Jan 15, 2024"


# ---------------------------------------------------------------------------
# Atom fallback
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_atom_fallback_parsed_when_no_rss_items():
    xml = _atom(_entry(title="Atom Post", href="https://medium.com/p/atom"))
    items = parse_rss(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Atom Post"
    assert items[0]["source"] == "Medium"


@pytest.mark.unit
def test_atom_date_formatted():
    xml = _atom(_entry(updated="2024-06-01T00:00:00Z"))
    items = parse_rss(xml)
    assert items[0]["pubDate"] == "Jun 01, 2024"


# ---------------------------------------------------------------------------
# Thumbnail extraction priority
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_thumbnail_from_media_thumbnail():
    xml = _rss(_item(media_thumbnail="https://cdn.example.com/thumb.jpg"))
    items = parse_rss(xml)
    assert items[0]["thumbnail"] == "https://cdn.example.com/thumb.jpg"


@pytest.mark.unit
def test_thumbnail_falls_back_to_media_content():
    xml = _rss(_item(media_content="https://cdn.example.com/content.jpg"))
    items = parse_rss(xml)
    assert items[0]["thumbnail"] == "https://cdn.example.com/content.jpg"


@pytest.mark.unit
def test_thumbnail_falls_back_to_enclosure():
    xml = _rss(_item(enclosure="https://cdn.example.com/enclosure.jpg"))
    items = parse_rss(xml)
    assert items[0]["thumbnail"] == "https://cdn.example.com/enclosure.jpg"


@pytest.mark.unit
def test_thumbnail_falls_back_to_regex_from_content():
    content = '<p>intro</p><img src="https://cdn.example.com/body.jpg"/>'
    xml = _rss(_item(content=content))
    items = parse_rss(xml)
    assert items[0]["thumbnail"] == "https://cdn.example.com/body.jpg"


@pytest.mark.unit
def test_thumbnail_empty_when_no_image():
    xml = _rss(_item(content="<p>just text, no images</p>"))
    items = parse_rss(xml)
    assert items[0]["thumbnail"] == ""


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_item_missing_title_is_skipped():
    xml = _rss(_item(title="") + _item(title="Good Post"))
    items = parse_rss(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Good Post"


@pytest.mark.unit
def test_item_missing_link_is_skipped():
    xml = _rss(_item(link="") + _item(link="https://medium.com/p/ok"))
    items = parse_rss(xml)
    assert len(items) == 1
    assert items[0]["link"] == "https://medium.com/p/ok"


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_format_date_rfc2822():
    assert format_date("Mon, 15 Jan 2024 12:00:00 GMT") == "Jan 15, 2024"


@pytest.mark.unit
def test_format_date_iso():
    assert format_date("2024-03-20T00:00:00Z") == "Mar 20, 2024"


@pytest.mark.unit
def test_format_date_failure_returns_raw():
    assert format_date("not-a-date") == "not-a-date"


@pytest.mark.unit
def test_format_date_empty_returns_empty():
    assert format_date("") == ""


# ---------------------------------------------------------------------------
# Empty feed
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_rss_feed_returns_empty_list():
    xml = _rss()
    items = parse_rss(xml)
    assert items == []


# ---------------------------------------------------------------------------
# Error paths — fetch_rss raises on bad HTTP
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_non_200_response_raises_exception():
    err = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.HTTPError):
            fetch_medium.fetch_rss("https://medium.com/feed/@user")


@pytest.mark.unit
def test_network_error_raises_exception():
    err = urllib.error.URLError(reason="Name or service not known")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(urllib.error.URLError):
            fetch_medium.fetch_rss("https://medium.com/feed/@user")


@pytest.mark.unit
def test_malformed_xml_raises_exception():
    with pytest.raises(Exception):
        parse_rss(b"this is not xml at all <<<")


# ---------------------------------------------------------------------------
# fetch_rss happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fetch_rss_returns_bytes():
    xml = _rss(_item())
    mock_resp = make_urllib_response(xml)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_medium.fetch_rss("https://medium.com/feed/@user")
    assert isinstance(result, bytes)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# main() error path — exits nonzero on any failure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_main_exits_nonzero_on_http_error():
    """main() must catch HTTPError and exit(1), not propagate."""
    err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    fake_args = Namespace(username="testuser", out="/dev/null")
    with patch("fetch_medium.fetch_rss", side_effect=err), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_medium.main()
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_main_exits_nonzero_on_malformed_xml():
    """main() must catch XML parse errors and exit(1)."""
    fake_args = Namespace(username="testuser", out="/dev/null")
    with patch("fetch_medium.fetch_rss", return_value=b"not valid xml <<<"), \
         patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
        with pytest.raises(SystemExit) as exc_info:
            fetch_medium.main()
    assert exc_info.value.code == 1
