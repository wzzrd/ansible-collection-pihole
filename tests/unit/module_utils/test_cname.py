"""Tests for plugins/module_utils/cname.py"""

from unittest.mock import MagicMock

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.cname import (
    add_cname_record,
    check_cname_record_exists,
    delete_cname_record,
    get_cname_records,
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


CNAME_RESPONSE = {
    "config": {
        "dns": {
            "cnameRecords": [
                "www.acme.lab,nas01.acme.lab",
                "files.acme.lab,nas01.acme.lab",
                "cam.acme.lab,rpi-cam.acme.lab",
            ]
        }
    }
}


class TestGetCnameRecords:
    def test_returns_list_of_strings(self):
        client = _mock_client(_make_response(200, CNAME_RESPONSE))
        records = get_cname_records(client)
        assert len(records) == 3

    def test_correct_format(self):
        client = _mock_client(_make_response(200, CNAME_RESPONSE))
        records = get_cname_records(client)
        assert "www.acme.lab,nas01.acme.lab" in records

    def test_empty_returns_empty_list(self):
        resp = _make_response(200, {"config": {"dns": {"cnameRecords": []}}})
        client = _mock_client(resp)
        assert get_cname_records(client) == []

    def test_missing_keys_returns_empty_list(self):
        client = _mock_client(_make_response(200, {}))
        assert get_cname_records(client) == []

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, CNAME_RESPONSE))
        get_cname_records(client)
        client._request.assert_called_once_with("GET", "api/config/dns/cnameRecords")

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_cname_records(client)


class TestCheckCnameRecordExists:
    def setup_method(self):
        self.client = _mock_client(_make_response(200, CNAME_RESPONSE))

    def test_existing_record_returns_true(self):
        assert check_cname_record_exists(
            self.client, "www.acme.lab", "nas01.acme.lab"
        ) is True

    def test_missing_cname_returns_false(self):
        assert check_cname_record_exists(
            self.client, "blog.acme.lab", "nas01.acme.lab"
        ) is False

    def test_wrong_target_returns_false(self):
        assert check_cname_record_exists(
            self.client, "www.acme.lab", "other.acme.lab"
        ) is False

    def test_reversed_order_returns_false(self):
        # "nas01.acme.lab,www.acme.lab" is not in the list
        assert check_cname_record_exists(
            self.client, "nas01.acme.lab", "www.acme.lab"
        ) is False


class TestAddCnameRecord:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(200, {"result": "ok"}))
        result = add_cname_record(client, "blog.acme.lab", "nas01.acme.lab")
        assert result == {"result": "ok"}

    def test_calls_put_method(self):
        client = _mock_client(_make_response(200, {}))
        add_cname_record(client, "blog.acme.lab", "nas01.acme.lab")
        assert client._request.call_args.args[0] == "PUT"

    def test_endpoint_contains_comma_separated_pair(self):
        client = _mock_client(_make_response(200, {}))
        add_cname_record(client, "blog.acme.lab", "nas01.acme.lab")
        endpoint = client._request.call_args.args[1]
        assert "blog.acme.lab,nas01.acme.lab" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_cname_record(client, "alias", "target")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            add_cname_record(client, "alias", "target")


class TestDeleteCnameRecord:
    def test_successful_delete_returns_none(self):
        client = _mock_client(_make_response(204))
        result = delete_cname_record(client, "www.acme.lab", "nas01.acme.lab")
        assert result is None

    def test_calls_delete_method(self):
        client = _mock_client(_make_response(204))
        delete_cname_record(client, "www.acme.lab", "nas01.acme.lab")
        assert client._request.call_args.args[0] == "DELETE"

    def test_endpoint_contains_comma_separated_pair(self):
        client = _mock_client(_make_response(204))
        delete_cname_record(client, "www.acme.lab", "nas01.acme.lab")
        endpoint = client._request.call_args.args[1]
        assert "www.acme.lab,nas01.acme.lab" in endpoint

    def test_connection_error_propagates(self):
        client = _mock_client(side_effect=PiholeConnectionError("down"))
        with pytest.raises(PiholeConnectionError):
            delete_cname_record(client, "alias", "target")

    def test_unexpected_error_wrapped_as_api_error(self):
        client = _mock_client()
        client._request.side_effect = ValueError("bad")
        with pytest.raises(PiholeApiError):
            delete_cname_record(client, "alias", "target")
