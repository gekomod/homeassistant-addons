"""Sensors for HP 2530 Aruba switch."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HPSystemSensor(coordinator, entry, "uptime", "Uptime", UnitOfTime.SECONDS, SensorDeviceClass.DURATION),
        HPSystemSensor(coordinator, entry, "interfaces_up", "Porty aktywne", None),
        HPSystemSensor(coordinator, entry, "interfaces_down", "Porty nieaktywne", None),
        HPSystemSensor(coordinator, entry, "interfaces_count", "Porty wykryte", None),
        HPSystemSensor(coordinator, entry, "description", "Opis", None),
        HPSystemSensor(coordinator, entry, "sysname", "Nazwa urządzenia", None),
    ]
    for idx, interface in coordinator.data.get("interfaces", {}).items():
        for key, label, unit in [
            ("speed_bps", "Prędkość", "bit/s"),
            ("in_octets", "RX bajty", "B"),
            ("out_octets", "TX bajty", "B"),
            ("in_errors", "Błędy RX", None),
            ("out_errors", "Błędy TX", None),
        ]:
            entities.append(HPPortSensor(coordinator, entry, idx, key, f"{interface['name']} {label}", unit))
        entities.append(HPPortSensor(coordinator, entry, idx, "poe_used", f"{interface['name']} PoE pobór", "mW"))
    async_add_entities(entities)


class HPBase(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, unique):
        super().__init__(coordinator)
        host = entry.data["host"]
        self._attr_unique_id = f"{host}_{unique}".replace(".", "_").replace("/", "_")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, host)},
            "name": entry.title,
            "manufacturer": "HP / Aruba",
            "model": "2530-48G-PoEP (J9772A)",
            "configuration_url": f"http://{host}",
        }


class HPSystemSensor(HPBase, SensorEntity):
    def __init__(self, coordinator, entry, key, label, unit, device_class=None):
        super().__init__(coordinator, entry, key)
        self.key = key
        self._attr_name = label
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.key)
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return value


class HPPortSensor(HPBase, SensorEntity):
    def __init__(self, coordinator, entry, idx, key, label, unit):
        super().__init__(coordinator, entry, f"port_{idx}_{key}")
        self.idx = idx
        self.key = key
        self._attr_name = label
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = (
            SensorStateClass.TOTAL_INCREASING
            if key in ("in_octets", "out_octets", "in_errors", "out_errors")
            else None
        )

    @property
    def native_value(self):
        interface = self.coordinator.data.get("interfaces", {}).get(self.idx, {})
        value = interface.get(self.key)
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None
