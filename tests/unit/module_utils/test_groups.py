"""Tests for plugins/module_utils/groups.py"""

from unittest.mock import MagicMock, call, patch

import pytest
import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeNotFoundError,
    PiholeValidationError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.groups import (
    add_group,
    batch_delete_groups,
    delete_group,
    get_group,
    get_groups,
    group_names_to_ids,
    update_group,
)


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


GROUPS_RESPONSE = {
    "groups": [
        {"id": 0, "name": "Default", "comment": "Default group", "enabled": True},
        {"id": 1, "name": "IoT", "comment": "IoT devices", "enabled": True},
        {"id": 2, "name": "Kids", "comment": "Kids devices", "enabled": False},
    ]
}

SINGLE_GROUP_RESPONSE = {
    "groups": [
        {"id": 1, "name": "IoT", "comment": "IoT devices", "enabled": True}
    ]
}


# ---------------------------------------------------------------------------
# get_groups
# ---------------------------------------------------------------------------

class TestGetGroups:
    def test_returns_name_to_id_mapping(self):
        client = _mock_client(_make_response(200, GROUPS_RESPONSE))
        result = get_groups(client)
        assert result == {"Default": 0, "IoT": 1, "Kids": 2}

    def test_empty_groups_returns_empty_dict(self):
        client = _mock_client(_make_response(200, {"groups": []}))
        assert get_groups(client) == {}

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, GROUPS_RESPONSE))
        get_groups(client)
        client._request.assert_called_once_with("GET", "api/groups")

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_groups(client)

    def test_unexpected_error_wrapped(self):
        client = _mock_client()
        client._request.side_effect = RuntimeError("crash")
        with pytest.raises(PiholeApiError):
            get_groups(client)


# ---------------------------------------------------------------------------
# get_group
# ---------------------------------------------------------------------------

class TestGetGroup:
    def test_returns_group_dict_when_found(self):
        client = _mock_client(_make_response(200, SINGLE_GROUP_RESPONSE))
        result = get_group(client, "IoT")
        assert result["name"] == "IoT"
        assert result["id"] == 1

    def test_returns_none_when_status_404(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        assert get_group(client, "nonexistent") is None

    def test_returns_none_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert get_group(client, "ghost") is None

    def test_returns_none_when_groups_list_empty(self):
        client = _mock_client(_make_response(200, {"groups": []}))
        assert get_group(client, "anything") is None

    def test_calls_correct_endpoint(self):
        client = _mock_client(_make_response(200, SINGLE_GROUP_RESPONSE))
        get_group(client, "IoT")
        client._request.assert_called_once_with("GET", "api/groups/IoT")

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_group(client, "IoT")


# ---------------------------------------------------------------------------
# add_group
# ---------------------------------------------------------------------------

class TestAddGroup:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(201, {"groups": [{"id": 3, "name": "New"}]}))
        result = add_group(client, "New")
        assert "groups" in result

    def test_calls_post_to_api_groups(self):
        client = _mock_client(_make_response(201, {}))
        add_group(client, "New", comment="A new group", enabled=True)
        client._request.assert_called_once_with(
            "POST",
            "api/groups",
            json_data={"name": "New", "comment": "A new group", "enabled": True},
        )

    def test_default_comment_is_empty_string(self):
        client = _mock_client(_make_response(201, {}))
        add_group(client, "New")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["comment"] == ""

    def test_default_enabled_is_true(self):
        client = _mock_client(_make_response(201, {}))
        add_group(client, "New")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["enabled"] is True

    def test_disabled_group(self):
        client = _mock_client(_make_response(201, {}))
        add_group(client, "Disabled", enabled=False)
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["enabled"] is False

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_group(client, "New")


# ---------------------------------------------------------------------------
# update_group
# ---------------------------------------------------------------------------

