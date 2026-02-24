"""Tests for plugins/module_utils/client.py"""

import urllib.parse
from unittest.mock import MagicMock

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeNotFoundError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.client import (
    add_client,
    delete_client,
    get_client,
    update_client,
)

CLIENT_RECORD = {
    "client": "192.168.88.20",
    "comment": "workstation",
    "groups": [0, 1],
}

CLIENTS_RESPONSE = {"clients": [CLIENT_RECORD]}


def _make_response(status_code=200, json_data=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
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


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_returns_client_dict(self):
        client = _mock_client(_make_response(200, CLIENTS_RESPONSE))
        result = get_client(client, "192.168.88.20")
        assert result["client"] == "192.168.88.20"

    def test_returns_none_on_404_status(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        assert get_client(client, "10.0.0.1") is None

    def test_returns_none_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert get_client(client, "10.0.0.1") is None

    def test_returns_none_when_clients_list_empty(self):
        client = _mock_client(_make_response(200, {"clients": []}))
        assert get_client(client, "10.0.0.1") is None

    def test_client_id_url_encoded_in_endpoint(self):
        client = _mock_client(_make_response(200, CLIENTS_RESPONSE))
        get_client(client, "192.168.88.20")
        endpoint = client._request.call_args.args[1]
        assert urllib.parse.quote("192.168.88.20") in endpoint

    def test_cidr_encoded_in_endpoint(self):
        resp = _make_response(200, {"clients": [{"client": "192.168.88.0/24"}]})
        client = _mock_client(resp)
        get_client(client, "192.168.88.0/24")
        endpoint = client._request.call_args.args[1]
        assert urllib.parse.quote("192.168.88.0/24") in endpoint

    def test_mac_address_encoded(self):
        resp = _make_response(200, {"clients": [{"client": "de:ad:be:ef:00:01"}]})
        client = _mock_client(resp)
        get_client(client, "de:ad:be:ef:00:01")
        endpoint = client._request.call_args.args[1]
        assert "de%3Aad%3Abe%3Aef%3A00%3A01" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_client(client, "192.168.88.20")


# ---------------------------------------------------------------------------
# add_client
# ---------------------------------------------------------------------------


class TestAddClient:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(201, CLIENTS_RESPONSE))
        result = add_client(client, "192.168.88.20")
        assert "clients" in result

    def test_calls_post_to_api_clients(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20")
        assert client._request.call_args.args[0] == "POST"
        assert client._request.call_args.args[1] == "api/clients"

    def test_payload_includes_client_id(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["client"] == "192.168.88.20"

    def test_comment_included_when_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20", comment="workstation")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["comment"] == "workstation"

    def test_comment_omitted_when_not_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20")
        payload = client._request.call_args.kwargs["json_data"]
        assert "comment" not in payload

    def test_group_ids_included(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20", group_ids=[0, 1])
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["groups"] == [0, 1]

    def test_default_group_used_when_group_ids_none(self):
        client = _mock_client(_make_response(201, {}))
        add_client(client, "192.168.88.20", group_ids=None)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["groups"] == [0]

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_client(client, "192.168.88.20")


# ---------------------------------------------------------------------------
# update_client
# ---------------------------------------------------------------------------


class TestUpdateClient:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(200, CLIENTS_RESPONSE))
        result = update_client(client, "192.168.88.20", group_ids=[0])
        assert "clients" in result

    def test_calls_put_to_encoded_endpoint(self):
        client = _mock_client(_make_response(200, {}))
        update_client(client, "192.168.88.20", group_ids=[0])
        call_args = client._request.call_args
        assert call_args.args[0] == "PUT"
        encoded = urllib.parse.quote("192.168.88.20")
        assert encoded in call_args.args[1]

    def test_comment_included_when_provided(self):
        client = _mock_client(_make_response(200, {}))
        update_client(client, "192.168.88.20", comment="updated", group_ids=[0])
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["comment"] == "updated"

    def test_comment_omitted_when_none(self):
        client = _mock_client(_make_response(200, {}))
        update_client(client, "192.168.88.20", comment=None, group_ids=[0])
        payload = client._request.call_args.kwargs["json_data"]
        assert "comment" not in payload

    def test_groups_included_when_provided(self):
        client = _mock_client(_make_response(200, {}))
        update_client(client, "192.168.88.20", group_ids=[1, 2])
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["groups"] == [1, 2]

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            update_client(client, "192.168.88.20", group_ids=[0])


# ---------------------------------------------------------------------------
# delete_client
# ---------------------------------------------------------------------------


class TestDeleteClient:
    def test_returns_true_on_success(self):
        client = _mock_client(_make_response(204))
        assert delete_client(client, "192.168.88.20") is True

    def test_returns_false_on_404_status(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        assert delete_client(client, "10.0.0.1") is False

    def test_returns_false_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert delete_client(client, "10.0.0.1") is False

    def test_calls_delete_method(self):
        client = _mock_client(_make_response(204))
        delete_client(client, "192.168.88.20")
        assert client._request.call_args.args[0] == "DELETE"

    def test_client_id_encoded_in_endpoint(self):
        client = _mock_client(_make_response(204))
        delete_client(client, "192.168.88.20")
        endpoint = client._request.call_args.args[1]
        assert urllib.parse.quote("192.168.88.20") in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            delete_client(client, "192.168.88.20")

    def test_unexpected_error_wrapped(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            delete_client(client, "192.168.88.20")
