"""Tests for NUTPoller — mock socket: happy path, auth, retry, parse errors."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.models.power_snapshot import PowerSnapshot
from src.services.nut_poller import NUTPoller

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockNUTFileHandle:
    """Simulates a NUT socket file handle with separate read/write buffers."""

    def __init__(self, response_lines: list[str]) -> None:
        self._lines: list[str] = response_lines
        self._pos = 0
        self.written: list[str] = []

    def readline(self) -> str:
        """Return the next line from the mock buffer, or empty string when exhausted."""
        if self._pos < len(self._lines):
            line = self._lines[self._pos] + "\n"
            self._pos += 1
            return line
        return ""

    def __iter__(self):  # type: ignore[override]
        while self._pos < len(self._lines):
            line = self._lines[self._pos] + "\n"
            self._pos += 1
            yield line

    def write(self, s: str) -> int:
        """Record a write to the buffer and return the byte count."""
        self.written.append(s)
        return len(s)

    def flush(self) -> None:
        """No-op flush; required by the file-handle interface."""


def _make_mock_socket(lines: list[str]) -> MagicMock:
    """Return a mock socket whose makefile() yields the given lines."""
    fh = _MockNUTFileHandle(lines)
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.makefile.return_value = fh
    return mock_sock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_poll_returns_power_snapshot() -> None:
    """NUTPoller.poll() returns a populated PowerSnapshot on a successful response."""
    lines = [
        'VAR ups ups.load "50"',
        'VAR ups ups.status "OL"',
        'VAR ups battery.charge "90"',
        'VAR ups battery.runtime "1200"',
        'VAR ups input.voltage "230"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    assert isinstance(snap, PowerSnapshot)
    assert snap.load_percent == pytest.approx(50.0)
    assert snap.ups_status == "OL"
    assert snap.battery_percent == pytest.approx(90.0)
    assert snap.runtime_seconds == 1200
    assert snap.input_voltage == pytest.approx(230.0)


def test_poll_derives_power_watts_from_load_and_nominal() -> None:
    """power_watts is derived as nominal × load% when no direct watt reading is available."""
    lines = [
        'VAR ups ups.load "40"',
        'VAR ups ups.power.nominal "1000"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    # expected: 1000 × 40 / 100 = 400 W
    assert snap.power_watts == pytest.approx(400.0)


def test_poll_with_metadata_returns_metadata_dict() -> None:
    """poll_with_metadata() returns raw UPS variables alongside the snapshot."""
    lines = [
        'VAR ups ups.model "APC Smart-UPS 1500"',
        'VAR ups ups.firmware "1.3"',
        'VAR ups ups.serial "SN12345"',
        'VAR ups ups.mfr "APC"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        _, metadata = poller.poll_with_metadata()
    assert metadata["ups.model"] == "APC Smart-UPS 1500"
    assert metadata["ups.firmware"] == "1.3"
    assert metadata["ups.mfr"] == "APC"


def test_list_ups_returns_device_names() -> None:
    """list_ups() returns all device names from a LIST UPS response."""
    lines = [
        'UPS ups "Main UPS"',
        'UPS ups2 "Secondary UPS"',
        "END LIST UPS",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller()
        names = poller.list_ups()
    assert "ups" in names
    assert "ups2" in names


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_authentication_sends_username_and_password() -> None:
    """Credentials are forwarded as USERNAME / PASSWORD commands before polling."""
    var_lines = ['VAR ups ups.status "OL"', "END LIST VAR ups"]
    auth_lines = ["OK", "OK"] + var_lines

    fh = _MockNUTFileHandle(auth_lines)
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.makefile.return_value = fh

    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(username="admin", password="secret", ups_name="ups")  # NOSONAR
        poller.poll()

    assert any("USERNAME admin" in w for w in fh.written)
    assert any("PASSWORD secret" in w for w in fh.written)


def test_authentication_failure_raises_runtime_error() -> None:
    """An ERR ACCESS-DENIED response raises RuntimeError with 'authentication' in the message."""
    fh = _MockNUTFileHandle(["ERR ACCESS-DENIED"])
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.makefile.return_value = fh

    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(username="admin", password="wrong")  # NOSONAR
        with pytest.raises(RuntimeError, match="authentication"):
            poller.poll()


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def test_poll_retries_on_os_error() -> None:
    """poll() retries on a transient OSError and succeeds on the second attempt."""
    lines = ['VAR ups ups.status "OL"', "END LIST VAR ups"]
    good_sock = _make_mock_socket(lines)

    call_count = 0

    def fake_create_connection(*_args: object, **_kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("connection refused")
        return good_sock

    with patch("socket.create_connection", side_effect=fake_create_connection):
        poller = NUTPoller(ups_name="ups", max_retries=1)
        snap = poller.poll()

    assert call_count == 2
    assert isinstance(snap, PowerSnapshot)


def test_poll_raises_after_all_retries_exhausted() -> None:
    """poll() re-raises the last OSError when all retry attempts are exhausted."""
    with patch("socket.create_connection", side_effect=OSError("always fails")):
        poller = NUTPoller(max_retries=1)
        with pytest.raises(OSError):
            poller.poll()


# ---------------------------------------------------------------------------
# Parse edge cases
# ---------------------------------------------------------------------------

def test_poll_handles_quoted_value_with_spaces() -> None:
    """Quoted NUT values containing spaces are parsed correctly."""
    lines = [
        'VAR ups ups.model "APC Smart-UPS XL"',
        'VAR ups ups.status "OL CHRG"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    assert snap.ups_status == "OL CHRG"


def test_poll_ignores_unknown_variables() -> None:
    """Unknown NUT variable names are silently skipped without raising."""
    lines = [
        'VAR ups ups.unknown.field "whatever"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    assert isinstance(snap, PowerSnapshot)


def test_poll_with_empty_var_list_returns_minimal_snapshot() -> None:
    """An empty LIST VAR response still produces a valid PowerSnapshot with defaults."""
    lines = ["END LIST VAR ups"]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    assert isinstance(snap, PowerSnapshot)


# ---------------------------------------------------------------------------
# Password rejection (line 101)
# ---------------------------------------------------------------------------


def test_password_rejection_raises_runtime_error() -> None:
    """Successful username auth followed by rejected password raises RuntimeError."""
    fh = _MockNUTFileHandle(["OK", "ERR ACCESS-DENIED"])
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.makefile.return_value = fh

    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(username="admin", password="wrongpass", ups_name="ups")  # NOSONAR
        with pytest.raises(RuntimeError, match="password"):
            poller.poll()


# ---------------------------------------------------------------------------
# list_ups retry logic (lines 168-177, 195-204)
# ---------------------------------------------------------------------------


def test_list_ups_retries_on_os_error() -> None:
    """list_ups retries on a transient OSError and succeeds on the second attempt."""
    list_lines = ['UPS ups "Main UPS"', "END LIST UPS"]
    good_sock = _make_mock_socket(list_lines)

    call_count = 0

    def fake_create_connection(*_args: object, **_kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("connection refused")
        return good_sock

    with patch("socket.create_connection", side_effect=fake_create_connection):
        poller = NUTPoller(max_retries=1)
        names = poller.list_ups()

    assert call_count == 2
    assert "ups" in names


def test_list_ups_raises_after_all_retries_exhausted() -> None:
    """list_ups raises the last OSError when all retry attempts fail."""
    with patch("socket.create_connection", side_effect=OSError("always fails")):
        poller = NUTPoller(max_retries=0)
        with pytest.raises(OSError):
            poller.list_ups()


# ---------------------------------------------------------------------------
# poll_with_metadata retry logic (lines 195-204, 216-217)
# ---------------------------------------------------------------------------


def test_poll_with_metadata_retries_on_os_error() -> None:
    """poll_with_metadata retries on a transient OSError and succeeds."""
    lines = [
        'VAR ups ups.model "APC Smart-UPS"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    good_sock = _make_mock_socket(lines)

    call_count = 0

    def fake_create_connection(*_args: object, **_kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("connection refused")
        return good_sock

    with patch("socket.create_connection", side_effect=fake_create_connection):
        poller = NUTPoller(ups_name="ups", max_retries=1)
        snap, _ = poller.poll_with_metadata()

    assert isinstance(snap, PowerSnapshot)


def test_poll_with_metadata_raises_after_all_retries_exhausted() -> None:
    """poll_with_metadata raises the last OSError when all attempts fail."""
    with patch("socket.create_connection", side_effect=OSError("always fails")):
        poller = NUTPoller(ups_name="ups", max_retries=0)
        with pytest.raises(OSError):
            poller.poll_with_metadata()


# ---------------------------------------------------------------------------
# _apply_field float parse failure (line 225)
# ---------------------------------------------------------------------------


def test_apply_field_logs_warning_on_non_float_value() -> None:
    """A non-numeric NUT variable produces a warning and leaves the field as None."""
    lines = [
        'VAR ups ups.load "not-a-number"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    # Failed float parse → load_percent should be None
    assert snap.load_percent is None


# ---------------------------------------------------------------------------
# _derive_power_watts ValueError (lines 234-235)
# ---------------------------------------------------------------------------


def test_derive_power_watts_handles_nonnumeric_nominal() -> None:
    """A non-numeric nominal power value is silently ignored without raising."""
    lines = [
        'VAR ups ups.load "40"',
        'VAR ups ups.realpower.nominal "not-a-number"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    # Invalid nominal → power_watts cannot be derived
    assert snap.power_watts is None


def test_derive_power_watts_skips_when_power_watts_already_set() -> None:
    """_derive_power_watts returns early when power_watts is already set (line 225)."""
    lines = [
        'VAR ups ups.realpower "300"',
        'VAR ups ups.realpower.nominal "1000"',
        'VAR ups ups.load "30"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    # power_watts set directly from ups.realpower, not re-derived
    assert snap.power_watts == pytest.approx(300.0)


def test_derive_power_watts_skips_when_load_is_missing() -> None:
    """_derive_power_watts returns early when load_percent is None (line 231)."""
    lines = [
        'VAR ups ups.realpower.nominal "1000"',
        'VAR ups ups.status "OL"',
        "END LIST VAR ups",
    ]
    mock_sock = _make_mock_socket(lines)
    with patch("socket.create_connection", return_value=mock_sock):
        poller = NUTPoller(ups_name="ups")
        snap = poller.poll()
    # load_percent is None so power_watts cannot be derived
    assert snap.power_watts is None
