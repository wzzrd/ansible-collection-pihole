"""Tests for plugins/module_utils/domain.py"""

import urllib.parse
from unittest.mock import MagicMock

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeNotFoundError,
    PiholeValidationError,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.domain import (
    add_domain,
    delete_domain,
    get_domain,
    update_domain,
)
from .helpers import make_response as _make_response, mock_client as _mock_client

DOMAIN_RECORD = {
    "domain": "ads.example.com",
    "type": "deny",
    "kind": "exact",
    "enabled": True,
    "comment": "Known ad server",
    "groups": [0],
}

DOMAIN_RESPONSE = {"domains": [DOMAIN_RECORD]}


# ---------------------------------------------------------------------------
# get_domain
# ---------------------------------------------------------------------------


class TestGetDomain:
    def test_returns_domain_and_location(self):
        client = _mock_client(_make_response(200, DOMAIN_RESPONSE))
        domain_info, location = get_domain(client, "ads.example.com")
        assert domain_info["domain"] == "ads.example.com"
        assert location == ("deny", "exact")

    def test_returns_none_tuple_on_404_status(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        result = get_domain(client, "ghost.example.com")
        assert result == (None, None)

    def test_returns_none_tuple_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert get_domain(client, "ghost.example.com") == (None, None)

    def test_returns_none_tuple_when_domains_list_empty(self):
        client = _mock_client(_make_response(200, {"domains": []}))
        assert get_domain(client, "empty.example.com") == (None, None)

    def test_domain_url_encoded_in_endpoint(self):
        client = _mock_client(_make_response(200, DOMAIN_RESPONSE))
        domain = "ads.example.com"
        get_domain(client, domain)
        endpoint = client._request.call_args.args[1]
        assert urllib.parse.quote(domain) in endpoint

    def test_endpoint_with_type_and_kind(self):
        client = _mock_client(_make_response(200, DOMAIN_RESPONSE))
        get_domain(client, "ads.example.com", domain_type="deny", domain_kind="exact")
        endpoint = client._request.call_args.args[1]
        assert "deny/exact" in endpoint

    def test_endpoint_with_only_type(self):
        client = _mock_client(_make_response(200, DOMAIN_RESPONSE))
        get_domain(client, "ads.example.com", domain_type="deny")
        endpoint = client._request.call_args.args[1]
        assert "deny" in endpoint

    def test_endpoint_without_type_or_kind(self):
        client = _mock_client(_make_response(200, DOMAIN_RESPONSE))
        get_domain(client, "ads.example.com")
        endpoint = client._request.call_args.args[1]
        # Should not have deny/exact in path
        assert "deny/exact" not in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            get_domain(client, "ads.example.com")


# ---------------------------------------------------------------------------
# add_domain
# ---------------------------------------------------------------------------


class TestAddDomain:
    def test_returns_api_response(self):
        client = _mock_client(_make_response(201, DOMAIN_RESPONSE))
        result = add_domain(client, "ads.example.com", "deny", "exact")
        assert "domains" in result

    def test_calls_post_with_type_kind_in_path(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "ads.example.com", "deny", "exact")
        endpoint = client._request.call_args.args[1]
        assert "deny/exact" in endpoint
        assert client._request.call_args.args[0] == "POST"

    def test_payload_includes_domain_and_enabled(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "ads.example.com", "deny", "exact")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["domain"] == "ads.example.com"
        assert payload["enabled"] is True

    def test_comment_included_when_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "ads.example.com", "deny", "exact", comment="ad server")
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["comment"] == "ad server"

    def test_comment_omitted_when_not_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "ads.example.com", "deny", "exact")
        payload = client._request.call_args.kwargs["json_data"]
        assert "comment" not in payload

    def test_groups_included_when_provided(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "ads.example.com", "deny", "exact", group_ids=[0, 1])
        payload = client._request.call_args.kwargs["json_data"]
        assert payload["groups"] == [0, 1]

    def test_regex_domain_type(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, r"^ads\.", "deny", "regex")
        endpoint = client._request.call_args.args[1]
        assert "deny/regex" in endpoint

    def test_allow_domain_type(self):
        client = _mock_client(_make_response(201, {}))
        add_domain(client, "trusted.example.com", "allow", "exact")
        endpoint = client._request.call_args.args[1]
        assert "allow/exact" in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            add_domain(client, "ads.example.com", "deny", "exact")


