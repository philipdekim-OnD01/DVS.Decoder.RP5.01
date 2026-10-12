'use strict';

const W = 960;
const H = 720;
const RECORD_BYTES = 13; // <HHBQ: x, y, polarity, timestamp_us
const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d', {alpha: false});
const $ = selector => document.querySelector(selector);
const $$ = selector => document.querySelectorAll(selector);
const value = id => $(id).value;

const lastOn = new Float64Array(W * H);
const lastOff = new Float64Array(W * H);
const activePixels = new Set();
const hotCounts = new Map();
const hotBlockedUntil = new Map();

let ws = null;
let manualClose = false;
let retryTimer = null;
let paused = false;
let pausedAt = 0;
let total = 0;
let localInvalidX = 0;
let localInvalidY = 0;
let wireErrors = 0;
let renderFrames = 0;
let renderedPoints = 0;
let lastFpsAt = performance.now();
let lastDrawAt = 0;
let demoPhase = 0;
let hotWindowStarted = performance.now();
let serverAnchorUs = null;
let clientAnchorMs = null;
let roi = {x0: 0, x1: 959, y0: 0, y1: 719};
let raw2Image = null;
let raw2Active = 0;

$('#wsUrl').value = `ws://${location.hostname || 'localhost'}:8765`;

function setStatus(name, text, state = '') {
  $(`#${name}Text`).textContent = text;
  $(`#${name}Dot`).className = `dot ${state}`;
}

function number(value, digits = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString(undefined, {maximumFractionDigits: digits}) : '--';
}

function color(hex) {
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}

function clearSurface() {
  lastOn.fill(0);
  lastOff.fill(0);
  activePixels.clear();
  hotCounts.clear();
  hotBlockedUntil.clear();
  raw2Image = null;
  raw2Active = 0;
  ctx.fillStyle = value('#bgColor');
  ctx.fillRect(0, 0, W, H);
}

function eventClientTime(timestampUs, arrivalMs) {
  if (!Number.isFinite(timestampUs) || timestampUs <= 0) return arrivalMs;
  if (serverAnchorUs === null) {
    serverAnchorUs = timestampUs;
    clientAnchorMs = arrivalMs;
    return arrivalMs;
  }
  let projected = clientAnchorMs + (timestampUs - serverAnchorUs) / 1000;
  if (timestampUs < serverAnchorUs || Math.abs(projected - arrivalMs) > 2000) {
    serverAnchorUs = timestampUs;
    clientAnchorMs = arrivalMs;
    projected = arrivalMs;
  }
  return Math.min(arrivalMs + 20, projected);
}

function hotPixelAllows(index, now) {
  if (!$('#hotPixel').checked) return true;
  if (now - hotWindowStarted >= 1000) {
    hotCounts.clear();
    hotWindowStarted = now;
  }
  if ((hotBlockedUntil.get(index) || 0) > now) return false;
  const count = (hotCounts.get(index) || 0) + 1;
  hotCounts.set(index, count);
  if (count > Number(value('#hotThreshold'))) {
    hotBlockedUntil.set(index, now + 2000);
    return false;
  }
  return true;
}

function acceptEvent(x, y, polarity, timestampUs, arrivalMs) {
  total++;
  if (paused) return;
  if (x < 0 || x >= W) { localInvalidX++; return; }
  if (y < 0 || y >= H) { localInvalidY++; return; }
  if (polarity !== 0 && polarity !== 1) { wireErrors++; return; }
  if (x < roi.x0 || x > roi.x1 || y < roi.y0 || y > roi.y1) return;
  const subsample = Number(value('#subsample'));
  if (subsample > 1 && (x % subsample || y % subsample)) return;
  const index = y * W + x;
  if (!hotPixelAllows(index, arrivalMs)) return;
  const t = eventClientTime(timestampUs, arrivalMs);
  if (polarity === 0) lastOn[index] = t;
  else lastOff[index] = t;
  activePixels.add(index);
}

