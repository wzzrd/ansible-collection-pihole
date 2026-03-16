"""Tests for plugins/modules/domain.py"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.domain import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
)

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.domain"

EXISTING_DOMAIN = {
    "domain": "ads.example.com",
    "type": "deny",
    "kind": "exact",
    "comment": "ad server",
    "enabled": True,
    "groups": [0],
}

BASE_PARAMS = {
    "pihole": "https://pihole.local",
    "sid": "sid",
    "domain": "ads.example.com",
    "type": "deny",
    "kind": "exact",
    "comment": None,
    "groups": ["Default"],
    "enabled": True,
    "state": "present",
}


def _run(
    params=None, check_mode=False, existing=None, current_location=None, group_ids=None
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

    location = current_location or (("deny", "exact") if existing is not None else None)
    mock_group_ids = MagicMock(return_value=group_ids if group_ids is not None else [0])
    mock_get = MagicMock(return_value=(existing, location))
    mock_add = MagicMock(return_value={"domains": [EXISTING_DOMAIN]})
    mock_update = MagicMock(return_value={"domains": [EXISTING_DOMAIN]})
    mock_delete = MagicMock(return_value=True)

    with ExitStack() as stack:
        stack.enter_context(patch(f"{BASE}.AnsibleModule", return_value=mock_mod))
        stack.enter_context(patch(f"{BASE}.PiholeApiClient", return_value=MagicMock()))
        stack.enter_context(patch(f"{BASE}.group_names_to_ids", mock_group_ids))
        stack.enter_context(patch(f"{BASE}.get_domain", mock_get))
        stack.enter_context(patch(f"{BASE}.add_domain", mock_add))
        stack.enter_context(patch(f"{BASE}.update_domain", mock_update))
        stack.enter_context(patch(f"{BASE}.delete_domain", mock_delete))
        try:
            main()
        except SystemExit:
            pass

    return result, mock_add, mock_update, mock_delete


class TestDomainModulePresent:
    def test_not_exists_creates(self):
        result, mock_add, _, _ = _run(existing=None)
        assert result.get("changed") is True
        mock_add.assert_called_once()

    def test_exists_no_changes_no_update(self):
        result, _, mock_update, _ = _run(existing=EXISTING_DOMAIN, group_ids=[0])
        assert result.get("changed") is False
        mock_update.assert_not_called()

    def test_exists_different_type_triggers_update(self):
        params = {**BASE_PARAMS, "type": "allow"}
        result, _, mock_update, _ = _run(
            existing=EXISTING_DOMAIN, params=params, group_ids=[0]
        )
        assert result.get("changed") is True
        mock_update.assert_called_once()

    def test_check_mode_no_add(self):
        result, mock_add, _, _ = _run(existing=None, check_mode=True)
        assert result.get("changed") is True
        mock_add.assert_not_called()


class TestDomainModuleAbsent:
    def _absent(self, domain_type="deny", kind="exact"):
        return {**BASE_PARAMS, "state": "absent", "type": domain_type, "kind": kind}

    def test_exists_in_correct_list_deletes(self):
        result, _, _, mock_delete = _run(
            existing=EXISTING_DOMAIN, params=self._absent()
        )
        assert result.get("changed") is True
        mock_delete.assert_called_once()

    def test_exists_in_different_list_no_change(self):
        result, _, _, mock_delete = _run(
            existing=EXISTING_DOMAIN,
            current_location=("deny", "exact"),
            params=self._absent(domain_type="allow"),
        )
        assert result.get("changed") is False
        mock_delete.assert_not_called()

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
                with patch(f"{BASE}.group_names_to_ids", return_value=[0]):
                    with patch(
                        f"{BASE}.get_domain", side_effect=PiholeAuthError("x", 401)
                    ):
                        try:
                            main()
                        except SystemExit:
                            pass

        assert result.get("_failed") is True
