"""Binary status sensors for HP 2530 interfaces and PoE."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

POE_DETECT_LABELS = {
    1: "Wyłączone",
    2: "Wyszukiwanie urządzenia",
    3: "Podaje zasilanie",
    4: "Błąd",
    5: "Test",
    6: "Inny błąd",
}


def _int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for idx, info in coordinator.data.get("interfaces", {}).items():
        entities.extend([
            HPPortStatus(coordinator, entry, idx, info["name"]),
            HPPoeEnabled(coordinator, entry, idx),
            HPPoeDelivering(coordinator, entry, idx),
        ])
    async_add_entities(entities)


class HPPortStatus(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry, idx, name):
        super().__init__(coordinator)
        self.idx = idx
        self._attr_name = f"{name} link"
        self._attr_unique_id = f"{entry.data['host'].replace('.', '_')}_port_{idx}_link"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": entry.title,
            "manufacturer": "HP / Aruba",
            "model": "2530-48G-PoEP (J9772A)",
        }

    @property
    def is_on(self):
        return str(self.coordinator.data.get("interfaces", {}).get(self.idx, {}).get("oper")) == "1"

    @property
    def extra_state_attributes(self):
        info = self.coordinator.data.get("interfaces", {}).get(self.idx, {})
        admin = _int(info.get("poe_admin"))
        detect = _int(info.get("poe_detect"))
        power = _int(info.get("poe_used"))
        return {
            "port_index": self.idx,
            "port_name": info.get("name"),
            "port_alias": info.get("alias") or None,
            "poe_supported_by_snmp": admin is not None or detect is not None or power is not None,
            "poe_enabled": True if admin == 1 else False if admin == 2 else None,
            "poe_status_code": detect,
            "poe_status": POE_DETECT_LABELS.get(detect, "Brak danych" if detect is None else f"Nieznany ({detect})"),
            "poe_power_mw": power,
            "poe_power_w": round(power / 1000, 2) if power is not None else None,
            "speed_bps": _int(info.get("speed_bps")),
            "rx_bytes": _int(info.get("in_octets")),
            "tx_bytes": _int(info.get("out_octets")),
            "rx_errors": _int(info.get("in_errors")),
            "tx_errors": _int(info.get("out_errors")),
        }

    @property
    def available(self):
        return super().available and self.idx in self.coordinator.data.get("interfaces", {})


class HPPoeEnabled(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, idx):
        super().__init__(coordinator)
        self.idx = idx
        self._attr_name = f"Port {idx} PoE włączone"
        self._attr_unique_id = f"{entry.data['host'].replace('.', '_')}_port_{idx}_poe_enabled"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": entry.title,
            "manufacturer": "HP / Aruba",
            "model": "2530-48G-PoEP (J9772A)",
        }

    @property
    def is_on(self):
        return _int(self.coordinator.data.get("interfaces", {}).get(self.idx, {}).get("poe_admin")) == 1

    @property
    def available(self):
        info = self.coordinator.data.get("interfaces", {}).get(self.idx, {})
        return super().available and _int(info.get("poe_admin")) is not None


class HPPoeDelivering(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, idx):
        super().__init__(coordinator)
        self.idx = idx
        self._attr_name = f"Port {idx} PoE podaje zasilanie"
        self._attr_unique_id = f"{entry.data['host'].replace('.', '_')}_port_{idx}_poe_delivering"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": entry.title,
            "manufacturer": "HP / Aruba",
            "model": "2530-48G-PoEP (J9772A)",
        }

    @property
    def is_on(self):
        return _int(self.coordinator.data.get("interfaces", {}).get(self.idx, {}).get("poe_detect")) == 3

    @property
    def available(self):
        info = self.coordinator.data.get("interfaces", {}).get(self.idx, {})
        return super().available and _int(info.get("poe_detect")) is not None
