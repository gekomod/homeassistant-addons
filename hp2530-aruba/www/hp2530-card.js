/* HP 2530 Aruba dashboard card — port link and PoE overview. */
class HP2530Card extends HTMLElement {
  setConfig(config) { this.config = config || {}; }
  set hass(hass) { this._hass = hass; this.render(); }
  getCardSize() { return 10; }

  render() {
    if (!this._hass) return;
    const states = this._hass.states;
    const entities = Object.values(states).filter(function (s) {
      return s.entity_id.indexOf('sensor.hp2530_') === 0 ||
        s.entity_id.indexOf('binary_sensor.hp2530_') === 0 ||
        s.entity_id.indexOf('sensor.hp_2530_') === 0 ||
        s.entity_id.indexOf('binary_sensor.hp_2530_') === 0;
    });
    const find = function (part) { return entities.find(function (s) { return s.entity_id.indexOf(part) !== -1; }); };
    const desc = find('opis');
    const up = find('uptime');
    const active = find('porty_aktywne');
    const down = find('porty_nieaktywne');
    const esc = function (value) {
      return String(value == null ? '—' : value).replace(/[&<>"']/g, function (c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
      });
    };
    const ports = entities.filter(function (s) {
      return s.entity_id.indexOf('binary_sensor.') === 0 && s.entity_id.endsWith('_link');
    }).sort(function (a, b) {
      const ai = Number((a.attributes || {}).port_index || ((a.entity_id.match(/port_(\d+)/) || [])[1] || 999));
      const bi = Number((b.attributes || {}).port_index || ((b.entity_id.match(/port_(\d+)/) || [])[1] || 999));
      return ai - bi || a.entity_id.localeCompare(b.entity_id, undefined, {numeric:true});
    });
    const on = ports.filter(function (p) { return p.state === 'on'; }).length;
    const poeKnown = ports.filter(function (p) { return p.attributes && p.attributes.poe_supported_by_snmp; }).length;
    const poeEnabled = ports.filter(function (p) { return p.attributes && p.attributes.poe_enabled === true; }).length;
    const poeDelivering = ports.filter(function (p) { return p.attributes && p.attributes.poe_status_code === 3; }).length;
    const watts = ports.reduce(function (sum, p) { return sum + (Number((p.attributes || {}).poe_power_w) || 0); }, 0);
    const seconds = Number(up && up.state);
    const uptimeText = Number.isFinite(seconds) && seconds >= 0
      ? Math.floor(seconds / 86400) + ' d ' + Math.floor((seconds % 86400) / 3600) + ' h'
      : (up ? up.state : '—');

    const portMarkup = ports.length ? ports.map(function (p) {
      const a = p.attributes || {};
      const linkUp = p.state === 'on';
      const powered = a.poe_status_code === 3;
      const searching = a.poe_status_code === 2;
      const fault = a.poe_status_code === 4 || a.poe_status_code === 6;
      const poeClass = powered ? 'poe-powered' : searching ? 'poe-searching' : fault ? 'poe-fault' :
        a.poe_enabled === false ? 'poe-disabled' : a.poe_enabled === true ? 'poe-enabled' : 'poe-unknown';
      const poeLabel = powered ? 'ZASILA · ' + Number(a.poe_power_w || 0).toFixed(1) + ' W' :
        searching ? 'PoE · SZUKA' : fault ? 'PoE · BŁĄD' :
        a.poe_enabled === false ? 'PoE · OFF' : a.poe_enabled === true ? 'PoE · ON' : 'PoE · BRAK DANYCH';
      const speed = Number(a.speed_bps);
      const speedLabel = Number.isFinite(speed) && speed > 0
        ? (speed >= 1000000000 ? (speed / 1000000000) + ' Gb/s' : Math.round(speed / 1000000) + ' Mb/s')
        : '—';
      const name = a.port_alias || a.port_name || p.entity_id.replace(/^binary_sensor\./, '').replace(/_link$/, '');
      return '<div class="port ' + (linkUp ? 'up' : 'down') + '">' +
        '<div class="porttop"><span class="led"></span><span class="portname">' + esc(name) + '</span></div>' +
        '<div class="state">' + (linkUp ? 'LINK UP' : 'LINK DOWN') + ' · ' + esc(speedLabel) + '</div>' +
        '<div class="poe ' + poeClass + '">' + esc(poeLabel) + '</div>' +
        '<div class="state">' + esc(a.poe_status || 'Brak danych PoE') + '</div></div>';
    }).join('') : '<div class="stat">Statusy portów pojawią się po pierwszym odczycie SNMP.</div>';

    this.innerHTML = [
      '<style>',
      ':host{display:block;color:var(--primary-text-color)}',
      '.wrap{font-family:Arial,sans-serif;background:var(--ha-card-background,var(--card-background-color));border:1px solid var(--divider-color);border-radius:20px;overflow:hidden}',
      '.hero{padding:24px;background:linear-gradient(120deg,#071b35,#0d4770 65%,#00a6b2);color:white;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}',
      '.brand{font-size:12px;letter-spacing:2px;text-transform:uppercase;opacity:.8}.title{font-size:26px;font-weight:750;margin-top:5px}.subtitle{font-size:13px;opacity:.85;margin-top:6px}.chip{border:1px solid #ffffff55;background:#ffffff14;border-radius:999px;padding:8px 12px;font-size:12px}',
      '.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:16px}.stat{border:1px solid var(--divider-color);border-radius:14px;padding:14px;min-width:0}.label{font-size:12px;color:var(--secondary-text-color)}.value{font-size:23px;font-weight:700;margin-top:6px;overflow-wrap:anywhere}',
      '.section{padding:0 16px 16px}.section h3{font-size:15px;margin:4px 0 12px}.hint{font-size:12px;color:var(--secondary-text-color);margin:-4px 0 12px}.ports{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:8px}',
      '.port{border:1px solid var(--divider-color);border-radius:10px;padding:10px 7px;background:var(--secondary-background-color);min-width:0}.port.up{border-color:#18a66a;background:color-mix(in srgb,#18a66a 8%,var(--card-background-color))}.port.down{opacity:.78}',
      '.porttop{display:flex;align-items:center;gap:5px;min-width:0}.led{flex:0 0 8px;width:8px;height:8px;border-radius:50%;background:#9099a4}.up .led{background:#18a66a;box-shadow:0 0 8px #18a66a77}.portname{font-size:12px;font-weight:700;overflow-wrap:anywhere}',
      '.state{font-size:10px;color:var(--secondary-text-color);margin-top:6px;overflow-wrap:anywhere}.poe{font-size:10px;font-weight:750;border-radius:6px;padding:5px 4px;margin-top:8px;text-align:center;overflow-wrap:anywhere}',
      '.poe-powered{background:#18a66a22;color:var(--success-color,#168554);border:1px solid #18a66a66}.poe-enabled{background:#d49a1720;color:var(--warning-color,#a77700);border:1px solid #d49a1766}.poe-searching{background:#168bd21a;color:var(--info-color,#168bd2);border:1px solid #168bd266}.poe-disabled{background:#88888814;color:var(--secondary-text-color);border:1px solid var(--divider-color)}.poe-fault{background:#d9302520;color:var(--error-color,#d93025);border:1px solid #d9302566}.poe-unknown{background:var(--secondary-background-color);color:var(--secondary-text-color);border:1px dashed var(--divider-color)}',
      '.foot{padding:12px 16px;border-top:1px solid var(--divider-color);font-size:11px;color:var(--secondary-text-color);display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}',
      '@media(max-width:900px){.ports{grid-template-columns:repeat(6,minmax(0,1fr))}}@media(max-width:650px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.ports{grid-template-columns:repeat(3,minmax(0,1fr))}.title{font-size:22px}}',
      '</style>',
      '<div class="wrap"><div class="hero"><div><div class="brand">Aruba Networking · Switch management</div><div class="title">HP 2530 Aruba</div><div class="subtitle">' + esc(desc && desc.state || 'HP J9772A 2530-48G-PoEP') + ' · monitoring przez SNMP</div></div><div class="chip">● ' + esc(this.config.host || 'SWITCH_IP') + ' · SNMP v2c</div></div>',
      '<div class="stats">',
      '<div class="stat"><div class="label">Porty aktywne</div><div class="value">' + esc(active && active.state || on) + '</div></div>',
      '<div class="stat"><div class="label">Porty nieaktywne</div><div class="value">' + esc(down && down.state || '—') + '</div></div>',
      '<div class="stat"><div class="label">PoE włączone</div><div class="value">' + (poeKnown ? poeEnabled : '—') + '</div></div>',
      '<div class="stat"><div class="label">Urządzenia zasilane PoE</div><div class="value">' + (poeKnown ? poeDelivering : '—') + '</div></div>',
      '<div class="stat"><div class="label">Pobór mocy PoE</div><div class="value">' + (poeKnown ? watts.toFixed(1) + ' W' : '—') + '</div></div>',
      '<div class="stat"><div class="label">Czas pracy</div><div class="value">' + esc(uptimeText) + '</div></div></div>',
      '<div class="section"><h3>Mapa portów · link i PoE</h3><div class="hint">Zielony = podaje zasilanie · żółty = PoE włączone · szary = wyłączone lub brak danych.</div><div class="ports">' + portMarkup + '</div></div>',
      '<div class="foot"><span>SNMP · odświeżanie co 30 s · tylko odczyt</span><span>Odczyt PoE zależy od tabel SNMP udostępnianych przez firmware</span></div></div>'
    ].join('');
  }
}
customElements.define('hp2530-card', HP2530Card);
window.customCards = window.customCards || [];
window.customCards.push({type:'hp2530-card', name:'HP 2530 Aruba', description:'Panel HP/Aruba 2530 z mapą portów, linkiem i statusem PoE'});
