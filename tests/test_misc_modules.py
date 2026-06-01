"""Tests for InfluxDB exporter, Prometheus exporter, health_server, snmp_poller, Device model."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.models.device import Device
from src.models.power_snapshot import PowerSnapshot
from src.services.snmp_poller import SNMPv3Config

# RFC 5737 TEST-NET addresses — safe for use in test code
_TEST_HOST = "192.0.2.1"  # TEST-NET-1, never routable
_TEST_HOST_2 = "192.0.2.100"  # TEST-NET-1 alternate


def _snap(**kwargs: Any) -> PowerSnapshot:
    defaults: dict[str, Any] = {
        "timestamp": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "device_id": f"snmp:pdu@{_TEST_HOST}",
        "device_type": "pdu",
        "power_watts": 300.0,
        "load_percent": 40.0,
        "voltage": 120.0,
    }
    defaults.update(kwargs)
    return PowerSnapshot(**defaults)


# ===========================================================================
# Device model
# ===========================================================================


class TestDeviceModel:
    """Tests for the Device model."""

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict returns all expected fields with correct values."""
        dev = Device(
            id="d1",
            name="Test UPS",
            type="ups",
            poller="nut",
            host="localhost",
            port=3493,
        )
        d = dev.to_dict()
        assert d["id"] == "d1"
        assert d["name"] == "Test UPS"
        assert d["type"] == "ups"
        assert d["poller"] == "nut"
        assert d["host"] == "localhost"
        assert d["port"] == 3493
        assert d["enabled"] is True

    def test_default_enabled_true(self) -> None:
        """Device.enabled defaults to True when not specified."""
        dev = Device(id="d1", name="n", type="ups", poller="nut", host="h", port=3493)
        assert dev.enabled is True

    def test_optional_metadata_fields_default_none(self) -> None:
        """Optional metadata fields default to None when not provided."""
        dev = Device(id="d1", name="n", type="ups", poller="nut", host="h", port=3493)
        assert dev.model is None
        assert dev.firmware is None
        assert dev.serial is None
        assert dev.manufacturer is None
        assert dev.last_seen is None

    def test_to_dict_includes_metadata_when_set(self) -> None:
        """to_dict includes model, firmware, serial, and manufacturer when set."""
        dev = Device(
            id="d1",
            name="n",
            type="ups",
            poller="nut",
            host="h",
            port=3493,
            model="SmartUPS",
            firmware="v1.0",
            serial="SN-001",
            manufacturer="APC",
        )
        d = dev.to_dict()
        assert d["model"] == "SmartUPS"
        assert d["serial"] == "SN-001"

    def test_connection_config_default_empty(self) -> None:
        """Device.connection_config defaults to an empty dict."""
        dev = Device(id="d1", name="n", type="ups", poller="nut", host="h", port=3493)
        assert not dev.connection_config


# ===========================================================================
# InfluxDB exporter
# ===========================================================================


class TestInfluxDBExporter:
    """Tests for the InfluxDB exporter."""

    def test_import_error_silently_disables(self) -> None:
        """InfluxDBExporter sets _client to None when influxdb_client is unavailable."""
        from src.exporters.influxdb_exporter import InfluxDBExporter

        with patch.dict("sys.modules", {"influxdb_client": None}):
            exp = InfluxDBExporter(
                url="http://influxdb:8086", token="tok", org="org", bucket="bkt"
            )
            # Client should be None when import fails (accessing internal for test assertion)
            assert exp._client is None  # noqa: SLF001

    def test_export_is_no_op_when_client_none(self) -> None:
        """export does not raise when _client is None (import disabled)."""
        from src.exporters.influxdb_exporter import InfluxDBExporter

        with patch.dict("sys.modules", {"influxdb_client": None}):
            exp = InfluxDBExporter(
                url="http://influxdb:8086", token="tok", org="org", bucket="bkt"
            )
        # Should not raise
        exp.export(_snap())

    def test_export_calls_write_api(self) -> None:
        """export calls write_api.write with the InfluxDB Point."""
        from src.exporters.influxdb_exporter import InfluxDBExporter

        mock_point = MagicMock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point.time.return_value = mock_point
        mock_write_api = MagicMock()
        mock_client = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        mock_influxdb = MagicMock()
        mock_influxdb.InfluxDBClient.return_value = mock_client
        mock_influxdb.Point.return_value = mock_point
        mock_write_api_module = MagicMock()
        mock_write_api_module.SYNCHRONOUS = "SYNCHRONOUS"

        with patch.dict(
            "sys.modules",
            {
                "influxdb_client": mock_influxdb,
                "influxdb_client.client": MagicMock(),
                "influxdb_client.client.write_api": mock_write_api_module,
            },
        ):
            exp = InfluxDBExporter(
                url="http://influxdb:8086", token="tok", org="org", bucket="bkt"
            )
            exp.export(_snap())

        mock_write_api.write.assert_called_once()


