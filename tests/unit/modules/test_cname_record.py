"""Tests for plugins/modules/cname_record.py"""

from contextlib import ExitStack
from unittest.mock import ANY, MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.cname_record import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import PiholeAuthError

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.cname_record"

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "cname": "alias.local",
    "name": "target.local",
    "state": "present",
    "unique": True,
}


def _run(params=None, check_mode=False, raw_records=None, exact_exists=False):
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

    mock_get_raw = MagicMock(return_value=raw_records or [])
    mock_check = MagicMock(return_value=exact_exists)
    mock_add = MagicMock(return_value={"result": "ok"})
    mock_delete = MagicMock()

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.get_cname_records", mock_get_raw))
        stack.enter_context(patch(f"{BASE}.check_cname_record_exists", mock_check))
        stack.enter_context(patch(f"{BASE}.add_cname_record", mock_add))
        stack.enter_context(patch(f"{BASE}.delete_cname_record", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_delete


class TestCnameRecordModulePresent:
    def test_not_exists_adds_record(self):
        result, mock_add, _ = _run(exact_exists=False)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_conflict_same_alias_different_target_removed(self):
        raw = ["alias.local,old_target.local"]
        result, mock_add, mock_delete = _run(raw_records=raw, exact_exists=False)
        mock_delete.assert_called_once_with(ANY, "alias.local", "old_target.local")
        assert result.get("changed") is True

    def test_unique_false_no_conflict_check(self):
        params = {**BASE_PARAMS, "unique": False}
        raw = ["alias.local,old_target.local"]
        _, _, mock_delete = _run(params=params, raw_records=raw, exact_exists=False)
        mock_delete.assert_not_called()

    def test_check_mode_no_add(self):
        result, mock_add, _ = _run(exact_exists=False, check_mode=True)
        assert result.get("changed") is True
        mock_add.assert_not_called()


class TestCnameRecordModuleAbsent:
    def _absent(self, cname="alias.local", name="target.local"):
        return {**BASE_PARAMS, "state": "absent", "cname": cname, "name": name}

    def test_cname_all_deletes_all_pointing_to_target(self):
        raw = ["a.local,target.local", "b.local,target.local", "c.local,other.local"]
        result, _, mock_delete = _run(
            params=self._absent(cname="all"), raw_records=raw, exact_exists=False
        )
        assert result.get("changed") is True
        assert mock_delete.call_count == 2

    def test_both_all_fails(self):
        result, _, _ = _run(params=self._absent(cname="all", name="all"))
        assert result.get("_failed") is True

    def test_auth_error_calls_fail_json(self):
        mock_mod = MagicMock()
        mock_mod.params = BASE_PARAMS
        mock_mod.check_mode = False
        result = {}
        mock_mod.fail_json.side_effect = lambda **kw: (result.update({"_failed": True, **kw})) or (_ for _ in ()).throw(SystemExit(1))
        mock_mod.exit_json.side_effect = lambda **kw: (_ for _ in ()).throw(SystemExit(0))

        with patch(f"{BASE}.AnsibleModule", return_value=mock_mod):
            with patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()):
                with patch(f"{BASE}.get_cname_records",
                           side_effect=PiholeAuthError("x", 401)):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True
