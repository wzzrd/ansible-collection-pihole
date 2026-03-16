"""Tests for plugins/module_utils/dns.py"""

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.dns import (
    add_static_dns_record,
    check_static_dns_record_exists,
    delete_static_dns_record,
    find_conflicting_dns_records,
    get_static_dns_records,
    parse_dns_records,
)
from .helpers import make_response as _make_response, mock_client as _mock_client

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
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_static_dns_records(client)

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("timeout"))
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
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_static_dns_record(client, "1.2.3.4", "host.local")

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
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
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            delete_static_dns_record(client, "1.2.3.4", "host.local")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            delete_static_dns_record(client, "1.2.3.4", "host.local")


# ---------------------------------------------------------------------------
# parse_dns_records
# ---------------------------------------------------------------------------


class TestParseDnsRecords:
    def test_parses_ipv4_records(self):
        raw = ["192.168.1.10 host.local", "10.0.0.1 other.local"]
        result = parse_dns_records(raw)
        assert ("192.168.1.10", "host.local") in result
        assert ("10.0.0.1", "other.local") in result

    def test_parses_ipv6_records(self):
        raw = ["fd00::1 host.local"]
        result = parse_dns_records(raw)
        assert ("fd00::1", "host.local") in result

    def test_empty_list_returns_empty(self):
        assert parse_dns_records([]) == []

    def test_malformed_entry_skipped(self):
        raw = ["onlyone", "192.168.1.10 host.local"]
        result = parse_dns_records(raw)
        assert len(result) == 1
        assert result[0] == ("192.168.1.10", "host.local")

    def test_preserves_order(self):
        raw = ["1.1.1.1 a.local", "2.2.2.2 b.local", "3.3.3.3 c.local"]
        result = parse_dns_records(raw)
        assert result == [
            ("1.1.1.1", "a.local"),
            ("2.2.2.2", "b.local"),
            ("3.3.3.3", "c.local"),
        ]


# ---------------------------------------------------------------------------
# find_conflicting_dns_records
# ---------------------------------------------------------------------------


class TestFindConflictingDnsRecords:
    def test_no_conflicts_when_empty(self):
        assert find_conflicting_dns_records([], "1.2.3.4", "host.local") == []

    def test_exact_match_not_a_conflict(self):
        records = [("1.2.3.4", "host.local")]
        assert find_conflicting_dns_records(records, "1.2.3.4", "host.local") == []

    def test_same_ip_different_name_is_conflict(self):
        records = [("1.2.3.4", "other.local")]
        result = find_conflicting_dns_records(records, "1.2.3.4", "host.local")
        assert ("1.2.3.4", "other.local") in result

    def test_same_name_different_ipv4_is_conflict(self):
        records = [("1.2.3.5", "host.local")]
        result = find_conflicting_dns_records(records, "1.2.3.4", "host.local")
        assert ("1.2.3.5", "host.local") in result

    def test_ipv4_and_ipv6_same_name_not_a_conflict(self):
        # A record and AAAA record for the same hostname must coexist
        records = [("192.168.1.10", "nas.local")]
        result = find_conflicting_dns_records(records, "fd00::10", "nas.local")
        assert result == []

    def test_ipv6_and_ipv4_same_name_not_a_conflict(self):
        records = [("fd00::10", "nas.local")]
        result = find_conflicting_dns_records(records, "192.168.1.10", "nas.local")
        assert result == []

    def test_two_ipv6_same_name_is_conflict(self):
        records = [("fd00::1", "host.local")]
        result = find_conflicting_dns_records(records, "fd00::2", "host.local")
        assert ("fd00::1", "host.local") in result

    def test_multiple_conflicts_returned(self):
        records = [
            ("1.2.3.4", "other.local"),  # same IP, different name
            ("5.6.7.8", "host.local"),  # same name (both IPv4), different IP
            ("9.0.0.1", "unrelated.local"),  # no conflict
        ]
        result = find_conflicting_dns_records(records, "1.2.3.4", "host.local")
        assert ("1.2.3.4", "other.local") in result
        assert ("5.6.7.8", "host.local") in result
        assert ("9.0.0.1", "unrelated.local") not in result
