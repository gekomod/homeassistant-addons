# Home Assistant Add-ons by gekomod

Public collection of custom Home Assistant integrations, Lovelace cards, dashboards and automations.

## Add-ons

### HP 2530 Aruba
Custom integration and standalone dashboard for HP/Aruba 2530 switches, with SNMP system information, interface status, traffic counters and best-effort PoE telemetry.

- [Installation and configuration](hp2530-aruba/README.md)
- [Integration source](hp2530-aruba/custom_components/hp2530/)
- [Dashboard YAML](hp2530-aruba/hp2530-dashboard.yaml)
- [Lovelace card](hp2530-aruba/www/hp2530-card.js)

## Safety and privacy

- Never commit passwords, API tokens, private SNMP communities, personal IP addresses, or local configuration exports.
- Configure each device locally in Home Assistant.
- Use a read-only SNMP community.
- Public examples use documentation/reserved addresses or placeholders, not a user's real network configuration.

## Repository structure

Each add-on has its own directory and README. Changes are tracked through Git commits so updates can be reviewed and rolled back.
