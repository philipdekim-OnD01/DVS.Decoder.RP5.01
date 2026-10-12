#!/usr/bin/env bash
set -Eeuo pipefail

RUN=/home/philip/dvs_raw2_production
BACKUP="$RUN/backup"
APP=/home/philip/dvs_web_app
PRODUCER="$RUN/raw2_producer"
METRICS=/tmp/dvs_web_metrics.json
IPC_SOCKET=/tmp/dvs_reference_b3.sock
SETFILE=/home/philip/bin/Delta_10_2000FPS.txt
WIDTH=8192
HEIGHT=128
HTTP_PORT=8082
WS_PORT=8765
backend_pid=
producer_pid=

mkdir -p "$RUN/logs"
exec >>"$RUN/logs/raw2-live-supervisor.log" 2>&1

cleanup_on_exit() {
  local rc=$?
  trap - EXIT INT TERM
  [[ -n "$producer_pid" ]] && kill "$producer_pid" >/dev/null 2>&1 || true
  [[ -n "$backend_pid" ]] && kill "$backend_pid" >/dev/null 2>&1 || true
  [[ -n "$producer_pid" ]] && wait "$producer_pid" >/dev/null 2>&1 || true
  [[ -n "$backend_pid" ]] && wait "$backend_pid" >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup_on_exit EXIT INT TERM

read_reg_value() {
  local reg="${1^^}"
  i2ctransfer -f -y 10 w2@0x10 "0x${reg:0:2}" "0x${reg:2:2}" r1
}
read_reg() { local reg="${1^^}"; printf '%s %s\n' "$reg" "$(read_reg_value "$reg")"; }
write_reg() {
  local reg="${1^^}" value="$2"
  i2ctransfer -f -y 10 w3@0x10 "0x${reg:0:2}" "0x${reg:2:2}" "$value" >/dev/null
}
saved_reg() { awk -v r="${1^^}" '$1 == r {print $2; exit}' "$BACKUP/sensor_registers_before_key.txt"; }
find_rp1_media() {
  local media
  for media in /dev/media*; do
    media-ctl -d "$media" -p 2>/dev/null | grep -q 'driver[[:space:]]*rp1-cfe' && { echo "$media"; return 0; }
  done
  return 1
}
find_video() {
  media-ctl -d "$1" -p 2>/dev/null | awk '/entity .*rp1-cfe-csi2_ch0/ {found=1} found && /device node name/ {print $4; exit}'
}

[[ "$(id -u)" -eq 0 ]]
cat /proc/sys/kernel/random/boot_id >"$RUN/raw2_boot_id.txt"
echo "RAW2 production boot $(date -Ins)"
if [[ -e "$RUN/pending_first_boot_validation" ]]; then
  systemd-run --unit=raw2-production-firstboot-expiry --on-active=4min \
    "$RUN/raw2_production_rollback.sh" first-boot-health-timeout >/dev/null
fi

KERNEL="$(uname -r)"
[[ "$KERNEL" == 6.12.47+rpt-rpi-2712 ]]
[[ "$(/usr/sbin/modinfo -n rp1_cfe)" == "/lib/modules/$KERNEL/updates/rp1-cfe.ko" ]]
grep -qx Y /sys/module/rp1_cfe/parameters/diag_stride_zero
grep -qx 1 /sys/module/rp1_cfe/parameters/diag_pack_bytes
grep -qx 625000000 /sys/module/s5krc1s_min/parameters/link_freq_hz
grep -qx 42 /sys/module/s5krc1s_min/parameters/csi2_dt

media=
for _ in $(seq 1 60); do media="$(find_rp1_media || true)"; [[ -n "$media" ]] && break; sleep 1; done
[[ -n "$media" ]]
video="$(find_video "$media")"
[[ -n "$video" ]]
printf 'media=%s\nvideo=%s\n' "$media" "$video" >"$RUN/devices.txt"

python3 /home/philip/bin/s5krc1s_probe_init.py --bus 10 --addr 0x10 --setfile "$SETFILE" \
  >"$RUN/logs/sensor-setup.log" 2>&1
write_reg 3000 0x00
write_reg 3901 "$(saved_reg 3901)"
write_reg 3915 "$(saved_reg 3915)"

# Exact settings from the successful 2026-09-15 RAW2 fan-shape capture.
write_reg 3901 0x2A
write_reg 3902 0x40
write_reg 3903 0x0B
write_reg 3906 0x12
write_reg 3907 0x10
write_reg 3908 0x10
write_reg 391A 0x3C
write_reg 391B 0x00
orig3260=$(( $(saved_reg 3260) ))
printf -v raw2_3260 '0x%02X' $(( orig3260 | 0x02 ))
write_reg 3260 "$raw2_3260"

# Manual table 13: verified balanced hand-contour ON/OFF thresholds.
"$APP/.venv/bin/python" "$RUN/sensor_hand_profile.py" --apply >"$RUN/logs/hand-profile-registers.json"

for reg in 3000 3260 3901 3902 3903 3906 3907 3908 3910 3915 391A 391B; do read_reg "$reg"; done \
  >"$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3260 0x02$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3901 0x2a$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3902 0x40$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3903 0x0b$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3906 0x12$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3907 0x10$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^3908 0x10$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^391A 0x3c$' "$RUN/sensor_registers_raw2_programmed.txt"
grep -qi '^391B 0x00$' "$RUN/sensor_registers_raw2_programmed.txt"

media-ctl -d "$media" -r
media-ctl -d "$media" -V "'s5krc1s_min 10-0010':0 [fmt:Y8_1X8/${WIDTH}x${HEIGHT} field:none]"
media-ctl -d "$media" -V "'csi2':0 [fmt:Y8_1X8/${WIDTH}x${HEIGHT} field:none]"
media-ctl -d "$media" -V "'csi2':4 [fmt:Y8_1X8/${WIDTH}x${HEIGHT} field:none]"
media-ctl -d "$media" -l "'csi2':4 -> 'rp1-cfe-csi2_ch0':0 [1]"
media-ctl -d "$media" -p >"$RUN/media_graph_raw2.txt" 2>&1

debug_dir="$(find /sys/kernel/debug -maxdepth 1 -type d -name 'rp1-cfe:*csi' | head -n 1)"
[[ -n "$debug_dir" ]]
cat "$debug_dir/csi2_errors" >"$RUN/csi2_errors_initial_clear.txt" 2>/dev/null || true
rm -f "$IPC_SOCKET" "$METRICS"
chown -R philip:philip "$RUN/logs"
runuser -u philip -- "$APP/.venv/bin/python" "$RUN/server_production.py" \
  --http-port "$HTTP_PORT" --ws-port "$WS_PORT" --producer-metrics "$METRICS" \
  >>"$RUN/logs/backend.log" 2>&1 &
backend_pid=$!
for _ in $(seq 1 100); do [[ -S "$IPC_SOCKET" ]] && break; kill -0 "$backend_pid" 2>/dev/null; sleep .1; done
[[ -S "$IPC_SOCKET" ]]
for _ in $(seq 1 300); do
  [[ -S /run/user/1000/wayland-0 ]] && break
  sleep .1
done
[[ -S /run/user/1000/wayland-0 ]]
runuser -u philip -- env XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 \
  SDL_VIDEODRIVER=wayland DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  "$PRODUCER" "$video" "$IPC_SOCKET" "$METRICS" \
  >>"$RUN/logs/producer.log" 2>&1 &
producer_pid=$!
echo "$backend_pid $producer_pid" >"$RUN/pids.txt"
echo RAW2_PRODUCTION_RUNNING >"$RUN/stage.txt"
chown -R philip:philip "$RUN"

if [[ -e "$RUN/pending_first_boot_validation" ]]; then
  "$RUN/raw2_production_validate.sh" >>"$RUN/logs/first-boot-validation.log" 2>&1 &
fi

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$producer_pid" 2>/dev/null; do
  sleep 1
done
wait "$producer_pid" || true
wait "$backend_pid" || true
exit 1
