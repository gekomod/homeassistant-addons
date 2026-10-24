"""SNMP polling coordinator for HP/Aruba 2530 switches."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_VERSION, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"

IF_OIDS = {
    "descr": "1.3.6.1.2.1.2.2.1.2",
    "admin": "1.3.6.1.2.1.2.2.1.7",
    "oper": "1.3.6.1.2.1.2.2.1.8",
    "speed": "1.3.6.1.2.1.2.2.1.5",
    "in_octets": "1.3.6.1.2.1.2.2.1.10",
    "out_octets": "1.3.6.1.2.1.2.2.1.16",
    "in_errors": "1.3.6.1.2.1.2.2.1.14",
    "out_errors": "1.3.6.1.2.1.2.2.1.20",
    "alias": "1.3.6.1.2.1.31.1.1.1.18",
    "high_in_octets": "1.3.6.1.2.1.31.1.1.1.6",
    "high_out_octets": "1.3.6.1.2.1.31.1.1.1.10",
}
POE_OIDS = {
    "poe_admin": "1.3.6.1.2.1.105.1.1.1.3",
    "poe_detect": "1.3.6.1.2.1.105.1.1.1.6",
    "poe_used": "1.3.6.1.2.1.105.1.1.1.9",
}


def _value(line: str) -> str:
    if " = " not in line:
        return ""
    raw = line.split(" = ", 1)[1].strip()
    if raw.lower().startswith("timeticks:"):
        match = re.search(r"\((\d+)\)", raw)
        return str(int(match.group(1)) // 100) if match else ""
    raw = re.sub(r"^[A-Za-z][A-Za-z0-9 -]*:\s*", "", raw)
    return raw.strip().strip('"')


def _number(raw: str):
    """Extract numeric values, including SNMP enums like deliveringPower(3)."""
    if " = " in raw:
        raw = raw.split(" = ", 1)[1].strip()
    if raw.lower().startswith("timeticks:"):
        match = re.search(r"\((\d+)\)", raw)
        return int(match.group(1)) // 100 if match else None
    enum = re.search(r"\((-?\d+)\)\s*$", raw)
    if enum:
        return int(enum.group(1))
    match = re.search(
        r"(?:INTEGER|Gauge32|Counter32|Counter64|Gauge|Unsigned32):\s*(-?\d+)",
        raw, re.I,
    )
    if match:
        return int(match.group(1))
    match = re.search(r'(?:STRING|OCTET STRING):\s*"?(.+?)"?$', raw, re.I)
    return match.group(1).strip('"') if match else raw.strip().strip('"')

def _suffix(line: str, oid: str):
    left = line.split(" = ", 1)[0].strip().lstrip(".")
    prefix = oid.lstrip(".") + "."
    return left[len(prefix):] if left.startswith(prefix) else None


class HP2530Coordinator(DataUpdateCoordinator):
    """Fetch switch status using Net-SNMP command line utilities."""

    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        self.cfg = entry.data
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _snmp(self, oid: str, walk=False):
        cfg = self.cfg
        cmd = [
            "snmpwalk" if walk else "snmpget",
            "-On", "-t", "2", "-r", "0",
            "-v" + cfg.get(CONF_VERSION, "2c"),
            "-c", cfg["community"],
            f'{cfg[CONF_HOST]}:{cfg.get("port", DEFAULT_PORT)}',
            oid,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=5)
        except (OSError, asyncio.TimeoutError) as exc:
            raise UpdateFailed(f"SNMP command failed for {oid}: {exc}") from exc
        if proc.returncode != 0 and not out.strip():
            if walk:
                _LOGGER.debug("SNMP table unavailable for OID %s: %s", oid, err.decode(errors="replace").strip())
                return []
            raise UpdateFailed(f"SNMP query failed for {oid}: {err.decode(errors='replace').strip()}")
        return out.decode(errors="replace").splitlines()

    async def _async_update_data(self):
        try:
            desc_lines, uptime_lines, name_lines = await asyncio.gather(
                self._snmp(SYS_DESCR),
                self._snmp(SYS_UPTIME),
                self._snmp(SYS_NAME),
            )
            data = {
                "description": _value(desc_lines[0]) if desc_lines else "Unknown",
                "uptime": _number(uptime_lines[0]) if uptime_lines else None,
                "sysname": _value(name_lines[0]) if name_lines else "HP 2530",
                "interfaces": {},
                "poe": {},
            }
            all_oids = {**IF_OIDS, **POE_OIDS}
            tables = await asyncio.gather(
                *(self._snmp(oid, walk=True) for oid in all_oids.values())
            )
            parsed = {}
            for key, oid, lines in zip(all_oids.keys(), all_oids.values(), tables):
                parsed[key] = {}
                for line in lines:
                    idx = _suffix(line, oid)
                    if idx is not None:
                        if key in POE_OIDS:
                            idx = idx.split(".")[-1]
                        parsed[key][idx] = _number(_value(line))

            for idx, descr in parsed.get("descr", {}).items():
                name = str(descr)
                low = name.lower()
                if not (
                    low.startswith(("1/", "port", "ethernet", "gigabit", "eth"))
                    or re.fullmatch(r"\d+", name)
                ):
                    continue
                data["interfaces"][idx] = {
                    "index": int(idx) if idx.isdigit() else idx,
                    "name": name,
                    "alias": parsed.get("alias", {}).get(idx, ""),
                    "admin": parsed.get("admin", {}).get(idx),
                    "oper": parsed.get("oper", {}).get(idx),
                    "speed_bps": parsed.get("speed", {}).get(idx),
                    "in_octets": parsed.get("high_in_octets", {}).get(idx, parsed.get("in_octets", {}).get(idx)),
                    "out_octets": parsed.get("high_out_octets", {}).get(idx, parsed.get("out_octets", {}).get(idx)),
                    "in_errors": parsed.get("in_errors", {}).get(idx),
                    "out_errors": parsed.get("out_errors", {}).get(idx),
                    "poe_admin": parsed.get("poe_admin", {}).get(idx),
                    "poe_detect": parsed.get("poe_detect", {}).get(idx),
                    "poe_used": parsed.get("poe_used", {}).get(idx),
                }
            for key in POE_OIDS:
                data["poe"][key] = parsed.get(key, {})
            data["interfaces_count"] = len(data["interfaces"])
            data["interfaces_up"] = sum(
                1 for item in data["interfaces"].values() if str(item.get("oper")) == "1"
            )
            data["interfaces_down"] = sum(
                1 for item in data["interfaces"].values() if str(item.get("oper")) == "2"
            )
            return data
        except UpdateFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"Unable to update HP 2530 data: {exc}") from exc
