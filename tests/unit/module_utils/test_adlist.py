"""Tests for plugins/module_utils/adlist.py"""

import urllib.parse
from unittest.mock import MagicMock

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.adlist import (
    add_adlist,
    delete_adlist,
    get_adlist,
    update_adlist,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeNotFoundError,
    PiholeValidationError,
)

BLOCKLIST_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
ALLOWLIST_URL = "https://raw.githubusercontent.com/example/allowlist/main/list.txt"

ADLIST_RECORD = {
    "address": BLOCKLIST_URL,
    "type": "block",
    "enabled": True,
    "comment": "StevenBlack hosts",
    "groups": [0],
}

ADLISTS_RESPONSE = {"lists": [ADLIST_RECORD]}


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
# get_adlist
# ---------------------------------------------------------------------------


class TestGetAdlist:
    def test_returns_adlist_dict(self):
        client = _mock_client(_make_response(200, ADLISTS_RESPONSE))
        result = get_adlist(client, BLOCKLIST_URL)
        assert result["address"] == BLOCKLIST_URL

    def test_returns_none_on_404_status(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        assert get_adlist(client, "https://example.com/nonexistent.txt") is None

    def test_returns_none_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert get_adlist(client, BLOCKLIST_URL) is None

    def test_returns_none_when_lists_empty(self):
        client = _mock_client(_make_response(200, {"lists": []}))
        assert get_adlist(client, BLOCKLIST_URL) is None

    def test_url_is_percent_encoded_in_endpoint(self):
        client = _mock_client(_make_response(200, ADLISTS_RESPONSE))
        get_adlist(client, BLOCKLIST_URL)
        endpoint = client._request.call_args.args[1]
        encoded = urllib.parse.quote(BLOCKLIST_URL, safe="")
        assert encoded in endpoint

    def test_type_parameter_appended(self):
        client = _mock_client(_make_response(200, ADLISTS_RESPONSE))
        get_adlist(client, BLOCKLIST_URL, list_type="block")
        endpoint = client._request.call_args.args[1]
        assert "?type=block" in endpoint

    def test_allow_list_type(self):
        resp = _make_response(
            200, {"lists": [{"address": ALLOWLIST_URL, "type": "allow"}]}
        )
        client = _mock_client(resp)
        result = get_adlist(client, ALLOWLIST_URL, list_type="allow")
        assert result["type"] == "allow"

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_adlist(client, BLOCKLIST_URL)


# ---------------------------------------------------------------------------
# add_adlist
# ---------------------------------------------------------------------------


class TestAddAdlist:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(201, ADLISTS_RESPONSE))
        result = add_adlist(client, BLOCKLIST_URL)
        assert "lists" in result

    def test_calls_post_to_lists_endpoint(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL)
        assert client._request.call_args.args[0] == "POST"
        assert "api/lists" in client._request.call_args.args[1]

    def test_type_in_query_string(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL, list_type="block")
        endpoint = client._request.call_args.args[1]
        assert "?type=block" in endpoint

    def test_payload_includes_address_type_enabled(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL, list_type="block", enabled=True)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["address"] == BLOCKLIST_URL
        assert payload["type"] == "block"
        assert payload["enabled"] is True

    def test_comment_included_when_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL, comment="My blocklist")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["comment"] == "My blocklist"

    def test_comment_omitted_when_not_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL)
        payload = client._request.call_args.kwargs["json_data"]
        assert "comment" not in payload

    def test_groups_included_when_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL, group_ids=[0, 1])
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["groups"] == [0, 1]

    def test_groups_omitted_when_not_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_adlist(client, BLOCKLIST_URL)
        payload = client._request.call_args.kwargs["json_data"]
        assert "groups" not in payload

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_adlist(client, BLOCKLIST_URL)


# ---------------------------------------------------------------------------
# update_adlist
# ---------------------------------------------------------------------------


class TestUpdateAdlist:
    def _make_update_client(self, get_resp, put_resp):
        c = MagicMock()
        c._request.side_effect = [get_resp, put_resp]
        return c

    def test_raises_validation_error_when_adlist_not_found(self):
        # get_adlist returns None (404)
        resp_404 = _make_response(404)
        resp_404.raise_for_status.side_effect = None
        client = _mock_client(resp_404)
        with pytest.raises(PiholeValidationError) as exc_info:
            update_adlist(client, BLOCKLIST_URL, enabled=False)
        assert "does not exist" in str(exc_info.value)

    def test_preserves_existing_comment_when_none(self):
        get_resp = _make_response(200, ADLISTS_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._make_update_client(get_resp, put_resp)
        update_adlist(client, BLOCKLIST_URL, enabled=False)
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["comment"] == "StevenBlack hosts"

    def test_preserves_existing_groups_when_none(self):
        get_resp = _make_response(200, ADLISTS_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._make_update_client(get_resp, put_resp)
        update_adlist(client, BLOCKLIST_URL, comment="updated")
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["groups"] == [0]

    def test_new_comment_applied(self):
        get_resp = _make_response(200, ADLISTS_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._make_update_client(get_resp, put_resp)
        update_adlist(client, BLOCKLIST_URL, comment="new comment")
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["comment"] == "new comment"

    def test_enabled_false_applied(self):
        get_resp = _make_response(200, ADLISTS_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._make_update_client(get_resp, put_resp)
        update_adlist(client, BLOCKLIST_URL, enabled=False)
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["enabled"] is False

    def test_url_encoded_in_put_endpoint(self):
        get_resp = _make_response(200, ADLISTS_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._make_update_client(get_resp, put_resp)
        update_adlist(client, BLOCKLIST_URL)
        put_endpoint = client._request.call_args_list[1].args[1]
        encoded = urllib.parse.quote(BLOCKLIST_URL, safe="")
        assert encoded in put_endpoint


# ---------------------------------------------------------------------------
# delete_adlist
# ---------------------------------------------------------------------------


class TestDeleteAdlist:
    def test_204_response_returns_success(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        result = delete_adlist(client, BLOCKLIST_URL)
        assert result["success"] is True

    def test_404_status_returns_failure(self):
        resp = _make_response(404, text="not found")
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        result = delete_adlist(client, BLOCKLIST_URL)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_calls_delete_method(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        delete_adlist(client, BLOCKLIST_URL)
        assert client._request.call_args.args[0] == "DELETE"

    def test_url_encoded_in_endpoint(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        delete_adlist(client, BLOCKLIST_URL)
        endpoint = client._request.call_args.args[1]
        encoded = urllib.parse.quote(BLOCKLIST_URL, safe="")
        assert encoded in endpoint

    def test_type_appended_to_endpoint(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        delete_adlist(client, BLOCKLIST_URL, list_type="block")
        endpoint = client._request.call_args.args[1]
        assert "?type=block" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            delete_adlist(client, BLOCKLIST_URL)
