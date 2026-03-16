"""Shared test helpers for module_utils tests."""

from unittest.mock import MagicMock

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import PiholeResponse


def make_response(status_code=200, json_data=None, text=""):
    resp = MagicMock(spec=PiholeResponse)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


def mock_client(return_value=None, side_effect=None):
    c = MagicMock()
    if side_effect:
        c._request.side_effect = side_effect
    else:
        c._request.return_value = return_value
    return c