# ---------------------------------------------------------------------------
# update_domain
# ---------------------------------------------------------------------------


class TestUpdateDomain:
    def _client_two_calls(self, get_resp, put_resp):
        c = MagicMock()
        c._request.side_effect = [get_resp, put_resp]
        return c

    def test_raises_validation_error_when_domain_not_found(self):
        resp_404 = _make_response(404)
        resp_404.raise_for_status.side_effect = None
        client = _mock_client(resp_404)
        with pytest.raises(PiholeValidationError) as exc_info:
            update_domain(
                client,
                "ghost.example.com",
                current_type="deny",
                current_kind="exact",
                target_type="deny",
                target_kind="exact",
            )
        assert "does not exist" in str(exc_info.value)

    def test_preserves_existing_comment(self):
        get_resp = _make_response(200, DOMAIN_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_two_calls(get_resp, put_resp)
        update_domain(
            client,
            "ads.example.com",
            current_type="deny",
            current_kind="exact",
            target_type="deny",
            target_kind="exact",
            enabled=False,
        )
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["comment"] == "Known ad server"

    def test_preserves_existing_enabled_when_none(self):
        get_resp = _make_response(200, DOMAIN_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_two_calls(get_resp, put_resp)
        update_domain(
            client,
            "ads.example.com",
            current_type="deny",
            current_kind="exact",
            target_type="deny",
            target_kind="exact",
        )
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["enabled"] is True

    def test_moving_between_lists_includes_current_type_kind_in_payload(self):
        get_resp = _make_response(200, DOMAIN_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_two_calls(get_resp, put_resp)
        update_domain(
            client,
            "ads.example.com",
            current_type="deny",
            current_kind="exact",
            target_type="allow",
            target_kind="exact",
        )
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert put_payload["type"] == "deny"
        assert put_payload["kind"] == "exact"

    def test_same_list_update_omits_type_kind_from_payload(self):
        get_resp = _make_response(200, DOMAIN_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_two_calls(get_resp, put_resp)
        update_domain(
            client,
            "ads.example.com",
            current_type="deny",
            current_kind="exact",
            target_type="deny",
            target_kind="exact",
            comment="updated comment",
        )
        put_payload = client._request.call_args_list[1].kwargs["json_data"]
        assert "type" not in put_payload
        assert "kind" not in put_payload

    def test_target_type_kind_used_in_put_url(self):
        get_resp = _make_response(200, DOMAIN_RESPONSE)
        put_resp = _make_response(200, {})
        client = self._client_two_calls(get_resp, put_resp)
        update_domain(
            client,
            "ads.example.com",
            current_type="deny",
            current_kind="exact",
            target_type="allow",
            target_kind="exact",
        )
        put_endpoint = client._request.call_args_list[1].args[1]
        assert "allow/exact" in put_endpoint


# ---------------------------------------------------------------------------
# delete_domain
# ---------------------------------------------------------------------------


class TestDeleteDomain:
    def test_returns_true_on_success(self):
        client = _mock_client(_make_response(204))
        result = delete_domain(client, "ads.example.com", "deny", "exact")
        assert result is True

    def test_returns_false_on_404_status(self):
        resp = _make_response(404)
        resp.raise_for_status.side_effect = None
        client = _mock_client(resp)
        result = delete_domain(client, "ghost.example.com", "deny", "exact")
        assert result is False

    def test_returns_false_on_not_found_error(self):
        client = _mock_client(side_effect=PiholeNotFoundError("nope", 404))
        assert delete_domain(client, "ghost.example.com", "deny", "exact") is False

    def test_calls_delete_method(self):
        client = _mock_client(_make_response(204))
        delete_domain(client, "ads.example.com", "deny", "exact")
        assert client._request.call_args.args[0] == "DELETE"

    def test_endpoint_contains_type_kind_and_encoded_domain(self):
        client = _mock_client(_make_response(204))
        domain = "ads.example.com"
        delete_domain(client, domain, "deny", "exact")
        endpoint = client._request.call_args.args[1]
        assert "deny/exact" in endpoint
        assert urllib.parse.quote(domain) in endpoint

    def test_auth_error_propagates(self):
        client = _mock_client(side_effect=PiholeAuthError("unauth", 401))
        with pytest.raises(PiholeAuthError):
            delete_domain(client, "ads.example.com", "deny", "exact")
