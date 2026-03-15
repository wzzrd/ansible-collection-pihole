"""Tests for plugins/module_utils/api_client.py"""

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
    PiholeResponse,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
    PiholeNotFoundError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_open_url_response(status_code=200, json_data=None, text=""):
    """Create a mock response for ansible.module_utils.urls.open_url."""
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
    elif text:
        body = text.encode("utf-8")
    else:
        body = b""
    mock_resp = MagicMock()
    mock_resp.status = status_code
    mock_resp.read.return_value = body
    return mock_resp


def _make_http_error(code, msg, body=b""):
    return urllib.error.HTTPError(
        url="https://pihole.local/api/test",
        code=code,
        msg=msg,
        hdrs=None,
        fp=BytesIO(body),
    )


def _make_client(base_url="https://pihole.local", sid="test-sid", timeout=10):
    return PiholeApiClient(base_url=base_url, sid=sid, timeout=timeout)


# ---------------------------------------------------------------------------
# PiholeApiClient.__init__
# ---------------------------------------------------------------------------


class TestPiholeApiClientInit:
    def test_trailing_slash_stripped(self):
        client = _make_client(base_url="https://pihole.local/")
        assert client.base_url == "https://pihole.local"

    def test_sid_stored(self):
        client = _make_client(sid="abc123")
        assert client.sid == "abc123"

    def test_sid_in_headers(self):
        client = _make_client(sid="abc123")
        assert client.headers == {"sid": "abc123"}

    def test_default_timeout(self):
        client = _make_client()
        assert client.timeout == 10

    def test_custom_timeout(self):
        client = _make_client(timeout=30)
        assert client.timeout == 30


# ---------------------------------------------------------------------------
# PiholeApiClient._request
# ---------------------------------------------------------------------------