class TestUpdateGroup:
    def _client_with_get_then_put(self, get_resp, put_resp):
        """Return a mock client where first call is GET (get_group) and second is PUT."""
        c = MagicMock()
        c._request.side_effect = [get_resp, put_resp]
        return c

    def test_raises_validation_error_when_group_not_found(self):
        # get_group returns None (404 response)
        resp_404 = _make_response(404)
        resp_404.raise_for_status.side_effect = None
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        with pytest.raises(PiholeValidationError) as exc_info:
            update_group(client, "nonexistent")
        assert "does not exist" in str(exc_info.value)

    def test_preserves_existing_comment_when_not_provided(self):
        get_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        put_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        client = self._client_with_get_then_put(get_resp, put_resp)
        update_group(client, "IoT", enabled=False)
        put_call = client._request.call_args_list[1]
        payload = put_call.kwargs["json_data"]
        assert payload["comment"] == "IoT devices"

    def test_preserves_existing_enabled_when_not_provided(self):
        get_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        put_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        client = self._client_with_get_then_put(get_resp, put_resp)
        update_group(client, "IoT", comment="new comment")
        put_call = client._request.call_args_list[1]
        payload = put_call.kwargs["json_data"]
        assert payload["enabled"] is True

    def test_new_name_included_when_provided(self):
        get_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_with_get_then_put(get_resp, put_resp)
        update_group(client, "IoT", new_name="IoT_Devices")
        put_call = client._request.call_args_list[1]
        payload = put_call.kwargs["json_data"]
        assert payload["name"] == "IoT_Devices"

    def test_new_name_not_included_when_not_provided(self):
        get_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_with_get_then_put(get_resp, put_resp)
        update_group(client, "IoT", comment="updated")
        put_call = client._request.call_args_list[1]
        payload = put_call.kwargs["json_data"]
        assert "name" not in payload

    def test_put_calls_correct_endpoint(self):
        get_resp = _make_response(200, SINGLE_GROUP_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_with_get_then_put(get_resp, put_resp)
        update_group(client, "IoT", comment="updated")
        put_call = client._request.call_args_list[1]
        assert put_call.args[0] == "PUT"
        assert "api/groups/IoT" in put_call.args[1]


# ---------------------------------------------------------------------------
# delete_group
# ---------------------------------------------------------------------------

class TestDeleteGroup:
    def test_204_response_returns_success_dict(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        result = delete_group(client, "IoT")
        assert result["success"] is True

    def test_calls_delete_endpoint(self):
        resp = _make_response(204, text="")
        resp.text = ""
        client = _mock_client(resp)
        delete_group(client, "IoT")
        client._request.assert_called_once_with("DELETE", "api/groups/IoT")

    def test_not_found_error_re_raised(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        with pytest.raises(PiholeNotFoundError):
            delete_group(client, "ghost")

    def test_json_response_returned_when_available(self):
        resp = _make_response(200, {"message": "deleted"}, text='{"message":"deleted"}')
        resp.text = '{"message":"deleted"}'
        client = _mock_client(resp)
        result = delete_group(client, "IoT")
        assert result == {"message": "deleted"}


# ---------------------------------------------------------------------------
# batch_delete_groups
# ---------------------------------------------------------------------------

class TestBatchDeleteGroups:
    def test_empty_list_returns_immediately(self):
        client = MagicMock()
        result = batch_delete_groups(client, [])
        assert result["success"] is True
        client._request.assert_not_called()

    def test_204_success(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        result = batch_delete_groups(client, ["IoT", "Kids"])
        assert result["success"] is True
        assert result["status_code"] == 204

    def test_formatted_payload(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        batch_delete_groups(client, ["IoT", "Kids"])
        payload = client._request.call_args.kwargs["json_data"]
        assert {"item": "IoT"} in payload
        assert {"item": "Kids"} in payload

    def test_calls_batch_delete_endpoint(self):
        resp = _make_response(204)
        client = _mock_client(resp)
        batch_delete_groups(client, ["IoT"])
        endpoint = client._request.call_args.args[1]
        assert "batchDelete" in endpoint

    def test_400_raises_api_error(self):
        resp = _make_response(400, text="bad request")
        client = _mock_client(resp)
        with pytest.raises(PiholeApiError):
            batch_delete_groups(client, ["IoT"])

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            batch_delete_groups(client, ["IoT"])


# ---------------------------------------------------------------------------
# group_names_to_ids
# ---------------------------------------------------------------------------

class TestGroupNamesToIds:
    def setup_method(self):
        self.client = _mock_client(_make_response(200, GROUPS_RESPONSE))

    def test_empty_list_returns_default_group_zero(self):
        client = MagicMock()  # should not be called
        result = group_names_to_ids(client, [])
        assert result == [0]
        client._request.assert_not_called()

    def test_single_group_name_resolved(self):
        result = group_names_to_ids(self.client, ["IoT"])
        assert result == [1]

    def test_multiple_group_names_resolved(self):
        result = group_names_to_ids(self.client, ["Default", "IoT", "Kids"])
        assert result == [0, 1, 2]

    def test_duplicates_removed(self):
        result = group_names_to_ids(self.client, ["IoT", "IoT", "Default"])
        # Should have unique IDs only, preserving first-seen order
        assert result == [1, 0]

    def test_missing_group_raises_validation_error(self):
        with pytest.raises(PiholeValidationError) as exc_info:
            group_names_to_ids(self.client, ["NonExistent"])
        assert "NonExistent" in str(exc_info.value)

    def test_partial_missing_groups_raises_validation_error(self):
        with pytest.raises(PiholeValidationError) as exc_info:
            group_names_to_ids(self.client, ["IoT", "Ghost"])
        assert "Ghost" in str(exc_info.value)

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            group_names_to_ids(client, ["IoT"])
