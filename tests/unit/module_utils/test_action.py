"""Tests for plugins/module_utils/action.py"""

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.action import (
    perform_action,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
    PiholeValidationError,
)
from .helpers import make_response as _make_response, mock_client as _mock_client

# ---------------------------------------------------------------------------
# perform_action
# ---------------------------------------------------------------------------


class TestPerformAction:
    def test_gravity_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, {"status": "ok"}))
        perform_action(client, "gravity")
        client._request.assert_called_once()
        args = client._request.call_args
        assert args.args[0] == "POST"
        assert "api/action/gravity" in args.args[1]

    def test_restartdns_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, {}))
        perform_action(client, "restartdns")
        assert "api/action/restartdns" in client._request.call_args.args[1]

    def test_flush_logs_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, {}))
        perform_action(client, "flush_logs")
        assert "api/action/flush/logs" in client._request.call_args.args[1]

    def test_flush_arp_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, {}))
        perform_action(client, "flush_arp")
        assert "api/action/flush/arp" in client._request.call_args.args[1]

    def test_unsupported_action_raises_validation_error(self):
        client = _mock_client(_make_response(200, {}))
        with pytest.raises(PiholeValidationError) as exc_info:
            perform_action(client, "reboot")
        assert "reboot" in str(exc_info.value)

    def test_gravity_uses_extended_timeout(self):
        client = _mock_client(_make_response(200, {}))
        client.timeout = 10
        perform_action(client, "gravity")
        timeout_used = client._request.call_args.kwargs.get("timeout")
        assert timeout_used == 300

    def test_non_gravity_uses_default_timeout(self):
        client = _mock_client(_make_response(200, {}))
        client.timeout = 10
        perform_action(client, "restartdns")
        timeout_used = client._request.call_args.kwargs.get("timeout")
        assert timeout_used == 10

    def test_returns_json_on_success(self):
        client = _mock_client(_make_response(200, {"result": "done"}))
        result = perform_action(client, "restartdns")
        assert result == {"result": "done"}

    def test_non_json_response_returns_success_dict(self):
        resp = _make_response(200, text="OK")
        resp.json.side_effect = PiholeApiError("not json")
        client = _mock_client(resp)
        result = perform_action(client, "restartdns")
        assert result["success"] is True
        assert "restartdns" in result["message"]

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            perform_action(client, "gravity")

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            perform_action(client, "restartdns")

    def test_unexpected_error_wrapped(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            perform_action(client, "gravity")
