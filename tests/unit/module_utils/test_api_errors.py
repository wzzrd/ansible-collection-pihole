"""Tests for plugins/module_utils/api_errors.py"""

import pytest

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
    PiholeError,
    PiholeNotFoundError,
    PiholeValidationError,
)


class TestPiholeErrorHierarchy:
    def test_pihole_error_is_exception(self):
        assert issubclass(PiholeError, Exception)

    def test_api_error_is_pihole_error(self):
        assert issubclass(PiholeApiError, PiholeError)

    def test_auth_error_is_api_error(self):
        assert issubclass(PiholeAuthError, PiholeApiError)

    def test_not_found_error_is_api_error(self):
        assert issubclass(PiholeNotFoundError, PiholeApiError)

    def test_validation_error_is_pihole_error(self):
        assert issubclass(PiholeValidationError, PiholeError)

    def test_connection_error_is_pihole_error(self):
        assert issubclass(PiholeConnectionError, PiholeError)


class TestPiholeApiError:
    def test_message_only(self):
        err = PiholeApiError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.status_code is None
        assert err.response_text is None

    def test_with_status_code(self):
        err = PiholeApiError("bad request", status_code=400)
        assert "400" in str(err)
        assert err.status_code == 400

    def test_with_response_text(self):
        err = PiholeApiError(
            "oops", status_code=500, response_text='{"error":"internal"}'
        )
        assert err.response_text == '{"error":"internal"}'

    def test_str_without_status_code(self):
        err = PiholeApiError("no status")
        assert str(err) == "no status"

    def test_str_with_status_code(self):
        err = PiholeApiError("not found", status_code=404)
        assert str(err) == "not found (HTTP 404)"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(PiholeApiError) as exc_info:
            raise PiholeApiError("test error", status_code=503)
        assert exc_info.value.status_code == 503


class TestPiholeAuthError:
    def test_inherits_str_with_status(self):
        err = PiholeAuthError("unauthorized", status_code=401)
        assert "401" in str(err)

    def test_caught_as_api_error(self):
        with pytest.raises(PiholeApiError):
            raise PiholeAuthError("bad creds")

    def test_caught_as_pihole_error(self):
        with pytest.raises(PiholeError):
            raise PiholeAuthError("bad creds")


class TestPiholeNotFoundError:
    def test_caught_as_api_error(self):
        with pytest.raises(PiholeApiError):
            raise PiholeNotFoundError("not here", status_code=404)

    def test_status_code_stored(self):
        err = PiholeNotFoundError("missing", status_code=404)
        assert err.status_code == 404


class TestPiholeValidationError:
    def test_message(self):
        err = PiholeValidationError("invalid input")
        assert str(err) == "invalid input"

    def test_caught_as_pihole_error(self):
        with pytest.raises(PiholeError):
            raise PiholeValidationError("bad data")

    def test_not_caught_as_api_error(self):
        # PiholeValidationError is NOT a PiholeApiError
        with pytest.raises(PiholeValidationError):
            raise PiholeValidationError("wrong type")
        assert not issubclass(PiholeValidationError, PiholeApiError)


class TestPiholeConnectionError:
    def test_message(self):
        err = PiholeConnectionError("timeout")
        assert str(err) == "timeout"

    def test_caught_as_pihole_error(self):
        with pytest.raises(PiholeError):
            raise PiholeConnectionError("network down")

    def test_not_caught_as_api_error(self):
        assert not issubclass(PiholeConnectionError, PiholeApiError)
