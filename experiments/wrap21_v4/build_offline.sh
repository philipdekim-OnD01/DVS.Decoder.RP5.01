#!/usr/bin/env bash
# Offline only: compile experimental producer + synthetic/RAW replay; never opens V4L2.
set -Eeuo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "$HERE/../.." && pwd)"
BASE="$REPO/payload/home/philip/dvs_raw2_production"
OUT="$REPO/build/wrap21-v4"
RAW="${1:-}"
mkdir -p "$OUT"
for command in g++ gzip; do command -v "$command" >/dev/null || { echo "Missing: $command"; exit 2; }; done
g++ -std=c++17 -O2 -Wall -Wextra -Wno-unused-parameter -pthread -I"$BASE" -I"$HERE" \
  "$HERE/raw2_producer_wrap21.cpp" "$BASE/dvs_renderer.cpp" -o "$OUT/raw2_producer_wrap21"
g++ -std=c++17 -O3 -Wall -Wextra -Werror -I"$HERE" \
  "$HERE/test_wrap21.cpp" -o "$OUT/test_wrap21"
"$OUT/test_wrap21" --synthetic
if [[ -n "$RAW" ]]; then
  [[ -f "$RAW" ]] || { echo "Missing RAW file: $RAW"; exit 2; }
  gzip -dc -- "$RAW" | "$OUT/test_wrap21"
fi
echo "BUILD_AND_REPLAY_OK"
echo "EXPERIMENTAL_BINARY=$OUT/raw2_producer_wrap21"
echo "LIVE_SYSTEM_UNCHANGED=YES"
