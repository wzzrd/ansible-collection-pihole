"""Tests for plugins/module_utils/dhcp.py"""

from unittest.mock import MagicMock

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.dhcp import (
    add_dhcp_reservation,
    check_dhcp_reservation_exists,
    delete_dhcp_reservation,
    get_dhcp_reservations,
)


def _make_response(status_code=200, json_data=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = ""
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


def _mock_client(return_value=None, side_effect=None):
    c = MagicMock()
    if side_effect:
        c._request.side_effect = side_effect
    else:
        c._request.return_value = return_value
    return c


DHCP_RESPONSE = {
    "config": {
        "dhcp": {
            "hosts": [
                "de:ad:be:ef:00:01,192.168.88.10,nas01",
                "DE:AD:BE:EF:00:02,192.168.88.20,workstation",
                "de:ad:be:ef:00:03,192.168.88.30,laptop",
            ]
        }
    }
}


class TestGetDhcpReservations:
    def test_returns_list(self):
        client = _mock_client(_make_response(200, DHCP_RESPONSE))
        records = get_dhcp_reservations(client)
        assert len(records) == 3

    def test_correct_format(self):
        client = _mock_client(_make_response(200, DHCP_RESPONSE))
        records = get_dhcp_reservations(client)
        assert "de:ad:be:ef:00:01,192.168.88.10,nas01" in records

    def test_empty_returns_empty_list(self):
        resp = _make_response(200, {"config": {"dhcp": {"hosts": []}}})
        client = _mock_client(resp)
        assert get_dhcp_reservations(client) == []

    def test_missing_keys_returns_empty_list(self):
        client = _mock_client(_make_response(200, {}))
        assert get_dhcp_reservations(client) == []

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, DHCP_RESPONSE))
        get_dhcp_reservations(client)
        client._request.assert_called_once_with("GET", "api/config/dhcp/hosts")

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_dhcp_reservations(client)

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            get_dhcp_reservations(client)


class TestCheckDhcpReservationExists:
    def setup_method(self):
        self.client = _mock_client(_make_response(200, DHCP_RESPONSE))

    def test_existing_reservation_lowercase_returns_true(self):
        assert (
            check_dhcp_reservation_exists(
                self.client, "de:ad:be:ef:00:01", "192.168.88.10", "nas01"
            )
            is True
        )

    def test_case_insensitive_mac_match(self):
        # DE:AD:BE:EF:00:02 is in the list; querying with lowercase should still match
        assert (
            check_dhcp_reservation_exists(
                self.client, "de:ad:be:ef:00:02", "192.168.88.20", "workstation"
            )
            is True
        )

    def test_uppercase_query_matches_lowercase_stored(self):
        assert (
            check_dhcp_reservation_exists(
                self.client, "DE:AD:BE:EF:00:01", "192.168.88.10", "nas01"
            )
            is True
        )

    def test_wrong_ip_returns_false(self):
        assert (
            check_dhcp_reservation_exists(
                self.client, "de:ad:be:ef:00:01", "192.168.88.99", "nas01"
            )
            is False
        )

    def test_wrong_name_returns_false(self):
        assert (
            check_dhcp_reservation_exists(
                self.client, "de:ad:be:ef:00:01", "192.168.88.10", "wrongname"
            )
            is False
        )

    def test_nonexistent_returns_false(self):
        assert (
            check_dhcp_reservation_exists(
                self.client, "aa:bb:cc:dd:ee:ff", "10.0.0.1", "unknown"
            )
            is False
        )


class TestAddDhcpReservation:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(200, {"result": "ok"}))
        result = add_dhcp_reservation(
            client, "de:ad:be:ef:00:04", "192.168.88.40", "printer"
        )
        assert result == {"result": "ok"}

    def test_mac_normalized_to_lowercase(self):
        client = _mock_client(_make_response(200, {}))
        add_dhcp_reservation(client, "DE:AD:BE:EF:00:04", "192.168.88.40", "printer")
        endpoint = client._request.call_args.args[1]
        assert "de:ad:be:ef:00:04" in endpoint
        assert "DE:AD:BE:EF:00:04" not in endpoint

    def test_calls_put_method(self):
        client = _mock_client(_make_response(200, {}))
        add_dhcp_reservation(client, "de:ad:be:ef:00:04", "192.168.88.40", "printer")
        assert client._request.call_args.args[0] == "PUT"

    def test_endpoint_contains_comma_separated_values(self):
        client = _mock_client(_make_response(200, {}))
        add_dhcp_reservation(client, "de:ad:be:ef:00:04", "192.168.88.40", "printer")
        endpoint = client._request.call_args.args[1]
        assert "de:ad:be:ef:00:04,192.168.88.40,printer" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_dhcp_reservation(client, "aa:bb:cc:dd:ee:ff", "1.2.3.4", "host")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("boom")
        with pytest.raises(PiholeApiError):
            add_dhcp_reservation(client, "aa:bb:cc:dd:ee:ff", "1.2.3.4", "host")


class TestDeleteDhcpReservation:
    def test_successful_delete_returns_none(self):
        client = _mock_client(_make_response(204))
        result = delete_dhcp_reservation(
            client, "de:ad:be:ef:00:01", "192.168.88.10", "nas01"
        )
        assert result is None

    def test_mac_normalized_to_lowercase(self):
        client = _mock_client(_make_response(204))
        delete_dhcp_reservation(client, "DE:AD:BE:EF:00:01", "192.168.88.10", "nas01")
        endpoint = client._request.call_args.args[1]
        assert "de:ad:be:ef:00:01" in endpoint

    def test_calls_delete_method(self):
        client = _mock_client(_make_response(204))
        delete_dhcp_reservation(client, "de:ad:be:ef:00:01", "192.168.88.10", "nas01")
        assert client._request.call_args.args[0] == "DELETE"

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            delete_dhcp_reservation(client, "aa:bb:cc:dd:ee:ff", "1.2.3.4", "host")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = ValueError("bad")
        with pytest.raises(PiholeApiError):
            delete_dhcp_reservation(client, "aa:bb:cc:dd:ee:ff", "1.2.3.4", "host")
