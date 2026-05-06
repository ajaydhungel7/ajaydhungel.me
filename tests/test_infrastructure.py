"""Sanity tests — verify the test infrastructure itself works."""
import sys
import os
import pytest


@pytest.mark.unit
def test_scripts_on_path():
    """scripts/ must be importable so unit tests can import functions directly."""
    scripts_path = os.path.join(os.path.dirname(__file__), "..", "scripts")
    assert os.path.isdir(os.path.realpath(scripts_path)), "scripts/ directory must exist"


@pytest.mark.unit
def test_import_fetch_github():
    import fetch_github  # noqa: F401


@pytest.mark.unit
def test_import_fetch_medium():
    import fetch_medium  # noqa: F401


@pytest.mark.unit
def test_import_fetch_devto():
    import fetch_devto  # noqa: F401


@pytest.mark.unit
def test_import_fetch_credly():
    import fetch_credly  # noqa: F401
