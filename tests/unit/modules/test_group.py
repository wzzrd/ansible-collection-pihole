"""Tests for plugins/modules/group.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.group import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import PiholeAuthError

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.group"

EXISTING_GROUP = {"id": 1, "name": "IoT", "comment": "IoT devices", "enabled": True}

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "name": "IoT",
    "new_name": None,
    "comment": None,
    "enabled": None,
    "state": "present",
}


def _run(params=None, check_mode=False, existing=None):
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

    mock_get = MagicMock(return_value=existing)
    mock_add = MagicMock(return_value={"groups": [{"id": 2, "name": "New"}]})
    mock_update = MagicMock(return_value={"groups": [EXISTING_GROUP]})
    mock_delete = MagicMock(return_value={"success": True, "message": "deleted"})

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.get_group", mock_get))
        stack.enter_context(patch(f"{BASE}.add_group", mock_add))
        stack.enter_context(patch(f"{BASE}.update_group", mock_update))
        stack.enter_context(patch(f"{BASE}.delete_group", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_update, mock_delete


class TestGroupModulePresent:
    def test_not_exists_creates_group(self):
        result, mock_add, _, _ = _run(existing=None)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_exists_no_changes_no_update(self):
        result, _, mock_update, _ = _run(existing=EXISTING_GROUP)
        assert result.get("changed") is False
        mock_update.assert_not_called()

    def test_exists_new_name_updates(self):
        params = {**BASE_PARAMS, "new_name": "IoT_Renamed"}
        result, _, mock_update, _ = _run(existing=EXISTING_GROUP, params=params)
        assert result.get("changed") is True
        mock_update.assert_called_once()

    def test_exists_check_mode_needs_update_no_call(self):
        params = {**BASE_PARAMS, "comment": "changed"}
        result, _, mock_update, _ = _run(existing=EXISTING_GROUP, params=params,
                                         check_mode=True)
        assert result.get("changed") is True
        mock_update.assert_not_called()


class TestGroupModuleAbsent:
    def test_exists_deletes(self):
        result, _, _, mock_delete = _run(
            existing=EXISTING_GROUP, params={**BASE_PARAMS, "state": "absent"}
        )
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_auth_error_calls_fail_json(self):
        mock_mod = MagicMock()
        mock_mod.params = BASE_PARAMS
        mock_mod.check_mode = False
        result = {}
        mock_mod.fail_json.side_effect = lambda **kw: (result.update({"_failed": True, **kw})) or (_ for _ in ()).throw(SystemExit(1))
        mock_mod.exit_json.side_effect = lambda **kw: (_ for _ in ()).throw(SystemExit(0))

        with patch(f"{BASE}.AnsibleModule", return_value=mock_mod):
            with patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()):
                with patch(f"{BASE}.get_group", side_effect=PiholeAuthError("x", 401)):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True
