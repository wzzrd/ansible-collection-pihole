"""Tests for plugins/module_utils/api_client.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
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

def _make_response(status_code=200, json_data=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


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

    @patch("requests.request")
    def test_get_success(self, mock_req):
        mock_req.return_value = _make_response(200, {"key": "value"})
        resp = self.client._request("GET", "api/test")
        assert resp.status_code == 200
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert "api/test" in call_kwargs.kwargs["url"]

    @patch("requests.request")
    def test_url_construction(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "/api/config/dns/hosts")
        url = mock_req.call_args.kwargs["url"]
        assert url == "https://pihole.local/api/config/dns/hosts"

    @patch("requests.request")
    def test_sid_header_sent(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "api/test")
        headers = mock_req.call_args.kwargs["headers"]
        assert headers == {"sid": "test-sid"}

    @patch("requests.request")
    def test_verify_false(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "api/test")
        assert mock_req.call_args.kwargs["verify"] is False

    @patch("requests.request")
    def test_post_with_json(self, mock_req):
        mock_req.return_value = _make_response(201)
        payload = {"name": "group1"}
        self.client._request("POST", "api/groups", json_data=payload)
        assert mock_req.call_args.kwargs["json"] == payload

    @patch("requests.request")
    def test_custom_timeout_used(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "api/test", timeout=60)
        assert mock_req.call_args.kwargs["timeout"] == 60

    @patch("requests.request")
    def test_default_timeout_used(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "api/test")
        assert mock_req.call_args.kwargs["timeout"] == 10

    @patch("requests.request")
    def test_401_raises_auth_error(self, mock_req):
        mock_req.return_value = _make_response(401, text="Unauthorized")
        with pytest.raises(PiholeAuthError) as exc_info:
            self.client._request("GET", "api/groups")
        assert exc_info.value.status_code == 401

    @patch("requests.request")
    def test_404_raises_not_found_error(self, mock_req):
        mock_req.return_value = _make_response(404, text="Not Found")
        with pytest.raises(PiholeNotFoundError) as exc_info:
            self.client._request("GET", "api/groups/nonexistent")
        assert exc_info.value.status_code == 404

    @patch("requests.request")
    def test_timeout_raises_connection_error(self, mock_req):
        mock_req.side_effect = requests.exceptions.Timeout()
        with pytest.raises(PiholeConnectionError) as exc_info:
            self.client._request("GET", "api/test")
        assert "timed out" in str(exc_info.value)

    @patch("requests.request")
    def test_connection_error_raises_connection_error(self, mock_req):
        mock_req.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(PiholeConnectionError) as exc_info:
            self.client._request("GET", "api/test")
        assert "Failed to connect" in str(exc_info.value)

    @patch("requests.request")
    def test_generic_request_exception_raises_api_error(self, mock_req):
        mock_req.side_effect = requests.exceptions.RequestException("boom")
        with pytest.raises(PiholeApiError):
            self.client._request("GET", "api/test")

    @patch("requests.request")
    def test_params_forwarded(self, mock_req):
        mock_req.return_value = _make_response(200)
        self.client._request("GET", "api/lists", params={"type": "block"})
        assert mock_req.call_args.kwargs["params"] == {"type": "block"}


# ---------------------------------------------------------------------------
# PiholeApiClient.authenticate (classmethod)
# ---------------------------------------------------------------------------

class TestAuthenticate:
    @patch("requests.post")
    def test_success_returns_sid(self, mock_post):
        mock_post.return_value = _make_response(
            200, {"session": {"sid": "my-session-id"}}
        )
        sid = PiholeApiClient.authenticate("https://pihole.local", "secret")
        assert sid == "my-session-id"

    @patch("requests.post")
    def test_posts_to_api_auth(self, mock_post):
        mock_post.return_value = _make_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local", "pass")
        url = mock_post.call_args.args[0]
        assert url == "https://pihole.local/api/auth"

    @patch("requests.post")
    def test_trailing_slash_stripped_from_url(self, mock_post):
        mock_post.return_value = _make_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local/", "pass")
        url = mock_post.call_args.args[0]
        assert url == "https://pihole.local/api/auth"

    @patch("requests.post")
    def test_password_sent_in_body(self, mock_post):
        mock_post.return_value = _make_response(
            200, {"session": {"sid": "sid123"}}
        )
        PiholeApiClient.authenticate("https://pihole.local", "mypassword")
        assert mock_post.call_args.kwargs["json"] == {"password": "mypassword"}

    @patch("requests.post")
    def test_non_200_raises_auth_error(self, mock_post):
        mock_post.return_value = _make_response(403, text="Forbidden")
        with pytest.raises(PiholeAuthError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "wrong")
        assert exc_info.value.status_code == 403

    @patch("requests.post")
    def test_missing_sid_in_response_raises_auth_error(self, mock_post):
        mock_post.return_value = _make_response(200, {"session": {}})
        with pytest.raises(PiholeAuthError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "pass")
        assert "No session ID" in str(exc_info.value)

    @patch("requests.post")
    def test_missing_session_key_raises_auth_error(self, mock_post):
        mock_post.return_value = _make_response(200, {})
        with pytest.raises(PiholeAuthError):
            PiholeApiClient.authenticate("https://pihole.local", "pass")

    @patch("requests.post")
    def test_timeout_raises_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout()
        with pytest.raises(PiholeConnectionError) as exc_info:
            PiholeApiClient.authenticate("https://pihole.local", "pass")
        assert "timed out" in str(exc_info.value)

    @patch("requests.post")
    def test_connection_error_raises_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("no route")
        with pytest.raises(PiholeConnectionError):
            PiholeApiClient.authenticate("https://pihole.local", "pass")