function decodeBinary(buffer) {
  const view = new DataView(buffer);
  if (view.byteLength === 24 + W * H / 4 &&
      view.getUint8(0) === 0x52 && view.getUint8(1) === 0x32 &&
      view.getUint8(2) === 0x46 && view.getUint8(3) === 0x31) {
    const onCount = view.getUint32(4, true);
    const offCount = view.getUint32(8, true);
    const arrival = performance.now();
    const timestampUs = Number(view.getBigUint64(16, true));
    let pixel = 0;
    for (let offset = 24; offset < view.byteLength; offset++) {
      const packed = view.getUint8(offset);
      if (packed === 0) { pixel += 4; continue; }
      for (let shift = 6; shift >= 0; shift -= 2) {
        const code = (packed >> shift) & 3;
        const index = pixel++;
        if (code === 1 || code === 2)
          acceptEvent(index % W, Math.floor(index / W), code - 1, timestampUs, arrival);
      }
    }
    raw2Image = null;
    return;
  }
  if (view.byteLength % RECORD_BYTES !== 0) wireErrors++;
  const arrival = performance.now();
  for (let offset = 0; offset + RECORD_BYTES <= view.byteLength; offset += RECORD_BYTES) {
    const x = view.getUint16(offset, true);
    const y = view.getUint16(offset + 2, true);
    const polarity = view.getUint8(offset + 4);
    const timestampUs = Number(view.getBigUint64(offset + 5, true));
    acceptEvent(x, y, polarity, timestampUs, arrival);
  }
}

function applyStats(stats) {
  $('#eps').textContent = number(stats.events_per_s);
  $('#onEvents').textContent = number(stats.on_events);
  $('#offEvents').textContent = number(stats.off_events);
  $('#captureFps').textContent = number(stats.capture_fps, 1);
  $('#rawRate').textContent = number(stats.raw_bytes_per_sec);
  $('#sequence').textContent = stats.v4l2_sequence ?? '--';
  $('#latestTs').textContent = stats.latest_event_timestamp_us ?? '--';
  $('#validationIssues').textContent = number(stats.validation_issues_sec ?? stats.invalid_events_sec ?? stats.parser_errors);
  $('#padPackets').textContent = number(stats.pad_packets_sec);
  $('#imuDataPackets').textContent = number(stats.imu_data_packets_sec);
  $('#imuTimestampPackets').textContent = number(stats.imu_timestamp_packets_sec);
  $('#unknownPackets').textContent = number(stats.truly_unknown_packets_sec);
  $('#unknownPercent').textContent = `${number(stats.truly_unknown_percent, 2)}%`;
  $('#invalid').textContent = `${number(stats.invalid_x)} / ${number(stats.invalid_y)}`;
  $('#uptime').textContent = number(stats.uptime_s, 1);
  $('#clients').textContent = number(stats.websocket_clients);
  $('#batches').textContent = number(stats.websocket_batches);
  $('#wsBytes').textContent = number(stats.websocket_bytes);
  $('#dropped').textContent = number((stats.dropped_events || 0) + (stats.dropped_websocket_batches || 0));
  $('#socketErrors').textContent = number((stats.socket_receive_errors || 0) + wireErrors);
  $('#latency').textContent = stats.latency_median_ms == null ? '--' : `${stats.latency_median_ms} / ${stats.latency_p95_ms}`;
  $('#dataType').textContent = stats.data_type || '--';
  const mhz = stats.link_freq_hz ? `${stats.link_freq_hz / 1e6} MHz` : 'link unknown';
  $('#mipiMode').textContent = `${mhz} · 4-lane · ${stats.mipi_mode || '--'}`;
  $('#timestampSource').textContent = stats.timestamp_source || '--';
  $('#timestampSource').title = stats.timestamp_source || '';
  const ipcState = stats.ipc_status === 'connected' ? 'on' : stats.ipc_status === 'idle' ? 'idle' : 'bad';
  setStatus('ipc', `DVS capture ${stats.producer_status || 'unknown'} / IPC ${stats.ipc_status || 'unknown'}`, ipcState);
  setStatus('i2c', `Register ${stats.i2c_status || 'unknown'}`, stats.i2c_status === 'available' ? 'on' : stats.i2c_status === 'unavailable' ? 'bad' : '');
}

