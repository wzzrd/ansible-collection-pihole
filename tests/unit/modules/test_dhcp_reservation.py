"""Tests for plugins/modules/dhcp_reservation.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.dhcp_reservation import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.dhcp_reservation"

PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "hw": "00:11:22:33:44:55",
    "ip": "192.168.1.100",
    "name": "laptop.local",
    "state": "present",
}


def _run(params=None, check_mode=False, exists=False):
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

    mock_check = MagicMock(return_value=exists)
    mock_add = MagicMock(return_value={"result": "ok"})
    mock_delete = MagicMock()

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.check_dhcp_reservation_exists", mock_check))
        stack.enter_context(patch(f"{BASE}.add_dhcp_reservation", mock_add))
        stack.enter_context(patch(f"{BASE}.delete_dhcp_reservation", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_delete


class TestDhcpReservationModule:
    def test_present_not_exists_creates(self):
        result, mock_add, _ = _run(exists=False)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_present_already_exists_no_change(self):
        result, mock_add, _ = _run(exists=True)
        assert result.get("changed") is False
        mock_add.assert_not_called()

    def test_absent_exists_deletes(self):
        result, _, mock_delete = _run(params={**PARAMS, "state": "absent"}, exists=True)
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_check_mode_does_not_add(self):
        result, mock_add, _ = _run(exists=False, check_mode=True)
        assert result.get("changed") is True
        mock_add.assert_not_called()

    def test_auth_error_calls_fail_json(self):
        mock_mod = MagicMock()
        mock_mod.params = PARAMS
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
                    f"{BASE}.check_dhcp_reservation_exists",
                    side_effect=PiholeAuthError("x", 401),
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True
