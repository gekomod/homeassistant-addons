# HP 2530 Aruba for Home Assistant

Custom integration and standalone Lovelace dashboard for HP/Aruba 2530 switches.

## Features

- Device setup through Settings → Devices & services → Add integration.
- SNMP system description, system name and uptime.
- Discovery of physical interfaces, link status, speed, RX/TX counters and errors.
- Best-effort PoE status and power readings via POWER-ETHERNET-MIB.
- Separate Lovelace dashboard with a visual port map.
- Custom port names, editable from the port details dialog and saved in the browser.
- Polish and English interface, switchable from the card header.
- Read-only monitoring: no port, VLAN or PoE configuration is changed.

## Requirements

- Home Assistant with custom integrations enabled.
- Net-SNMP command-line utilities (snmpget and snmpwalk) available to the Home Assistant process.
- SNMP v1 or v2c enabled on the switch.
- A read-only SNMP community. Do not use an unrestricted/write community.

On Debian, install Net-SNMP tools if needed:

    sudo apt install snmp

## Install the integration

Copy the directory custom_components/hp2530 to:

    /home/homeassistant/.homeassistant/custom_components/hp2530

Adjust the destination to match your Home Assistant configuration directory. Ensure the Home Assistant service user can read the files.

Restart Home Assistant, then open Settings → Devices & services → Add integration → HP 2530 Aruba. Enter your switch IP address, read-only community, SNMP version and port. The public defaults are intentionally placeholders; use your own local settings.

## Install the dashboard card

Copy www/hp2530-card.js to the www directory under your Home Assistant configuration directory.

Register the resource under Settings → Dashboards → Resources:

- URL: /local/hp2530-card.js
- Type: JavaScript Module

## Add the dashboard

Copy hp2530-dashboard.yaml to the root of your Home Assistant configuration directory.

Merge the following into the existing top-level lovelace section in configuration.yaml (do not create a duplicate lovelace key):

    lovelace:
      dashboards:
        hp2530-dashboard:
          mode: yaml
          title: HP 2530 Aruba
          icon: mdi:ethernet
          show_in_sidebar: true
          filename: hp2530-dashboard.yaml

If the lovelace section already exists, add only the dashboards entry beneath it. Restart Home Assistant.

## SNMP and PoE notes

The integration uses standard SNMP interface tables and POWER-ETHERNET-MIB OIDs. The exact PoE values exposed by a switch depend on its firmware and MIB implementation. Missing values are shown as unavailable rather than guessed.

Interface indexes are discovered from SNMP and may not always match the physical port number printed on the switch. Confirm the reported interface names on your device.

## Security

- Use a read-only SNMP community.
- Do not publish your actual SNMP community, private IPs, passwords or configuration exports.
- This integration only reads telemetry; it does not issue switch configuration commands.
