"""
Integration tests — content lint.

Parses every .md file in content/ and asserts structural correctness:
  - All files have YAML frontmatter
  - Posts in content/posts/ have required fields (title, date, description, tags)
  - No post has draft: true (drafts should not be merged to main)
  - tech field values (if present) use the Simple Icons / custom slug allowlist
  - Every image referenced in frontmatter cover/images exists on disk
  - Every markdown body image reference exists on disk
"""
import os
import re
import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CONTENT_DIR = os.path.join(REPO_ROOT, "content")

# Valid tech/icon slugs used in post_meta.html
VALID_TECH_SLUGS = {
    "kubernetes", "aws", "terraform", "github-actions", "nginx",
    "docker", "argocd", "gitops", "iac", "terragrunt", "eks",
    "cicd", "devops", "networking", "gateway-api",
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
COVER_IMAGE_RE = re.compile(r"^\s*image:\s*(.+)$", re.MULTILINE)
MD_IMAGE_RE = re.compile(r"!\[.*?\]\((/[^)]+)\)")


def _all_md_files():
    """Yield (path, rel_path) for every .md in content/."""
    for dirpath, _, filenames in os.walk(CONTENT_DIR):
        for fname in filenames:
            if fname.endswith(".md"):
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, REPO_ROOT)
                yield full, rel


def _post_md_files():
    """Yield (path, rel_path) for actual posts only (excludes _index.md)."""
    posts_dir = os.path.join(CONTENT_DIR, "posts")
    if not os.path.isdir(posts_dir):
        return
    for fname in os.listdir(posts_dir):
        if fname.endswith(".md") and fname != "_index.md":
            full = os.path.join(posts_dir, fname)
            rel = os.path.relpath(full, REPO_ROOT)
            yield full, rel


def _parse_frontmatter(content):
    """Return raw frontmatter string, or None if not found."""
    m = FRONTMATTER_RE.match(content)
    return m.group(1) if m else None


def _fm_value(frontmatter, key):
    """Very light key extraction — handles simple scalar values."""
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+)$", re.MULTILINE)
    m = pattern.search(frontmatter)
    return m.group(1).strip().strip('"\'') if m else None


def _fm_list(frontmatter, key):
    """Extract inline YAML list like: tags: ["a", "b"]"""
    pattern = re.compile(rf"^{re.escape(key)}:\s*\[([^\]]*)\]", re.MULTILINE)
    m = pattern.search(frontmatter)
    if not m:
        return []
    raw = m.group(1)
    return [v.strip().strip('"\'') for v in raw.split(",") if v.strip()]


# ---------------------------------------------------------------------------
# All markdown files have frontmatter
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_all_md_files()))
def test_file_has_frontmatter(path, rel):
    content = open(path, encoding="utf-8").read()
    fm = _parse_frontmatter(content)
    assert fm is not None, f"{rel}: missing YAML frontmatter (must start with ---)"


# ---------------------------------------------------------------------------
# Posts have required fields
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_post_md_files()))
def test_post_has_required_fields(path, rel):
    content = open(path, encoding="utf-8").read()
    fm = _parse_frontmatter(content)
    assert fm is not None, f"{rel}: missing frontmatter"

    for field in ("title", "date", "description"):
        value = _fm_value(fm, field)
        assert value, f"{rel}: required field '{field}' is missing or empty"

    tags = _fm_list(fm, "tags")
    assert tags, f"{rel}: 'tags' must be a non-empty list"


# ---------------------------------------------------------------------------
# No draft: true posts
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_post_md_files()))
def test_post_is_not_draft(path, rel):
    content = open(path, encoding="utf-8").read()
    fm = _parse_frontmatter(content)
    if fm is None:
        return
    draft = _fm_value(fm, "draft")
    assert draft != "true", (
        f"{rel}: draft: true — drafts must not be merged to main"
    )


# ---------------------------------------------------------------------------
# tech slugs are valid
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_post_md_files()))
def test_tech_slugs_are_valid(path, rel):
    content = open(path, encoding="utf-8").read()
    fm = _parse_frontmatter(content)
    if fm is None:
        return
    slugs = _fm_list(fm, "tech")
    invalid = [s for s in slugs if s not in VALID_TECH_SLUGS]
    assert not invalid, (
        f"{rel}: unrecognised tech slug(s) {invalid}. "
        f"Valid slugs: {sorted(VALID_TECH_SLUGS)}"
    )


# ---------------------------------------------------------------------------
# Frontmatter cover image exists on disk
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_post_md_files()))
def test_frontmatter_cover_image_exists(path, rel):
    content = open(path, encoding="utf-8").read()
    fm = _parse_frontmatter(content)
    if fm is None:
        return

    # cover:\n  image: /path
    m = COVER_IMAGE_RE.search(fm)
    if not m:
        return  # no cover image — that's fine

    img_path = m.group(1).strip()
    if not img_path.startswith("/"):
        return  # external URL — skip

    on_disk = os.path.join(REPO_ROOT, "static", img_path.lstrip("/"))
    # Also check public/ (some images are placed there directly)
    on_disk_public = os.path.join(REPO_ROOT, "public", img_path.lstrip("/"))
    theme_static = os.path.join(REPO_ROOT, "themes", "charlolamode", "static", img_path.lstrip("/"))

    found = any(os.path.isfile(p) for p in [on_disk, on_disk_public, theme_static])
    assert found, (
        f"{rel}: cover image '{img_path}' not found at "
        f"static{img_path}, public{img_path}, or theme static"
    )


# ---------------------------------------------------------------------------
# Markdown body image references exist on disk
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("path,rel", list(_all_md_files()))
def test_body_images_exist(path, rel):
    content = open(path, encoding="utf-8").read()
    # Strip frontmatter before scanning
    body = FRONTMATTER_RE.sub("", content, count=1)

    missing = []
    for img_path in MD_IMAGE_RE.findall(body):
        on_disk = os.path.join(REPO_ROOT, "static", img_path.lstrip("/"))
        on_disk_public = os.path.join(REPO_ROOT, "public", img_path.lstrip("/"))
        theme_static = os.path.join(REPO_ROOT, "themes", "charlolamode", "static", img_path.lstrip("/"))
        if not any(os.path.isfile(p) for p in [on_disk, on_disk_public, theme_static]):
            missing.append(img_path)

    assert not missing, (
        f"{rel}: body references missing image(s): {missing}"
    )
