"""
Integration tests — Hugo build smoke test.

Runs `hugo --buildFuture` against the real site and asserts:
  - Build exits 0
  - Key output files exist and are non-empty
  - No shortcode error strings appear in rendered HTML
  - Internal anchor hrefs point to files that actually exist in public/
"""
import os
import re
import subprocess
import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
PUBLIC_DIR = os.path.join(REPO_ROOT, "public")

# Strings emitted by shortcodes when data is missing
SHORTCODE_ERROR_STRINGS = [
    "no projects found",
    "no articles found",
    "no talks found",
    "no badges found",
]

# Pages that must exist after a successful build
REQUIRED_PAGES = [
    "index.html",
    "404.html",
    "sitemap.xml",
    "blog/index.html",
    "projects/index.html",
    "certifications/index.html",
    "talks/index.html",
    "about/index.html",
]


@pytest.fixture(scope="module")
def hugo_build():
    """Run hugo once per module; return the CompletedProcess result."""
    result = subprocess.run(
        ["hugo", "--buildFuture"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result


# ---------------------------------------------------------------------------
# Build succeeds
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_hugo_exits_zero(hugo_build):
    assert hugo_build.returncode == 0, (
        f"hugo exited {hugo_build.returncode}\n"
        f"stdout: {hugo_build.stdout[-2000:]}\n"
        f"stderr: {hugo_build.stderr[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Required output files exist
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("page", REQUIRED_PAGES)
def test_required_page_exists(hugo_build, page):
    path = os.path.join(PUBLIC_DIR, page)
    assert os.path.isfile(path), f"public/{page} not found after build"
    assert os.path.getsize(path) > 0, f"public/{page} is empty"


# ---------------------------------------------------------------------------
# No shortcode error strings in rendered HTML
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("error_string", SHORTCODE_ERROR_STRINGS)
def test_no_shortcode_errors_in_html(hugo_build, error_string):
    """
    If a data file is missing or empty, shortcodes render an error string.
    A successful build must not contain any of these.
    """
    for dirpath, _, filenames in os.walk(PUBLIC_DIR):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            assert error_string.lower() not in content.lower(), (
                f"Shortcode error '{error_string}' found in {fpath}"
            )


# ---------------------------------------------------------------------------
# Internal links resolve
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_internal_links_resolve(hugo_build):
    """
    Every internal href (not starting with http/mailto/#) in the built HTML
    must resolve to a real file under public/.
    """
    HREF_RE = re.compile(r'href="(/[^"#?][^"]*)"')
    broken = []

    for dirpath, _, filenames in os.walk(PUBLIC_DIR):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue

            for href in HREF_RE.findall(content):
                # Strip query strings and fragments
                path = href.split("?")[0].split("#")[0].rstrip("/")
                if not path:
                    continue

                # Try as a file directly, or as a directory index
                candidates = [
                    os.path.join(PUBLIC_DIR, path.lstrip("/")),
                    os.path.join(PUBLIC_DIR, path.lstrip("/"), "index.html"),
                ]
                if not any(os.path.isfile(c) for c in candidates):
                    broken.append(f"{fpath}: href={href!r}")

    assert not broken, (
        f"{len(broken)} broken internal link(s) found:\n" + "\n".join(broken[:20])
    )
