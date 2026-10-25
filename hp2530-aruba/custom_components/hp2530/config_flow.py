"""Config flow for HP 2530 Aruba switches."""
from __future__ import annotations

import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN, CONF_VERSION, DEFAULT_PORT


def _schema(defaults=None):
    defaults = defaults or {}
    return vol.Schema({
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "HP 2530 Aruba")): str,
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "192.0.2.1")): str,
        vol.Required("community", default=defaults.get("community", "CHANGE_ME")): str,
        vol.Required(CONF_VERSION, default=defaults.get(CONF_VERSION, "2c")): vol.In(["1", "2c"]),
        vol.Optional("port", default=defaults.get("port", DEFAULT_PORT)): vol.All(int, vol.Range(min=1, max=65535)),
    })


class CannotConnect(HomeAssistantError):
    """Unable to communicate with switch over SNMP."""


async def _test_connection(data):
    cmd = [
        "snmpget", "-On", "-t", "2", "-r", "0",
        "-v" + data[CONF_VERSION], "-c", data["community"],
        f'{data[CONF_HOST]}:{data.get("port", DEFAULT_PORT)}',
        "1.3.6.1.2.1.1.1.0",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    except (OSError, asyncio.TimeoutError) as exc:
        raise CannotConnect from exc
    if proc.returncode != 0 or not out.strip() or b"No Such" in out or b"Timeout" in out:
        raise CannotConnect


class HP2530OptionsFlow(config_entries.OptionsFlow):
    """Configure optional SNMP write access for setting port aliases."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "write_community",
                    default=self.config_entry.options.get(
                        "write_community",
                        self.config_entry.data.get("write_community", ""),
                    ),
                ): str,
            }),
            description_placeholders={
                "hint": "Optional. Required only to write port aliases to the switch. Leave empty for read-only monitoring."
            },
        )


class HP2530ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return HP2530OptionsFlow()


    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            await self.async_set_unique_id(user_input[CONF_HOST].lower())
            self._abort_if_unique_id_configured()
            try:
                await _test_connection(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )
