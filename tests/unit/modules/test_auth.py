"""Tests for plugins/modules/auth.py"""

from unittest.mock import MagicMock, patch

from ansible_collections.wzzrd.pihole.plugins.modules.auth import main
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import PiholeAuthError

BASE = "ansible_collections.wzzrd.pihole.plugins.modules.auth"

PARAMS = {"pihole": "https://pihole.local", "password": "secret"}


def _run(authenticate_return="test-sid", authenticate_side_effect=None):
    result = {}

    mock_mod = MagicMock()
    mock_mod.params = PARAMS
    mock_mod.check_mode = False
    mock_mod.exit_json.side_effect = lambda **kw: result.update(kw) or (_ for _ in ()).throw(SystemExit(0))
    mock_mod.fail_json.side_effect = lambda **kw: (result.update({"_failed": True, **kw})) or (_ for _ in ()).throw(SystemExit(1))

    mock_client_class = MagicMock()
    if authenticate_side_effect:
        mock_client_class.authenticate.side_effect = authenticate_side_effect
    else:
        mock_client_class.authenticate.return_value = authenticate_return

    with patch(f"{BASE}.AnsibleModule", return_value=mock_mod):
        with patch(f"{BASE}.PiholeApiClient", mock_client_class):
            try:
                main()
            except SystemExit:
                pass

    return result, mock_client_class


class TestAuthModule:
    def test_success_returns_sid(self):
        result, _ = _run(authenticate_return="abc123")
        assert result.get("sid") == "abc123"

    def test_authenticate_called_with_url_and_password(self):
        _, mock_client_class = _run()
        mock_client_class.authenticate.assert_called_once_with("https://pihole.local", "secret")

    def test_auth_error_calls_fail_json(self):
        result, _ = _run(authenticate_side_effect=PiholeAuthError("bad password", 401))
        assert result.get("_failed") is True
