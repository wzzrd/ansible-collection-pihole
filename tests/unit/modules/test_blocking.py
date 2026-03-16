"""Tests for plugins/modules/blocking.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.blocking import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.blocking"

STATUS_ENABLED = {"blocking": "enabled", "timer": None}
STATUS_DISABLED = {"blocking": "disabled", "timer": None}


def _run(params, check_mode=False, current_status=None, set_side_effect=None):
    result = {}

    def fake_exit(**kw):
        result.update(kw)
        raise SystemExit(0)

    def fake_fail(**kw):
        result["_failed"] = True
        result.update(kw)
        raise SystemExit(1)

    mock_mod = MagicMock()
    mock_mod.params = params
    mock_mod.check_mode = check_mode
    mock_mod.exit_json.side_effect = fake_exit
    mock_mod.fail_json.side_effect = fake_fail

    mock_get = MagicMock(return_value=current_status or STATUS_ENABLED)
    mock_set = MagicMock(return_value=STATUS_ENABLED)
    if set_side_effect:
        mock_get.side_effect = set_side_effect

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.get_blocking_status", mock_get))
        stack.enter_context(patch(f"{BASE}.set_blocking_status", mock_set))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_set


def _params(enabled=True, timer=0, force=False):
    return {
        "pihole": "https://pihole.local",
        "sid": "sid",
        "enabled": enabled,
        "timer": timer,
        "force": force,
    }


class TestBlockingModule:
    def test_already_enabled_no_change(self):
        result, mock_set = _run(_params(enabled=True), current_status=STATUS_ENABLED)
        assert result.get("changed") is False
        mock_set.assert_not_called()

    def test_disabled_want_enabled_changes(self):
        result, mock_set = _run(_params(enabled=True), current_status=STATUS_DISABLED)
        assert result.get("changed") is True
        mock_set.assert_called_once()

    def test_force_causes_change_even_if_same_state(self):
        result, mock_set = _run(
            _params(enabled=True, force=True), current_status=STATUS_ENABLED
        )
        assert result.get("changed") is True
        mock_set.assert_called_once()

    def test_timer_differs_causes_change(self):
        current = {"blocking": "disabled", "timer": 100}
        result, _ = _run(_params(enabled=False, timer=300), current_status=current)
        assert result.get("changed") is True

    def test_check_mode_does_not_call_set(self):
        result, mock_set = _run(
            _params(enabled=True), check_mode=True, current_status=STATUS_DISABLED
        )
        assert result.get("changed") is True
        mock_set.assert_not_called()

    def test_auth_error_calls_fail_json(self):
        mock_mod = MagicMock()
        mock_mod.params = _params()
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
                    f"{BASE}.get_blocking_status", side_effect=PiholeAuthError("x", 401)
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

        assert result.get("_failed") is True