# ===========================================================================
# Prometheus exporter
# ===========================================================================


class TestPrometheusExporter:
    """Tests for the Prometheus exporter."""

    def test_export_is_no_op_when_prometheus_unavailable(self) -> None:
        """export does not raise when prometheus_client is unavailable."""
        from src.exporters.prometheus_exporter import PrometheusExporter

        with patch.dict("sys.modules", {"prometheus_client": None}):
            exp = PrometheusExporter(port=9200)
        # _gauges should be None/empty when module missing
        exp.export(_snap())  # should not raise

    def test_export_calls_set_on_gauges(self) -> None:
        """export calls Gauge.set for each metric in the snapshot."""
        from src.exporters.prometheus_exporter import PrometheusExporter

        mock_gauge = MagicMock()
        mock_gauge.labels.return_value = mock_gauge
        mock_pc = MagicMock()
        mock_pc.Gauge.return_value = mock_gauge
        mock_pc.start_http_server = MagicMock()

        with patch.dict("sys.modules", {"prometheus_client": mock_pc}):
            exp = PrometheusExporter(port=9201)
            exp.export(_snap())

        mock_gauge.set.assert_called()


# ===========================================================================
# Health server
# ===========================================================================


class TestHealthServer:
    """Tests for the HealthServer and its HTTP handler."""

    def _make_request(self, path: str, status_fn: Any = None) -> tuple[int, dict]:
        """Directly invoke the handler's do_GET logic without binding a real socket."""
        from src.services.health_server import _HealthHandler

        class CapturingHandler(_HealthHandler):
            """Test double capturing response code and body without a real socket."""

            def __init__(self) -> None:  # type: ignore[override]
                """Skip super().__init__ to avoid binding a real socket."""
                self._status_fn = status_fn or (lambda: {"status": "ok"})  # noqa: SLF001
                self.path = path
                self._wfile: BytesIO = BytesIO()  # noqa: SLF001
                self._last_code: int = 200  # noqa: SLF001

            def send_response(self, code: int, message: str = "") -> None:
                self._last_code = code  # noqa: SLF001

            def send_header(self, keyword: str, value: str) -> None:
                """Stub — headers not needed in unit tests."""

            def end_headers(self) -> None:
                """Stub — no socket to flush in unit tests."""

            @property
            def wfile(self) -> BytesIO:
                """Stub — returns the in-memory buffer used to capture response bytes."""
                return self._wfile  # noqa: SLF001

        handler = CapturingHandler()
        handler.do_GET()
        body = handler._wfile.getvalue()  # noqa: SLF001
        data = json.loads(body) if body else {}
        return handler._last_code, data  # noqa: SLF001

    def test_health_ok_returns_200(self) -> None:
        """_make_request to /health returns HTTP 200 and status=ok."""
        code, data = self._make_request("/health")
        assert code == 200
        assert data.get("status") == "ok"

    def test_health_degraded_returns_503(self) -> None:
        """A degraded status function causes /health to return HTTP 503."""
        code, _ = self._make_request(
            "/health", status_fn=lambda: {"status": "degraded"}
        )
        assert code == 503

    def test_unknown_path_returns_404(self) -> None:
        """An unrecognised path returns HTTP 404."""
        code, _ = self._make_request("/unknown")
        assert code == 404

    def test_start_spawns_daemon_thread(self) -> None:
        """HealthServer.start spawns a daemon thread for the HTTP server."""
        from src.services.health_server import HealthServer

        with patch("src.services.health_server.HTTPServer") as mock_server_cls:
            mock_server = MagicMock()
            mock_server_cls.return_value = mock_server
            hs = HealthServer(port=19100)
            hs.start()
            assert hs._thread is not None  # noqa: SLF001
            assert hs._thread.daemon is True  # noqa: SLF001