function setRegisterBits(bits) {
  $$('#regBits input').forEach(input => { input.checked = Boolean(bits[input.dataset.bit]); });
}

function textMessage(text) {
  try {
    const message = JSON.parse(text);
    if (message.type === 'stats') applyStats(message);
    else if (message.type === 'reg_read') {
      setRegisterBits(message.bits || {});
      $('#regValue').value = message.value;
      $('#regMsg').textContent = `${message.address} = ${message.value}`;
      setStatus('i2c', 'Register available', 'on');
    } else if (message.type === 'reg_write_result') {
      setRegisterBits(message.bits || {});
      $('#regValue').value = message.readback;
      $('#regMsg').textContent = `${message.bit}: ${message.old} → ${message.written}, readback ${message.readback}`;
      setStatus('i2c', 'Register available', 'on');
    } else if (message.type === 'error') {
      $('#regMsg').textContent = message.message;
      setStatus('i2c', 'Register unavailable', 'bad');
    }
  } catch (error) {
    wireErrors++;
  }
}

function connect() {
  manualClose = false;
  clearTimeout(retryTimer);
  if (value('#transport') === 'demo') {
    setStatus('ws', 'Synthetic demo', 'idle');
    return;
  }
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;
  ws = new WebSocket(value('#wsUrl'));
  ws.binaryType = 'arraybuffer';
  ws.onopen = () => setStatus('ws', 'Backend connected', 'on');
  ws.onmessage = event => typeof event.data === 'string' ? textMessage(event.data) : decodeBinary(event.data);
  ws.onerror = () => setStatus('ws', 'Backend error', 'bad');
  ws.onclose = () => {
    setStatus('ws', 'Backend disconnected', 'bad');
    if (!manualClose) retryTimer = setTimeout(connect, 1500);
  };
}

function synthetic(now) {
  demoPhase += 0.035;
  const phase = Math.floor(demoPhase / 8) % 4;
  const polarity = Math.floor(demoPhase * 2) & 1;
  if (phase === 0) {
    const x = Math.round(480 + Math.sin(demoPhase) * 350);
    for (let y = 40; y < 680; y += 3) acceptEvent(x, y, polarity, 0, now);
  } else if (phase === 1) {
    const cx = Math.round(480 + Math.sin(demoPhase) * 220), cy = 360, r = 100;
    for (let d = -r; d <= r; d += 3) {
      acceptEvent(cx + d, cy - r, polarity, 0, now); acceptEvent(cx + d, cy + r, polarity, 0, now);
      acceptEvent(cx - r, cy + d, 1 - polarity, 0, now); acceptEvent(cx + r, cy + d, 1 - polarity, 0, now);
    }
  } else if (phase === 2) {
    const cx = 480 + Math.sin(demoPhase) * 160, cy = 360, r = 130;
    for (let a = 0; a < Math.PI * 2; a += 0.02) acceptEvent(Math.round(cx + Math.cos(a) * r), Math.round(cy + Math.sin(a) * r), polarity, 0, now);
  } else {
    const x = Math.round(480 + Math.sin(demoPhase * 1.5) * 300);
    for (let y = 80; y < 640; y += 2) acceptEvent(x, y, y & 1, 0, now);
  }
}

function newestAt(index) {
  return Math.max(lastOn[index], lastOff[index]);
}

