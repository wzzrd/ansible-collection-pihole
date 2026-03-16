"""Tests for plugins/modules/client.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.client import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeValidationError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.client"

EXISTING_CLIENT = {"client": "192.168.1.100", "comment": "My PC", "groups": [0]}

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "client": "192.168.1.100",
    "comment": None,
    "groups": ["Default"],
    "state": "present",
}


def _run(params=None, check_mode=False, existing=None, group_ids=None):
    result = {}

    def fake_exit(**kw):
        result.update(kw)
        raise SystemExit(0)

    def fake_fail(**kw):
        result["_failed"] = True
        result.update(kw)
        raise SystemExit(1)

    mock_mod = MagicMock()
    mock_mod.params = params or BASE_PARAMS
    mock_mod.check_mode = check_mode
    mock_mod.exit_json.side_effect = fake_exit
    mock_mod.fail_json.side_effect = fake_fail

    mock_group_ids = MagicMock(return_value=group_ids if group_ids is not None else [0])
    mock_get = MagicMock(return_value=existing)
    mock_add = MagicMock(return_value={"clients": [EXISTING_CLIENT]})
    mock_update = MagicMock(return_value={"clients": [EXISTING_CLIENT]})
    mock_delete = MagicMock(return_value=True)

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.group_names_to_ids", mock_group_ids))
        stack.enter_context(patch(f"{BASE}.get_client", mock_get))
        stack.enter_context(patch(f"{BASE}.add_client", mock_add))
        stack.enter_context(patch(f"{BASE}.update_client", mock_update))
        stack.enter_context(patch(f"{BASE}.delete_client", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_update, mock_delete


class TestClientModulePresent:
    def test_not_exists_creates(self):
        result, mock_add, _, _ = _run(existing=None)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_exists_matching_no_change(self):
        result, _, mock_update, _ = _run(existing=EXISTING_CLIENT, group_ids=[0])
        assert result.get("changed") is False
        mock_update.assert_not_called()

    def test_exists_groups_differ_updates(self):
        result, _, mock_update, _ = _run(existing=EXISTING_CLIENT, group_ids=[0, 1])
        assert result.get("changed") is True
        mock_update.assert_called_once()

    def test_null_comment_from_api_treated_as_empty(self):
        existing = {**EXISTING_CLIENT, "comment": None}
        params = {**BASE_PARAMS, "comment": ""}
        result, _, mock_update, _ = _run(
            existing=existing, params=params, group_ids=[0]
        )
        assert result.get("changed") is False

    def test_invalid_group_fails(self):
        mock_mod = MagicMock()
        mock_mod.params = BASE_PARAMS
        mock_mod.check_mode = False
        result = {}
        mock_mod.fail_json.side_effect = lambda **kw: (
            result.update({"_failed": True, **kw})
        ) or (_ for _ in ()).throw(SystemExit(1))
        mock_mod.exit_json.side_effect = lambda **kw: (_ for _ in ()).throw(
            SystemExit(0)
        )

        with patch(f"{BASE}.AnsibleModule", return_value=mock_mod):
            with patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()):
                with patch(
                    f"{BASE}.group_names_to_ids",
                    side_effect=PiholeValidationError("group not found"),
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True


class TestClientModuleAbsent:
    def test_exists_deletes(self):
        result, _, _, mock_delete = _run(
            existing=EXISTING_CLIENT, params={**BASE_PARAMS, "state": "absent"}
        )
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_not_exists_no_change(self):
        result, _, _, mock_delete = _run(
            existing=None, params={**BASE_PARAMS, "state": "absent"}
        )
        assert result.get("changed") is False
        mock_delete.assert_not_called()