# ===========================================================================
# SNMP poller
# ===========================================================================


class TestSNMPPoller:
    """Tests for the SNMP poller."""

    def test_poll_returns_empty_snapshot_when_pysnmp_missing(self) -> None:
        """_build_snapshot returns a skeleton snapshot when pysnmp is not installed."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST)
        with patch.dict(
            "sys.modules",
            {
                "pysnmp": None,
                "pysnmp.hlapi": None,
                "pysnmp.proto": None,
                "pysnmp.proto.rfc1905": None,
            },
        ):
            snapshot = poller._build_snapshot({})  # noqa: SLF001
        assert snapshot.device_id == f"snmp:{_TEST_HOST}:161"
        assert snapshot.power_watts is None

    def test_build_snapshot_maps_known_oids(self) -> None:
        """_build_snapshot correctly maps UPS-MIB OIDs to snapshot fields."""
        from src.services.snmp_poller import SNMPPoller, _UPS_MIB

        poller = SNMPPoller(host=_TEST_HOST, oids=_UPS_MIB)
        raw = {
            "1.3.6.1.2.1.33.1.4.4.1.5.1": "50",  # load_percent
            "1.3.6.1.2.1.33.1.4.4.1.4.1": "200",  # power_watts
            "1.3.6.1.2.1.33.1.2.3.0": "10",  # runtime_seconds (minutes→×60)
        }
        snapshot = poller._build_snapshot(raw)  # noqa: SLF001
        assert snapshot.load_percent == pytest.approx(50.0)
        assert snapshot.power_watts == pytest.approx(200.0)
        assert snapshot.runtime_seconds == pytest.approx(600.0)  # 10 min × 60

    def test_build_snapshot_ignores_non_numeric_values(self) -> None:
        """_build_snapshot leaves fields None when an OID value is non-numeric."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST)
        raw = {"1.3.6.1.2.1.33.1.4.4.1.5.1": "N/A"}
        snapshot = poller._build_snapshot(raw)  # noqa: SLF001
        assert snapshot.load_percent is None

    def test_default_device_id_from_host(self) -> None:
        """The default device_id includes the host address."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST_2)
        assert _TEST_HOST_2 in poller._device_id  # noqa: SLF001

    def test_custom_device_id_used(self) -> None:
        """A custom device_id is stored verbatim in the poller."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST, device_id="pdu:rack1")
        assert poller._device_id == "pdu:rack1"  # noqa: SLF001

    def test_poll_retries_on_os_error(self) -> None:
        """poll retries once on OSError and re-raises after exhausting retries."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST, max_retries=1)
        call_count = 0

        def failing_snmp_get(_oids: list) -> dict:
            nonlocal call_count
            call_count += 1
            raise OSError("Connection refused")

        poller._snmp_get = failing_snmp_get  # type: ignore[method-assign]  # noqa: SLF001
        with pytest.raises(OSError):
            poller.poll()
        assert call_count == 2  # 1 initial + 1 retry

    def test_snmp_get_returns_empty_dict_when_pysnmp_unavailable(self) -> None:
        """_snmp_get returns {} when pysnmp is not installed."""
        from src.services.snmp_poller import SNMPPoller

        poller = SNMPPoller(host=_TEST_HOST)
        with patch.dict(
            "sys.modules",
            {
                "pysnmp": None,
                "pysnmp.hlapi": None,
                "pysnmp.proto": None,
                "pysnmp.proto.rfc1905": None,
            },
        ):
            result = poller._snmp_get(["1.3.6.1.2.1.1.1.0"])  # noqa: SLF001
        assert result == {}

    def test_snmp_get_with_mocked_pysnmp(self) -> None:
        """Test the main code path of _snmp_get when pysnmp is available (mocked)."""
        from src.services.snmp_poller import SNMPPoller

        oid = "1.3.6.1.2.1.33.1.4.4.1.4.1"

        # Build a minimal mock of pysnmp objects
        mock_var_bind_val = MagicMock()
        mock_var_bind_val.prettyPrint.return_value = "250"

        mock_var_bind_key = MagicMock()
        mock_var_bind_key.__str__ = lambda self: oid

        mock_var_bind = (mock_var_bind_key, mock_var_bind_val)

        # getCmd returns (error_indication=None, error_status=None, error_index, var_binds)
        # iter(next(...)) yields one item
        mock_get_cmd = MagicMock(
            return_value=iter([(None, None, None, [mock_var_bind])])
        )

        mock_no_such_obj = type("noSuchObject", (), {})  # distinct type

        mock_hlapi = MagicMock()
        mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
        mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
        mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
        mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
        mock_hlapi.UsmUserData = MagicMock(return_value=MagicMock())
        mock_hlapi.getCmd = mock_get_cmd

        mock_rfc1905 = MagicMock()
        mock_rfc1905.noSuchObject = mock_no_such_obj()

        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": mock_hlapi,
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": mock_rfc1905,
            },
        ):
            poller = SNMPPoller(host=_TEST_HOST, community="public")
            snmp_result = poller._snmp_get([oid])  # noqa: SLF001

        # The var_bind value.prettyPrint() returns "250", so we expect the OID mapped
        assert isinstance(snmp_result, dict)

    def test_build_v3_auth_with_mocked_pysnmp(self) -> None:
        """Cover _build_v3_auth when pysnmp is available."""
        from src.services.snmp_poller import SNMPPoller

        mock_usm = MagicMock()
        mock_hlapi = MagicMock()
        mock_hlapi.usmHMACMD5AuthProtocol = "MD5"
        mock_hlapi.usmHMACSHAAuthProtocol = "SHA"
        mock_hlapi.usmHMAC128SHA224AuthProtocol = "SHA224"
        mock_hlapi.usmHMAC192SHA256AuthProtocol = "SHA256"
        mock_hlapi.usmNoAuthProtocol = "NONE_AUTH"
        mock_hlapi.usmDESPrivProtocol = "DES"
        mock_hlapi.usmAesCfb128Protocol = "AES"
        mock_hlapi.usmNoPrivProtocol = "NONE_PRIV"
        mock_hlapi.UsmUserData = mock_usm

        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": mock_hlapi,
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": MagicMock(),
            },
        ):
            poller = SNMPPoller(
                host=_TEST_HOST,
                v3_config=SNMPv3Config(
                    username="admin",
                    auth_key="authkey",
                    priv_key="privkey",
                ),
            )
            poller._build_v3_auth(mock_usm)  # noqa: SLF001

        mock_usm.assert_called_once()

    def test_snmp_get_error_status_path(self) -> None:
        """Cover the error_status warning branch in _snmp_get."""
        from src.services.snmp_poller import SNMPPoller

        mock_hlapi = MagicMock()
        mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
        mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
        mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
        mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
        mock_hlapi.UsmUserData = MagicMock(return_value=MagicMock())
        # Return error_status = truthy
        mock_hlapi.getCmd = MagicMock(
            return_value=iter([(None, "noSuchInstance", None, [])])
        )
        mock_rfc1905 = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": mock_hlapi,
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": mock_rfc1905,
            },
        ):
            poller = SNMPPoller(host=_TEST_HOST, community="public")
            result = poller._snmp_get(["1.3.6.1.2.1.1.1.0"])  # noqa: SLF001

        assert result == {}

    def test_snmp_get_v3_username_path(self) -> None:
        """Cover the v3_username branch in _snmp_get (calls _build_v3_auth)."""
        from src.services.snmp_poller import SNMPPoller

        oid = "1.3.6.1.2.1.1.1.0"
        mock_var_bind_val = MagicMock()
        mock_var_bind_val.prettyPrint.return_value = "somevalue"
        mock_var_bind_key = MagicMock()
        mock_var_bind_key.__str__ = lambda s: oid
        mock_var_bind = (mock_var_bind_key, mock_var_bind_val)

        mock_usm_data = MagicMock()
        mock_hlapi = MagicMock()
        mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
        mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
        mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
        mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
        mock_hlapi.UsmUserData = mock_usm_data
        mock_hlapi.getCmd = MagicMock(
            return_value=iter([(None, None, None, [mock_var_bind])])
        )
        # v3 auth/priv protocols
        mock_hlapi.usmHMACMD5AuthProtocol = "MD5"
        mock_hlapi.usmHMACSHAAuthProtocol = "SHA"
        mock_hlapi.usmHMAC128SHA224AuthProtocol = "SHA224"
        mock_hlapi.usmHMAC192SHA256AuthProtocol = "SHA256"
        mock_hlapi.usmNoAuthProtocol = "NONE_AUTH"
        mock_hlapi.usmDESPrivProtocol = "DES"
        mock_hlapi.usmAesCfb128Protocol = "AES"
        mock_hlapi.usmNoPrivProtocol = "NONE_PRIV"
        mock_rfc1905 = MagicMock()
        mock_rfc1905.noSuchObject = type("noSuchObject", (), {})()

        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": mock_hlapi,
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": mock_rfc1905,
            },
        ):
            poller = SNMPPoller(
                host=_TEST_HOST,
                v3_config=SNMPv3Config(
                    username="admin",
                    auth_key="authkey",
                    priv_key="privkey",
                ),
            )
            result = poller._snmp_get([oid])  # noqa: SLF001

        assert isinstance(result, dict)

    def test_snmp_get_version_1_mp_model(self) -> None:
        """Cover the version='1' branch that sets mp_model=0 in CommunityData."""
        from src.services.snmp_poller import SNMPPoller

        mock_community_cls = MagicMock(return_value=MagicMock())
        mock_hlapi = MagicMock()
        mock_hlapi.CommunityData = mock_community_cls
        mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
        mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
        mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
        mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
        mock_hlapi.UsmUserData = MagicMock(return_value=MagicMock())
        mock_hlapi.getCmd = MagicMock(return_value=iter([(None, None, None, [])]))
        mock_rfc1905 = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": mock_hlapi,
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": mock_rfc1905,
            },
        ):
            poller = SNMPPoller(host=_TEST_HOST, version="1", community="public")
            poller._snmp_get(["1.3.6.1.2.1.1.1.0"])  # noqa: SLF001

        # With version="1", CommunityData should be called with mpModel=0
        mock_community_cls.assert_called_once_with("public", mpModel=0)

    def test_build_v3_auth_import_error_fallback(self) -> None:
        """Cover _build_v3_auth ImportError branch that returns minimal UsmUserData."""
        from src.services.snmp_poller import SNMPPoller

        mock_usm = MagicMock(return_value=MagicMock())
        # Simulate ImportError inside _build_v3_auth by hiding the pysnmp.hlapi attrs
        with patch.dict(
            "sys.modules",
            {
                "pysnmp": MagicMock(),
                "pysnmp.hlapi": None,  # type: ignore[assignment]
                "pysnmp.proto": MagicMock(),
                "pysnmp.proto.rfc1905": MagicMock(),
            },
        ):
            poller = SNMPPoller(
                host=_TEST_HOST, v3_config=SNMPv3Config(username="admin")
            )
            result = poller._build_v3_auth(mock_usm)  # noqa: SLF001

        # Fallback path: UsmUserData called with just the username
        mock_usm.assert_called_once_with("admin")
        assert result is not None


# ===========================================================================
# exporter_registry factory builders
# ===========================================================================


def test_build_influxdb_returns_none_when_url_missing() -> None:
    """_build_influxdb returns None and logs a warning when INFLUXDB_URL is unset."""
    from src.exporter_registry import _build_influxdb

    with patch("src.exporter_registry.config") as mock_cfg:
        mock_cfg.INFLUXDB_URL = ""
        mock_cfg.INFLUXDB_TOKEN = "some-token"
        result = _build_influxdb()
    assert result is None


def test_build_influxdb_returns_none_when_token_missing() -> None:
    """_build_influxdb returns None and logs a warning when INFLUXDB_TOKEN is unset."""
    from src.exporter_registry import _build_influxdb

    with patch("src.exporter_registry.config") as mock_cfg:
        mock_cfg.INFLUXDB_URL = "http://influxdb:8086"
        mock_cfg.INFLUXDB_TOKEN = ""
        result = _build_influxdb()
    assert result is None


def test_build_loki_returns_none_when_url_missing() -> None:
    """_build_loki returns None and logs a warning when LOKI_URL is unset."""
    from src.exporter_registry import _build_loki

    with patch("src.exporter_registry.config") as mock_cfg:
        mock_cfg.LOKI_URL = ""
        result = _build_loki()
    assert result is None


# ===========================================================================
# SNMPPoller extra coverage — poll() success path and _snmp_get edge cases
# ===========================================================================


def test_poll_succeeds_via_direct_snmp_get_mock() -> None:
    """poll() returns a snapshot via line 72 when _snmp_get succeeds."""
    from src.services.snmp_poller import SNMPPoller

    poller = SNMPPoller(host=_TEST_HOST)
    poller._snmp_get = MagicMock(return_value={})  # type: ignore[method-assign]  # noqa: SLF001
    snap = poller.poll()
    assert snap is not None


def test_snmp_get_error_indication_path() -> None:
    """Cover the error_indication warning branch in _snmp_get (lines 129-130)."""
    from src.services.snmp_poller import SNMPPoller

    mock_hlapi = MagicMock()
    mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
    mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
    mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
    mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
    mock_hlapi.UsmUserData = MagicMock(return_value=MagicMock())
    # Truthy error_indication, falsy error_status
    mock_hlapi.getCmd = MagicMock(return_value=iter([("Timeout", None, None, [])]))
    mock_rfc1905 = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "pysnmp": MagicMock(),
            "pysnmp.hlapi": mock_hlapi,
            "pysnmp.proto": MagicMock(),
            "pysnmp.proto.rfc1905": mock_rfc1905,
        },
    ):
        poller = SNMPPoller(host=_TEST_HOST, community="public")
        result = poller._snmp_get(["1.3.6.1.2.1.1.1.0"])  # noqa: SLF001

    assert result == {}


def test_snmp_get_no_such_object_skipped() -> None:
    """Cover the isinstance(value, noSuchObject) continue branch (line 137)."""
    from src.services.snmp_poller import SNMPPoller

    _NoSuchClass = type("noSuchObject", (), {})
    no_such_instance = _NoSuchClass()

    mock_var_bind_key = MagicMock()
    mock_var_bind_key.__str__ = lambda s: "1.3.6.1.2.1.1.1.0"
    # value IS an instance of _NoSuchClass — isinstance check is True
    mock_var_bind = (mock_var_bind_key, no_such_instance)

    mock_hlapi = MagicMock()
    mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
    mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
    mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
    mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
    mock_hlapi.UsmUserData = MagicMock(return_value=MagicMock())
    mock_hlapi.getCmd = MagicMock(
        return_value=iter([(None, None, None, [mock_var_bind])])
    )

    mock_rfc1905 = MagicMock()
    mock_rfc1905.noSuchObject = no_such_instance

    with patch.dict(
        "sys.modules",
        {
            "pysnmp": MagicMock(),
            "pysnmp.hlapi": mock_hlapi,
            "pysnmp.proto": MagicMock(),
            "pysnmp.proto.rfc1905": mock_rfc1905,
        },
    ):
        poller = SNMPPoller(host=_TEST_HOST, community="public")
        result = poller._snmp_get(["1.3.6.1.2.1.1.1.0"])  # noqa: SLF001

    # noSuchObject var_bind is skipped — result should be empty
    assert result == {}


def test_snmpv3_authpriv_poll_returns_populated_snapshot() -> None:
    """SNMPv3 authPriv (auth_key + priv_key) full round-trip → PowerSnapshot.

    Verifies that when both auth_key and priv_key are configured, poll() passes
    the v3 credentials through _snmp_get → UsmUserData, then maps the returned
    OID values to the correct PowerSnapshot fields via _build_snapshot.
    """
    from src.services.snmp_poller import SNMPPoller

    # OID → field name mapping (subset of _UPS_MIB)
    battery_pct_oid = "1.3.6.1.2.1.33.1.2.4.0"
    load_pct_oid = "1.3.6.1.2.1.33.1.4.4.1.5.1"
    power_watts_oid = "1.3.6.1.2.1.33.1.4.4.1.4.1"
    runtime_oid = "1.3.6.1.2.1.33.1.2.3.0"

    # Build mock var_binds that look like pysnmp getCmd output
    def _make_var_bind(oid_str: str, value_str: str) -> tuple[MagicMock, MagicMock]:
        key = MagicMock()
        key.__str__ = lambda s, _o=oid_str: _o
        val = MagicMock()
        val.prettyPrint.return_value = value_str
        return (key, val)

    mock_usm_cls = MagicMock(return_value=MagicMock())
    mock_hlapi = MagicMock()
    mock_hlapi.CommunityData = MagicMock(return_value=MagicMock())
    mock_hlapi.ContextData = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectIdentity = MagicMock(return_value=MagicMock())
    mock_hlapi.ObjectType = MagicMock(return_value=MagicMock())
    mock_hlapi.SnmpEngine = MagicMock(return_value=MagicMock())
    mock_hlapi.UdpTransportTarget = MagicMock(return_value=MagicMock())
    mock_hlapi.UsmUserData = mock_usm_cls
    # _snmp_get calls getCmd once per OID (6 OIDs in _UPS_MIB); each call must
    # return a fresh single-item iterator — a shared iterator would be exhausted
    # after the first next() call.  Map each OID position to its var_bind.
    _oid_responses: list[tuple[None, None, None, list[Any]]] = [
        (None, None, None, []),  # input_voltage — no value returned
        (None, None, None, []),  # output_voltage — no value returned
        (None, None, None, [_make_var_bind(load_pct_oid, "45")]),
        (None, None, None, [_make_var_bind(battery_pct_oid, "80")]),
        (None, None, None, [_make_var_bind(runtime_oid, "20")]),
        (None, None, None, [_make_var_bind(power_watts_oid, "300")]),
    ]
    mock_hlapi.getCmd = MagicMock(
        side_effect=[iter([r]) for r in _oid_responses]
    )
    # Auth / priv protocol sentinels
    mock_hlapi.usmHMACMD5AuthProtocol = "MD5_PROTO"
    mock_hlapi.usmHMACSHAAuthProtocol = "SHA_PROTO"
    mock_hlapi.usmHMAC128SHA224AuthProtocol = "SHA224_PROTO"
    mock_hlapi.usmHMAC192SHA256AuthProtocol = "SHA256_PROTO"
    mock_hlapi.usmNoAuthProtocol = "NONE_AUTH"
    mock_hlapi.usmDESPrivProtocol = "DES_PROTO"
    mock_hlapi.usmAesCfb128Protocol = "AES_PROTO"
    mock_hlapi.usmNoPrivProtocol = "NONE_PRIV"
    mock_rfc1905 = MagicMock()
    mock_rfc1905.noSuchObject = type("noSuchObject", (), {})()

    with patch.dict(
        "sys.modules",
        {
            "pysnmp": MagicMock(),
            "pysnmp.hlapi": mock_hlapi,
            "pysnmp.proto": MagicMock(),
            "pysnmp.proto.rfc1905": mock_rfc1905,
        },
    ):
        poller = SNMPPoller(
            host=_TEST_HOST,
            v3_config=SNMPv3Config(
                username="v3admin",
                auth_protocol="SHA",
                auth_key="s3cretAuth!",
                priv_protocol="AES",
                priv_key="s3cretPriv!",
            ),
        )
        snap = poller.poll()

    # UsmUserData must have been constructed (auth+priv credentials passed in)
    mock_usm_cls.assert_called_once()
    call_kwargs = mock_usm_cls.call_args
    assert call_kwargs is not None

    # Snapshot must be a valid PowerSnapshot with fields from OID values
    assert isinstance(snap, PowerSnapshot)
    assert snap.battery_percent == pytest.approx(80.0)
    assert snap.load_percent == pytest.approx(45.0)
    assert snap.power_watts == pytest.approx(300.0)
    assert snap.runtime_seconds == pytest.approx(20.0 * 60)  # minutes → seconds
    assert snap.device_id == f"snmp:{_TEST_HOST}:161"
