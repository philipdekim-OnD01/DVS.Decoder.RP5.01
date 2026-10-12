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
g++ -O3 -std=c++17 -pthread "$APP/raw2_producer.cpp" "$APP/dvs_renderer.cpp" -o "$OUT/raw2_producer"
dtc -@ -I dts -O dtb -o "$OUT/s5krc1s-cam0.dtbo" drivers/overlay/s5krc1s-cam0-overlay.dts
g++ -O3 -std=c++17 -pthread -I"$APP" tests/test_raw2.cpp "$APP/dvs_renderer.cpp" -o "$OUT/test_raw2"
"$OUT/test_raw2"
PYTHONPATH="$APP" python3 -m unittest discover -s tests -p 'test_frame_surface.py' -v
mkdir -p build
cp "$OUT/raw2_producer" "$OUT/s5krc1s-cam0.dtbo" "$OUT/drivers/sensor/s5krc1s_min.ko" "$OUT/drivers/rp1_cfe/rp1-cfe.ko" build/
echo 'Build/tests OK. Outputs in build/; live drivers/application unchanged.'
