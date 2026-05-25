"""Tests for device_registry, shared_state, alert_provider_factory, and exporter_registry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from src import shared_state
from src.services.alert_manager import AlertManager


# ===========================================================================
# shared_state
# ===========================================================================


def test_set_and_get_alert_manager() -> None:
    mgr = AlertManager()
    shared_state.set_alert_manager(mgr)
    assert shared_state.get_alert_manager() is mgr


def test_get_alert_manager_returns_none_by_default() -> None:
    shared_state.set_alert_manager(None)  # type: ignore[arg-type]
    assert shared_state.get_alert_manager() is None


def test_set_and_get_last_diagnostics() -> None:
    data = {"last_snapshot": {"device_id": "dev-1"}, "events": []}
    shared_state.set_last_diagnostics(data)
    result = shared_state.get_last_diagnostics()
    assert result["last_snapshot"]["device_id"] == "dev-1"


def test_get_last_diagnostics_returns_copy() -> None:
    data = {"foo": "bar"}
    shared_state.set_last_diagnostics(data)
    result = shared_state.get_last_diagnostics()
    result["foo"] = "mutated"
    assert shared_state.get_last_diagnostics()["foo"] == "bar"


# ===========================================================================
# device_registry
# ===========================================================================


class TestDeviceRegistry:
    def test_load_devices_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        from src.services import device_registry

        with patch.object(
            device_registry, "_DEVICES_FILE", str(tmp_path / "devices.json")
        ):
            devices = device_registry.load_devices()
        assert devices == []

    def test_save_and_load_devices(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        device = {"id": "nut:ups@localhost", "type": "ups", "host": "localhost"}
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.save_devices([device])
            loaded = device_registry.load_devices()
        assert loaded[0]["id"] == "nut:ups@localhost"

    def test_upsert_inserts_new_device(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        device = {"id": "dev-1", "type": "ups"}
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device(device)
            devices = device_registry.load_devices()
        assert any(d["id"] == "dev-1" for d in devices)

    def test_upsert_updates_existing_device(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device(
                {"id": "dev-1", "type": "ups", "model": "old"}
            )
            device_registry.upsert_device({"id": "dev-1", "model": "new"})
            devices = device_registry.load_devices()
        dev = next(d for d in devices if d["id"] == "dev-1")
        assert dev["model"] == "new"

    def test_upsert_preserves_existing_fields_when_update_is_none(
        self, tmp_path: Path
    ) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device({"id": "dev-1", "serial": "SN-123"})
            device_registry.upsert_device(
                {"id": "dev-1", "serial": None}
            )  # None should not overwrite
            devices = device_registry.load_devices()
        dev = next(d for d in devices if d["id"] == "dev-1")
        assert dev["serial"] == "SN-123"

    def test_get_device_returns_device_by_id(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device({"id": "dev-1", "type": "ups"})
            device = device_registry.get_device("dev-1")
        assert device is not None
        assert device["id"] == "dev-1"

    def test_get_device_returns_none_for_unknown_id(self, tmp_path: Path) -> None:
        from src.services import device_registry

        with patch.object(
            device_registry, "_DEVICES_FILE", str(tmp_path / "devices.json")
        ):
            result = device_registry.get_device("does-not-exist")
        assert result is None

    def test_remove_device_removes_by_id(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device({"id": "dev-1"})
            removed = device_registry.remove_device("dev-1")
            devices = device_registry.load_devices()
        assert removed is True
        assert not any(d["id"] == "dev-1" for d in devices)

    def test_remove_device_returns_false_when_not_found(self, tmp_path: Path) -> None:
        from src.services import device_registry

        with patch.object(
            device_registry, "_DEVICES_FILE", str(tmp_path / "devices.json")
        ):
            result = device_registry.remove_device("does-not-exist")
        assert result is False

    def test_load_devices_resets_on_corrupt_json(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = tmp_path / "devices.json"
        path.write_text("NOT JSON {{", encoding="utf-8")
        with patch.object(device_registry, "_DEVICES_FILE", str(path)):
            result = device_registry.load_devices()
        assert result == []

    def test_multiple_devices_saved_and_loaded(self, tmp_path: Path) -> None:
        from src.services import device_registry

        path = str(tmp_path / "devices.json")
        with patch.object(device_registry, "_DEVICES_FILE", path):
            device_registry.upsert_device({"id": "dev-a"})
            device_registry.upsert_device({"id": "dev-b"})
            device_registry.upsert_device({"id": "dev-c"})
            devices = device_registry.load_devices()
        assert len(devices) == 3


# ===========================================================================
# exporter_registry
# ===========================================================================


def test_exporter_registry_contains_sqlite() -> None:
    from src.exporter_registry import EXPORTER_REGISTRY

    assert "sqlite" in EXPORTER_REGISTRY


def test_exporter_registry_sqlite_factory_returns_exporter() -> None:
    from src.exporter_registry import EXPORTER_REGISTRY

    factory = EXPORTER_REGISTRY["sqlite"]
    exporter = factory()
    assert exporter is not None


def test_exporter_registry_all_known_exporters_present() -> None:
    from src.exporter_registry import EXPORTER_REGISTRY

    for name in ("sqlite", "prometheus", "influxdb", "loki", "csv", "energy"):
        assert name in EXPORTER_REGISTRY, f"Missing exporter: {name}"


# ===========================================================================
# alert_provider_factory
# ===========================================================================


class TestAlertProviderFactory:
    def test_register_webhook_provider_when_url_set(self) -> None:
        from src.services.alert_provider_factory import register_webhook_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value",
            return_value="https://hooks.example.com",
        ):
            register_webhook_provider(mgr)
        assert len(mgr._providers) == 1

    def test_skip_webhook_when_no_url(self) -> None:
        from src.services.alert_provider_factory import register_webhook_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value", return_value=""
        ):
            register_webhook_provider(mgr)
        assert len(mgr._providers) == 0

    def test_register_gotify_when_url_and_token_set(self) -> None:
        from src.services.alert_provider_factory import register_gotify_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value",
            side_effect=["https://gotify.example.com", "mytoken"],
        ):
            register_gotify_provider(mgr)
        assert len(mgr._providers) == 1

    def test_skip_gotify_when_no_token(self) -> None:
        from src.services.alert_provider_factory import register_gotify_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value",
            side_effect=["https://gotify.example.com", ""],
        ):
            register_gotify_provider(mgr)
        assert len(mgr._providers) == 0

    def test_register_ntfy_when_url_and_topic_set(self) -> None:
        from src.services.alert_provider_factory import register_ntfy_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value",
            side_effect=["https://ntfy.sh", "argus"],
        ):
            register_ntfy_provider(mgr)
        assert len(mgr._providers) == 1

    def test_register_apprise_when_url_set(self) -> None:
        from src.services.alert_provider_factory import register_apprise_provider

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value",
            return_value="https://apprise.example.com",
        ):
            register_apprise_provider(mgr)
        assert len(mgr._providers) == 1

    def test_register_all_providers_calls_all_four(self) -> None:
        from src.services.alert_provider_factory import register_all_providers

        mgr = AlertManager()
        with patch(
            "src.services.alert_provider_factory._get_config_value", return_value=""
        ):
            register_all_providers(mgr)
        # No providers should be registered when all URLs are empty
        assert len(mgr._providers) == 0
