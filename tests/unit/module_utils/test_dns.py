"""Tests for plugins/module_utils/dns.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.dns import (
    add_static_dns_record,
    check_static_dns_record_exists,
    delete_static_dns_record,
    get_static_dns_records,
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


def _mock_client(request_return=None, request_side_effect=None):
    client = MagicMock()
    if request_side_effect:
        client._request.side_effect = request_side_effect
    else:
        client._request.return_value = request_return
    return client


DNS_RESPONSE = {
    "config": {
        "dns": {
            "hosts": [
                "192.168.88.10 nas01.acme.lab",
                "192.168.88.20 workstation.acme.lab",
                "fd00:dead:beef::10 nas01.acme.lab",
            ]
        }
    }
}


# ---------------------------------------------------------------------------
# get_static_dns_records
# ---------------------------------------------------------------------------


class TestGetStaticDnsRecords:
    def test_returns_list(self):
        client = _mock_client(_make_response(200, DNS_RESPONSE))
        records = get_static_dns_records(client)
        assert isinstance(records, list)
        assert len(records) == 3

    def test_correct_format(self):
        client = _mock_client(_make_response(200, DNS_RESPONSE))
        records = get_static_dns_records(client)
        assert "192.168.88.10 nas01.acme.lab" in records

    def test_empty_hosts_returns_empty_list(self):
        resp = _make_response(200, {"config": {"dns": {"hosts": []}}})
        client = _mock_client(resp)
        assert get_static_dns_records(client) == []

    def test_missing_keys_returns_empty_list(self):
        client = _mock_client(_make_response(200, {}))
        assert get_static_dns_records(client) == []

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, DNS_RESPONSE))
        get_static_dns_records(client)
        client._request.assert_called_once_with("GET", "api/config/dns/hosts")

    def test_auth_error_propagates(self):
        client = _mock_client(request_side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_static_dns_records(client)

    def test_connection_error_propagates(self):
        client = _mock_client(request_side_effect=PiholeConnectionError("timeout"))
        with pytest.raises(PiholeConnectionError):
            get_static_dns_records(client)


# ---------------------------------------------------------------------------
# check_static_dns_record_exists
# ---------------------------------------------------------------------------


class TestCheckStaticDnsRecordExists:
    def setup_method(self):
        self.client = _mock_client(_make_response(200, DNS_RESPONSE))

    def test_existing_record_returns_true(self):
        assert (
            check_static_dns_record_exists(
                self.client, "192.168.88.10", "nas01.acme.lab"
            )
            is True
        )

    def test_missing_record_returns_false(self):
        assert (
            check_static_dns_record_exists(
                self.client, "192.168.88.99", "unknown.acme.lab"
            )
            is False
        )

    def test_partial_ip_returns_false(self):
        assert (
            check_static_dns_record_exists(
                self.client, "192.168.88.1", "nas01.acme.lab"
            )
            is False
        )

    def test_partial_name_returns_false(self):
        assert (
            check_static_dns_record_exists(self.client, "192.168.88.10", "nas01")
            is False
        )

    def test_ipv6_record_found(self):
        assert (
            check_static_dns_record_exists(
                self.client, "fd00:dead:beef::10", "nas01.acme.lab"
            )
            is True
        )


# ---------------------------------------------------------------------------
# add_static_dns_record
# ---------------------------------------------------------------------------


class TestAddStaticDnsRecord:
    def test_returns_api_response(self):
        resp = _make_response(200, {"result": "ok"})
        client = _mock_client(resp)
        result = add_static_dns_record(client, "192.168.88.30", "laptop.acme.lab")
        assert result == {"result": "ok"}

    def test_calls_put_method(self):
        resp = _make_response(200, {})
        client = _mock_client(resp)
        add_static_dns_record(client, "192.168.88.30", "laptop.acme.lab")
        client._request.assert_called_once()
        call_args = client._request.call_args
        assert call_args.args[0] == "PUT"

    def test_url_encodes_space_as_percent20(self):
        resp = _make_response(200, {})
        client = _mock_client(resp)
        add_static_dns_record(client, "192.168.88.30", "laptop.acme.lab")
        endpoint = client._request.call_args.args[1]
        assert "192.168.88.30%20laptop.acme.lab" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(request_side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_static_dns_record(client, "1.2.3.4", "host.local")

    def test_connection_error_propagates(self):
        client = _mock_client(request_side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            add_static_dns_record(client, "1.2.3.4", "host.local")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = ValueError("oops")
        with pytest.raises(PiholeApiError):
            add_static_dns_record(client, "1.2.3.4", "host.local")


# ---------------------------------------------------------------------------
# delete_static_dns_record
# ---------------------------------------------------------------------------


class TestDeleteStaticDnsRecord:
    def test_successful_delete_returns_none(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        result = delete_static_dns_record(client, "192.168.88.10", "nas01.acme.lab")
        assert result is None

    def test_calls_delete_method(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        delete_static_dns_record(client, "192.168.88.10", "nas01.acme.lab")
        call_args = client._request.call_args
        assert call_args.args[0] == "DELETE"

    def test_url_encodes_space_as_percent20(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        delete_static_dns_record(client, "192.168.88.10", "nas01.acme.lab")
        endpoint = client._request.call_args.args[1]
        assert "192.168.88.10%20nas01.acme.lab" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(request_side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            delete_static_dns_record(client, "1.2.3.4", "host.local")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            delete_static_dns_record(client, "1.2.3.4", "host.local")
