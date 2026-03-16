"""Tests for plugins/modules/batch_delete_groups.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.batch_delete_groups import main

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.batch_delete_groups"

ALL_GROUPS = {"Default": 0, "IoT": 1, "Kids": 2}

PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "names": ["IoT", "Kids"],
}


def _run(params=None, check_mode=False, all_groups=None):
    result = {}

    def fake_exit(**kw):
        result.update(kw)
        raise SystemExit(0)

    def fake_fail(**kw):
        result["_failed"] = True
        result.update(kw)
        raise SystemExit(1)

    mock_mod = MagicMock()
    mock_mod.params = params or PARAMS
    mock_mod.check_mode = check_mode
    mock_mod.exit_json.side_effect = fake_exit
    mock_mod.fail_json.side_effect = fake_fail

    mock_get_groups = MagicMock(return_value=all_groups if all_groups is not None else ALL_GROUPS)
    mock_batch = MagicMock(return_value={"success": True, "status_code": 204})

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.get_groups", mock_get_groups))
        stack.enter_context(patch(f"{BASE}.batch_delete_groups", mock_batch))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_batch


class TestBatchDeleteGroupsModule:
    def test_deletes_existing_groups(self):
        result, mock_batch = _run()
        assert result.get("changed") is True
        mock_batch.assert_called_once()

    def test_only_deletes_groups_that_exist(self):
        params = {**PARAMS, "names": ["IoT", "NonExistent"]}
        _, mock_batch = _run(params=params)
        called_names = mock_batch.call_args.args[1]
        assert "IoT" in called_names
        assert "NonExistent" not in called_names

    def test_partial_match_deleted_count(self):
        params = {**PARAMS, "names": ["IoT", "Ghost"]}
        result, _ = _run(params=params)
        assert result.get("deleted_count") == 1

    def test_check_mode_does_not_call_batch_delete(self):
        result, mock_batch = _run(check_mode=True)
        assert result.get("changed") is True
        mock_batch.assert_not_called()
