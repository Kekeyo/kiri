#!/usr/bin/env bash
set -euo pipefail

max_ms="${KIRI_PERF_MAX_MS:-1500}"

if [ -n "${KIRI_BIN:-}" ]; then
  bin_cmd=("$KIRI_BIN")
elif [ -x "./target/release/ports" ]; then
  bin_cmd=("./target/release/ports")
else
  bin_cmd=(cargo run --quiet --bin ports --)
fi

command_label() {
  local label=""
  local part
  for part in "${bin_cmd[@]}"; do
    label+="$(printf '%q' "$part") "
  done
  printf '%s' "${label% }"
}

measure() {
  local name="$1"
  shift
  python3 - "$name" "$max_ms" "$@" <<'PY'
import subprocess
import sys
import time

name = sys.argv[1]
max_ms = int(sys.argv[2])
command = sys.argv[3:]

started = time.perf_counter()
result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
elapsed_ms = int((time.perf_counter() - started) * 1000)
status = "OK" if result.returncode == 0 and elapsed_ms <= max_ms else "SLOW/FAIL"
print(f"{status} {name}: {elapsed_ms}ms")
if result.returncode != 0 or elapsed_ms > max_ms:
    sys.exit(1)
PY
}

echo "Kiri perf smoke using: $(command_label)"
measure "ports" "${bin_cmd[@]}"
measure "ports --all" "${bin_cmd[@]}" --all
measure "ports ps" "${bin_cmd[@]}" ps

if [ -n "${KIRI_PERF_LOG_TARGET:-}" ]; then
  measure "ports logs ${KIRI_PERF_LOG_TARGET}" "${bin_cmd[@]}" logs "$KIRI_PERF_LOG_TARGET" --lines 5
fi
