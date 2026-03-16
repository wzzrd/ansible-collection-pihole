"""Tests for plugins/modules/action.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.action import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.action"

PARAMS = {"pihole": "https://pihole.local", "sid": "sid123", "action": "restartdns"}


def _run(params=None, check_mode=False, **mocks):
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

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        for name, val in mocks.items():
            stack.enter_context(patch(f"{BASE}.{name}", val))
        try:
            main()
        except SystemExit:
            pass

    return result


class TestActionModule:
    def test_success_changed_true(self):
        result = _run(perform_action=MagicMock(return_value={"success": True}))
        assert result.get("changed") is True

    def test_check_mode_does_not_call_perform_action(self):
        mock_perform = MagicMock(return_value={})
        result = _run(check_mode=True, perform_action=mock_perform)
        assert result.get("changed") is True
        mock_perform.assert_not_called()

    def test_auth_error_calls_fail_json(self):
        result = _run(
            perform_action=MagicMock(side_effect=PiholeAuthError("unauth", 401))
        )
        assert result.get("_failed") is True
