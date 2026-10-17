#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
[[ "$(uname -r)" == '6.12.47+rpt-rpi-2712' ]] || { echo 'Unsupported kernel'; exit 1; }
KDIR=/lib/modules/$(uname -r)/build
OUT=$(mktemp -d /tmp/dvs-build.XXXXXX)
trap 'rm -rf "$OUT"' EXIT
cp -R drivers "$OUT/"
make -C "$KDIR" M="$OUT/drivers/sensor" modules
make -C "$KDIR" M="$OUT/drivers/rp1_cfe" CONFIG_VIDEO_RP1_CFE=m modules
APP="$PWD/payload/home/philip/dvs_raw2_production"
# Match the build flags of the binary captured from the running Pi.
CXXFLAGS=(-std=c++17 -O2 -Wall -Wextra -Wno-unused-parameter -pthread -I"$APP")
# ELF retains the translation-unit filename; preserve the original name too.
cp "$APP/raw2_producer.cpp" "$OUT/raw2_producer_trace_shadow.cpp"
g++ "${CXXFLAGS[@]}" "$OUT/raw2_producer_trace_shadow.cpp" "$APP/dvs_renderer.cpp" -o "$OUT/raw2_producer"
cmp "$OUT/raw2_producer" "$APP/raw2_producer" || { echo 'Rebuilt producer differs from live snapshot'; exit 1; }
dtc -@ -I dts -O dtb -o "$OUT/s5krc1s-cam0.dtbo" drivers/overlay/s5krc1s-cam0-overlay.dts
g++ -O3 -std=c++17 -pthread -I"$APP" tests/test_raw2.cpp "$APP/dvs_renderer.cpp" -o "$OUT/test_raw2"
"$OUT/test_raw2"
for test in test_alignment test_visual test_live_shadow test_trace; do
    g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$APP" "tests/$test.cpp" -o "$OUT/$test"
    "$OUT/$test"
done
g++ "${CXXFLAGS[@]}" tests/test_json_metrics.cpp "$APP/dvs_renderer.cpp" -o "$OUT/test_json_metrics"
"$OUT/test_json_metrics" "$OUT/test_metrics.json"
python3 - "$OUT/test_metrics.json" <<'PY'
import json, sys
with open(sys.argv[1]) as source:
    data = json.load(source)
assert data['raw2_boundary_trace_enabled'] is True
assert data['raw2_boundary_legacy_reject_wrap21'] == 1
assert any(x['kind'] == 'R' and x['head_run'] == 11 and x['tail_run'] == 10
           for x in data['raw2_boundary_trace_samples'])
print('PASS: production metrics JSON and 21-column wrap metadata')
PY
PYTHONPATH="$APP" python3 -m unittest discover -s tests -p 'test_frame_surface.py' -v
mkdir -p build
cp "$OUT/raw2_producer" "$OUT/s5krc1s-cam0.dtbo" "$OUT/drivers/sensor/s5krc1s_min.ko" "$OUT/drivers/rp1_cfe/rp1-cfe.ko" build/
echo 'Build/tests OK. Outputs in build/; live drivers/application unchanged.'