function hasRecentNeighbor(index, now, windowMs) {
  const x = index % W;
  const y = Math.floor(index / W);
  for (let dy = -1; dy <= 1; dy++) {
    const ny = y + dy;
    if (ny < 0 || ny >= H) continue;
    for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue;
      const nx = x + dx;
      if (nx < 0 || nx >= W) continue;
      const t = newestAt(ny * W + nx);
      if (t > 0 && now - t <= windowMs) return true;
    }
  }
  return false;
}

function intensity(timestamp, now, mode, lifetime, accumulation, tau) {
  if (!timestamp) return 0;
  const age = Math.max(0, now - timestamp);
  if (mode === 'dot') return age <= lifetime ? 1 : 0;
  if (mode === 'accumulation') return age <= accumulation ? 1 : 0;
  const result = Math.exp(-age / tau);
  return result >= 0.015 ? result : 0;
}

function draw(now) {
  requestAnimationFrame(draw);
  const targetMs = 1000 / Number(value('#fps'));
  if (now - lastDrawAt < targetMs) return;
  lastDrawAt = now;
  const clock = paused ? pausedAt : now;
  if (!paused && value('#transport') === 'demo') synthetic(clock);
  if (raw2Image) {
    if (!paused) ctx.putImageData(raw2Image, 0, 0);
    renderedPoints += raw2Active;
    renderFrames++;
    $('#total').textContent = number(total);
    $('#active').textContent = number(raw2Active);
    if (now - lastFpsAt >= 1000) {
      const elapsed = (now - lastFpsAt) / 1000;
      $('#renderFps').textContent = (renderFrames / elapsed).toFixed(1);
      $('#renderedEps').textContent = number(renderedPoints / elapsed);
      renderFrames = 0;
      renderedPoints = 0;
      lastFpsAt = now;
    }
    return;
  }

  const mode = value('#viewMode');
  const lifetime = Number(value('#persistence'));
  const accumulation = Number(value('#accumulation'));
  const tau = Number(value('#tau'));
  const gain = Number(value('#gain')) / 100;
  const pointSize = $('#dilation').checked ? Math.max(3, Number(value('#pointSize'))) : Number(value('#pointSize'));
  const polarityMode = value('#polarity');
  const flipX = $('#flipX').checked;
  const flipY = $('#flipY').checked;
  const onColor = color(value('#onColor'));
  const offColor = color(value('#offColor'));
  const bg = color(value('#bgColor'));

  ctx.fillStyle = value('#bgColor');
  ctx.fillRect(0, 0, W, H);
  let drawn = 0;
  for (const index of activePixels) {
    let on = intensity(lastOn[index], clock, mode, lifetime, accumulation, tau);
    let off = intensity(lastOff[index], clock, mode, lifetime, accumulation, tau);
    if (polarityMode === 'on') off = 0;
    if (polarityMode === 'off') on = 0;
    on = Math.min(1, on * gain);
    off = Math.min(1, off * gain);
    if (!on && !off) {
      const expiry = mode === 'dot' ? lifetime : mode === 'accumulation' ? accumulation : tau * 6;
      if (clock - newestAt(index) > expiry) activePixels.delete(index);
      continue;
    }
    if ($('#noise').checked && !hasRecentNeighbor(index, clock, 25)) continue;
    const sum = on + off;
    if (sum > 1) { on /= sum; off /= sum; }
    const base = Math.max(0, 1 - on - off);
    const r = Math.round(bg.r * base + onColor.r * on + offColor.r * off);
    const g = Math.round(bg.g * base + onColor.g * on + offColor.g * off);
    const b = Math.round(bg.b * base + onColor.b * on + offColor.b * off);
    let x = index % W;
    let y = Math.floor(index / W);
    if (flipX) x = W - 1 - x;
    if (flipY) y = H - 1 - y;
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(x, y, pointSize, pointSize);
    drawn++;
  }

  renderedPoints += drawn;
  renderFrames++;
  $('#total').textContent = number(total);
  $('#active').textContent = number(activePixels.size);
  if (now - lastFpsAt >= 1000) {
    const elapsed = (now - lastFpsAt) / 1000;
    $('#renderFps').textContent = (renderFrames / elapsed).toFixed(1);
    $('#renderedEps').textContent = number(renderedPoints / elapsed);
    renderFrames = 0;
    renderedPoints = 0;
    lastFpsAt = now;
  }
}