class TestRequest:
    def setup_method(self):
        self.client = _make_client()

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_get_success(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200, {"key": "value"})
        resp = self.client._request("GET", "api/test")
        assert resp.status_code == 200
        mock_open_url.assert_called_once()

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_url_construction(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "/api/config/dns/hosts")
        url = mock_open_url.call_args.args[0]
        assert url == "https://pihole.local/api/config/dns/hosts"

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_sid_header_sent(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "api/test")
        headers = mock_open_url.call_args.kwargs["headers"]
        assert headers["sid"] == "test-sid"

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_validate_certs_false(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "api/test")
        assert mock_open_url.call_args.kwargs["validate_certs"] is False

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_post_with_json(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(201)
        payload = {"name": "group1"}
        self.client._request("POST", "api/groups", json_data=payload)
        assert json.loads(mock_open_url.call_args.kwargs["data"]) == payload

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_custom_timeout_used(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "api/test", timeout=60)
        assert mock_open_url.call_args.kwargs["timeout"] == 60

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_default_timeout_used(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "api/test")
        assert mock_open_url.call_args.kwargs["timeout"] == 10

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_401_raises_auth_error(self, mock_open_url):
        mock_open_url.side_effect = _make_http_error(
            401, "Unauthorized", b"Unauthorized"
        )
        with pytest.raises(PiholeAuthError) as exc_info:
            self.client._request("GET", "api/groups")
        assert exc_info.value.status_code == 401

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_404_raises_not_found_error(self, mock_open_url):
        mock_open_url.side_effect = _make_http_error(404, "Not Found", b"Not Found")
        with pytest.raises(PiholeNotFoundError) as exc_info:
            self.client._request("GET", "api/groups/nonexistent")
        assert exc_info.value.status_code == 404

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_timeout_raises_connection_error(self, mock_open_url):
        mock_open_url.side_effect = urllib.error.URLError("timed out")
        with pytest.raises(PiholeConnectionError) as exc_info:
            self.client._request("GET", "api/test")
        assert "timed out" in str(exc_info.value)

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_connection_error_raises_connection_error(self, mock_open_url):
        mock_open_url.side_effect = urllib.error.URLError("Connection refused")
        with pytest.raises(PiholeConnectionError) as exc_info:
            self.client._request("GET", "api/test")
        assert "Failed to connect" in str(exc_info.value)

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_generic_exception_raises_api_error(self, mock_open_url):
        mock_open_url.side_effect = RuntimeError("boom")
        with pytest.raises(PiholeApiError):
            self.client._request("GET", "api/test")

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_params_forwarded(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200)
        self.client._request("GET", "api/lists", params={"type": "block"})
        url = mock_open_url.call_args.args[0]
        assert "type=block" in url

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_non_401_404_http_error_returns_response(self, mock_open_url):
        mock_open_url.side_effect = _make_http_error(400, "Bad Request", b"bad input")
        resp = self.client._request("GET", "api/test")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PiholeApiClient.authenticate (classmethod)
# ---------------------------------------------------------------------------


class TestAuthenticate:
    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_success_returns_sid(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(
            200, {"session": {"sid": "my-session-id"}}
        )
        sid = PiholeApiClient.authenticate("https://pihole.local", "secret")
        assert sid == "my-session-id"

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_posts_to_api_auth(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local", "pass")
        url = mock_open_url.call_args.args[0]
        assert url == "https://pihole.local/api/auth"

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_trailing_slash_stripped_from_url(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local/", "pass")
        url = mock_open_url.call_args.args[0]
        assert url == "https://pihole.local/api/auth"

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_password_sent_in_body(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local", "mypassword")
        assert json.loads(mock_open_url.call_args.kwargs["data"]) == {
            "password": "mypassword"
        }

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_non_200_raises_auth_error(self, mock_open_url):
        mock_open_url.side_effect = _make_http_error(403, "Forbidden", b"Forbidden")
        with pytest.raises(PiholeAuthError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "wrong")
        assert exc_info.value.status_code == 403

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_missing_sid_in_response_raises_auth_error(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200, {"session": {}})
        with pytest.raises(PiholeAuthError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "pass")
        assert "No session ID" in str(exc_info.value)

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_missing_session_key_raises_auth_error(self, mock_open_url):
        mock_open_url.return_value = _make_open_url_response(200, {})
        with pytest.raises(PiholeAuthError):
            PiholeApiClient.authenticate("https://pihole.local", "pass")

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_timeout_raises_connection_error(self, mock_open_url):
        mock_open_url.side_effect = urllib.error.URLError("timed out")
        with pytest.raises(PiholeConnectionError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "pass")
        assert "timed out" in str(exc_info.value)

    @patch("ansible_collections.wzzrd.pihole.plugins.module_utils.api_client.open_url")
    def test_connection_error_raises_connection_error(self, mock_open_url):
        mock_open_url.side_effect = urllib.error.URLError("no route to host")
        with pytest.raises(PiholeConnectionError):
            PiholeApiClient.authenticate("https://pihole.local", "pass")


# ---------------------------------------------------------------------------
# PiholeResponse
# ---------------------------------------------------------------------------


class TestPiholeResponse:
    def test_status_code(self):
        resp = PiholeResponse(200, b"ok")
        assert resp.status_code == 200

    def test_text(self):
        resp = PiholeResponse(200, b"hello")
        assert resp.text == "hello"

    def test_json(self):
        resp = PiholeResponse(200, json.dumps({"key": "val"}).encode())
        assert resp.json() == {"key": "val"}

    def test_json_invalid_raises_api_error(self):
        resp = PiholeResponse(200, b"not json")
        with pytest.raises(PiholeApiError):
            resp.json()

    def test_raise_for_status_ok(self):
        resp = PiholeResponse(200, b"")
        resp.raise_for_status()  # should not raise

    def test_raise_for_status_error(self):
        resp = PiholeResponse(500, b"server error")
        with pytest.raises(PiholeApiError):
            resp.raise_for_status()
