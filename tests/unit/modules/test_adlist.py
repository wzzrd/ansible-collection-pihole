"""Tests for plugins/modules/adlist.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.adlist import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeValidationError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.adlist"

URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

EXISTING_ADLIST = {
    "address": URL,
    "type": "block",
    "comment": "StevenBlack",
    "enabled": True,
    "groups": [0],
}

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "address": URL,
    "type": "block",
    "comment": None,
    "groups": ["Default"],
    "enabled": True,
    "state": "present",
}


def _run(
    params=None, check_mode=False, existing=None, group_ids=None, delete_return=None
):
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
    mock_add = MagicMock(return_value={"lists": [EXISTING_ADLIST]})
    mock_update = MagicMock(return_value={"lists": [EXISTING_ADLIST]})
    mock_delete = MagicMock(
        return_value=delete_return or {"success": True, "message": "deleted"}
    )

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.group_names_to_ids", mock_group_ids))
        stack.enter_context(patch(f"{BASE}.get_adlist", mock_get))
        stack.enter_context(patch(f"{BASE}.add_adlist", mock_add))
        stack.enter_context(patch(f"{BASE}.update_adlist", mock_update))
        stack.enter_context(patch(f"{BASE}.delete_adlist", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_update, mock_delete


class TestAdlistModulePresent:
    def test_not_exists_creates(self):
        result, mock_add, _, _ = _run(existing=None)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_exists_no_changes_no_update(self):
        result, _, mock_update, _ = _run(existing=EXISTING_ADLIST, group_ids=[0])
        assert result.get("changed") is False
        mock_update.assert_not_called()

    def test_exists_enabled_changed_updates(self):
        params = {**BASE_PARAMS, "enabled": False}
        result, _, mock_update, _ = _run(
            existing=EXISTING_ADLIST, params=params, group_ids=[0]
        )
        assert result.get("changed") is True
        mock_update.assert_called_once()

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


class TestAdlistModuleAbsent:
    def test_exists_deletes(self):
        result, _, _, mock_delete = _run(
            existing=EXISTING_ADLIST, params={**BASE_PARAMS, "state": "absent"}
        )
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_delete_not_found_no_change(self):
        result, _, _, _ = _run(
            existing=EXISTING_ADLIST,
            params={**BASE_PARAMS, "state": "absent"},
            delete_return={"success": False, "message": "Adlist not found"},
        )
        assert result.get("changed") is False