function send(message) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    $('#regMsg').textContent = 'Backend is not connected.';
    return false;
  }
  ws.send(JSON.stringify(message));
  return true;
}

$('#connect').onclick = connect;
$('#disconnect').onclick = () => { manualClose = true; clearTimeout(retryTimer); if (ws) ws.close(); };
$('#transport').onchange = () => {
  clearSurface();
  if (value('#transport') === 'websocket') connect();
  else { manualClose = true; if (ws) ws.close(); setStatus('ws', 'Synthetic demo', 'idle'); }
};
$('#clear').onclick = clearSurface;
$('#pause').onclick = () => {
  if (!paused) {
    paused = true;
    pausedAt = performance.now();
    $('#pause').textContent = 'Resume';
  } else {
    const shift = performance.now() - pausedAt;
    for (const index of activePixels) {
      if (lastOn[index]) lastOn[index] += shift;
      if (lastOff[index]) lastOff[index] += shift;
    }
    paused = false;
    $('#pause').textContent = 'Pause';
  }
};
$('#full').onclick = () => $('.canvaswrap').requestFullscreen?.();
$('#save').onclick = () => { const link = document.createElement('a'); link.download = 's5krc1s_dvs.png'; link.href = canvas.toDataURL('image/png'); link.click(); };
$('#persistence').oninput = event => { $('#persistLabel').textContent = `${event.target.value} ms`; };
$('#tau').oninput = event => { $('#tauLabel').textContent = `${event.target.value} ms`; };
$('#pointSize').oninput = event => { $('#pointLabel').textContent = `${event.target.value} px`; };
$('#gain').oninput = event => { $('#gainLabel').textContent = `${(event.target.value / 100).toFixed(2)}×`; };
$('#viewMode').onchange = () => {
  $('#accumulation').disabled = value('#viewMode') !== 'accumulation';
  $('#tau').disabled = value('#viewMode') !== 'time';
  $('#persistence').disabled = value('#viewMode') !== 'dot';
};
$('#applyRoi').onclick = () => {
  const next = {x0: Number(value('#x0')), x1: Number(value('#x1')), y0: Number(value('#y0')), y1: Number(value('#y1'))};
  if (next.x0 < 0 || next.x1 >= W || next.y0 < 0 || next.y1 >= H || next.x0 > next.x1 || next.y0 > next.y1) return alert('Invalid Display ROI');
  roi = next;
  clearSurface();
};
$('#read392c').onclick = () => send({type: 'reg_read', address: '0x392C'});
$$('#regBits input').forEach(input => {
  input.onchange = () => {
    if (!send({type: 'reg_update_bit', address: '0x392C', bit: input.dataset.bit, enabled: input.checked})) input.checked = !input.checked;
    else $('#regMsg').textContent = `Updating ${input.dataset.bit}; waiting for readback...`;
  };
});

window.addEventListener('beforeunload', () => { manualClose = true; if (ws) ws.close(); });
$('#viewMode').onchange();
// Hand contour preset: full resolution, short decay and no thickening.
$('#viewMode').value = 'time';
$('#tau').value = '25';
$('#accumulation').value = '35';
$('#pointSize').value = '1';
$('#gain').value = '125';
$('#noise').checked = true;
$('#dilation').checked = false;
$('#subsample').value = '1';
$('#tauLabel').textContent = '25 ms';
$('#gainLabel').textContent = '1.25×';
$('#viewMode').onchange();
clearSurface();
requestAnimationFrame(draw);
connect();
