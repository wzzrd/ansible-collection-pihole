"""Tests for plugins/modules/dns_record.py"""

from contextlib import ExitStack
from unittest.mock import ANY, MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.dns_record import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.dns_record"

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "ip": "192.168.1.10",
    "name": "host.local",
    "state": "present",
    "unique": True,
}


def _run(
    params=None,
    check_mode=False,
    raw_records=None,
    parsed_records=None,
    exact_exists=False,
    conflicts=None,
    add_return=None,
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

    mock_get_raw = MagicMock(return_value=raw_records or [])
    mock_parse = MagicMock(
        return_value=parsed_records if parsed_records is not None else []
    )
    mock_check_exists = MagicMock(return_value=exact_exists)
    mock_conflicts = MagicMock(return_value=conflicts if conflicts is not None else [])
    mock_add = MagicMock(return_value=add_return or {"result": "ok"})
    mock_delete = MagicMock()

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.get_static_dns_records", mock_get_raw))
        stack.enter_context(patch(f"{BASE}.parse_dns_records", mock_parse))
        stack.enter_context(
            patch(f"{BASE}.check_static_dns_record_exists", mock_check_exists)
        )
        stack.enter_context(
            patch(f"{BASE}.find_conflicting_dns_records", mock_conflicts)
        )
        stack.enter_context(patch(f"{BASE}.add_static_dns_record", mock_add))
        stack.enter_context(patch(f"{BASE}.delete_static_dns_record", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_delete, mock_conflicts


class TestDnsRecordModulePresent:
    def test_exact_match_no_change(self):
        result, mock_add, _, _ = _run(exact_exists=True, conflicts=[])
        assert result.get("changed") is False
        mock_add.assert_not_called()

    def test_not_exists_adds_record(self):
        result, mock_add, _, _ = _run(exact_exists=False, conflicts=[])
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_conflicts_resolved_before_add(self):
        conflicts = [("192.168.1.99", "host.local")]
        _, mock_add, mock_delete, _ = _run(exact_exists=False, conflicts=conflicts)
        mock_delete.assert_called_once_with(ANY, "192.168.1.99", "host.local")
        mock_add.assert_called_once()

    def test_unique_false_skips_conflict_check(self):
        params = {**BASE_PARAMS, "unique": False}
        _, _, _, mock_conflicts = _run(params=params, exact_exists=False)
        mock_conflicts.assert_not_called()

    def test_check_mode_not_exists_no_add(self):
        result, mock_add, _, _ = _run(exact_exists=False, conflicts=[], check_mode=True)
        assert result.get("changed") is True
        mock_add.assert_not_called()


class TestDnsRecordModuleAbsent:
    def _absent(self, ip="192.168.1.10", name="host.local"):
        return {**BASE_PARAMS, "state": "absent", "ip": ip, "name": name}

    def test_exact_match_deletes(self):
        result, _, mock_delete, _ = _run(
            params=self._absent(),
            parsed_records=[("192.168.1.10", "host.local")],
            exact_exists=True,
        )
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_name_all_deletes_all_for_ip(self):
        parsed = [
            ("192.168.1.10", "host.local"),
            ("192.168.1.10", "alias.local"),
            ("10.0.0.1", "other.local"),
        ]
        result, _, mock_delete, _ = _run(
            params=self._absent(name="all"), parsed_records=parsed, exact_exists=False
        )
        assert result.get("changed") is True
        assert mock_delete.call_count == 2

    def test_both_all_fails(self):
        result, _, _, _ = _run(params=self._absent(ip="all", name="all"))
        assert result.get("_failed") is True

    def test_auth_error_calls_fail_json(self):
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
                    f"{BASE}.get_static_dns_records",
                    side_effect=PiholeAuthError("x", 401),
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True
