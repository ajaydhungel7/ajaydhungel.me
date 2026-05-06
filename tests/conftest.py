"""Shared fixtures for all tests."""
import json
import sys
import os
from unittest.mock import MagicMock

# Make scripts importable as modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def make_urllib_response(data):
    """
    Build a mock object that satisfies urllib.request.urlopen as a context manager.
    data can be dict/list (serialised to JSON), str, or bytes.
    """
    if isinstance(data, (dict, list)):
        content = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        content = data.encode("utf-8")
    else:
        content = data

    mock_resp = MagicMock()
    mock_resp.read.return_value = content
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp
