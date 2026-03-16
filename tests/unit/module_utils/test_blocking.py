"""Tests for plugins/module_utils/blocking.py"""

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.blocking import (
    get_blocking_status,
    set_blocking_status,
)
from .helpers import make_response as _make_response, mock_client as _mock_client

# ---------------------------------------------------------------------------
# get_blocking_status
# ---------------------------------------------------------------------------


class TestGetBlockingStatus:
    def test_returns_status_dict(self):
        payload = {"blocking": "enabled", "timer": None}
        client = _mock_client(_make_response(200, payload))
        result = get_blocking_status(client)
        assert result == payload

    def test_disabled_with_timer(self):
        payload = {"blocking": "disabled", "timer": 300}
        client = _mock_client(_make_response(200, payload))
        result = get_blocking_status(client)
        assert result["blocking"] == "disabled"
        assert result["timer"] == 300

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, {"blocking": "enabled"}))
        get_blocking_status(client)
        client._request.assert_called_once_with("GET", "api/dns/blocking")

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_blocking_status(client)

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            get_blocking_status(client)

    def test_unexpected_error_wrapped(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            get_blocking_status(client)


# ---------------------------------------------------------------------------
# set_blocking_status
# ---------------------------------------------------------------------------


class TestSetBlockingStatus:
    def test_enable_blocking(self):
        payload = {"blocking": True, "timer": None}
        client = _mock_client(_make_response(200, payload))
        result = set_blocking_status(client, enabled=True)
        assert result["blocking"] is True

    def test_disable_blocking(self):
        payload = {"blocking": False, "timer": None}
        client = _mock_client(_make_response(200, payload))
        result = set_blocking_status(client, enabled=False)
        assert result["blocking"] is False

    def test_calls_post_to_correct_endpoint(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=True)
        assert client._request.call_args.args[0] == "POST"
        assert client._request.call_args.args[1] == "api/dns/blocking"

    def test_payload_has_blocking_true(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=True)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["blocking"] is True

    def test_payload_has_blocking_false(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=False)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["blocking"] is False

    def test_timer_included_when_positive(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=False, timer=300)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["timer"] == 300

    def test_timer_omitted_when_none(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=True, timer=None)
        payload = client._request.call_args.kwargs["json_data"]
        assert "timer" not in payload

    def test_timer_omitted_when_zero(self):
        client = _mock_client(_make_response(200, {}))
        set_blocking_status(client, enabled=True, timer=0)
        payload = client._request.call_args.kwargs["json_data"]
        assert "timer" not in payload

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            set_blocking_status(client, enabled=True)

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            set_blocking_status(client, enabled=True)

    def test_unexpected_error_wrapped(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            set_blocking_status(client, enabled=True)
