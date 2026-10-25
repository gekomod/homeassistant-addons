"""HP 2530 Aruba switch integration using Net-SNMP command-line tools."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol
from .const import DOMAIN, PLATFORMS
from .coordinator import HP2530Coordinator


async def _async_set_port_name(hass: HomeAssistant, call: ServiceCall) -> None:
    """Persist a port alias on the Aruba switch through SNMP SET."""
    host = str(call.data["host"]).strip().lower()
    port_index = str(call.data["port_index"]).strip()
    name = str(call.data.get("name", "")).strip()
    if not port_index.isdigit():
        raise HomeAssistantError("port_index must be a numeric SNMP interface index.")
    coordinator = next(
        (
            item for item in hass.data.get(DOMAIN, {}).values()
            if str(item.cfg.get("host", "")).strip().lower() == host
        ),
        None,
    )
    if coordinator is None:
        raise HomeAssistantError(
            f"No configured HP 2530 integration matches host {host!r}. "
            "Check the host field in the Lovelace card configuration."
        )
    try:
        await coordinator.async_set_port_alias(port_index, name)
    except (ValueError, RuntimeError) as exc:
        raise HomeAssistantError(str(exc)) from exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not hass.services.has_service(DOMAIN, "set_port_name"):
        hass.services.async_register(
            DOMAIN,
            "set_port_name",
            lambda call: _async_set_port_name(hass, call),
            schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("port_index"): str,
                vol.Required("name"): str,
            }),
        )
    coordinator = HP2530Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
