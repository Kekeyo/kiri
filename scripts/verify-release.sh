#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
repo="${KIRI_REPO:-GaoSSR/Kiri}"

if [ -z "$version" ]; then
  echo "usage: scripts/verify-release.sh <version|tag>" >&2
  exit 2
fi

case "$version" in
  v*) tag="$version"; version="${version#v}" ;;
  *) tag="v${version}" ;;
esac

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 2
  }
}

need gh
need npm
need python3
need shasum
need tar
need mktemp

tmp_dir="$(mktemp -d)"
install_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir" "$install_dir"
}
trap cleanup EXIT

echo "Kiri release verification: ${tag}"
gh release view "$tag" --repo "$repo" --json tagName,url,isDraft,isPrerelease,assets \
  --jq '{tagName,url,isDraft,isPrerelease,assetCount:(.assets|length),assets:[.assets[].name]}'

gh release download "$tag" --repo "$repo" --dir "$tmp_dir"
(
  cd "$tmp_dir"
  shasum -a 256 -c checksums.txt
  for archive in kiri-aarch64-apple-darwin.tar.gz kiri-x86_64-apple-darwin.tar.gz kiri-x86_64-unknown-linux-musl.tar.gz; do
    tar -tzf "$archive" | grep -qx './ports'
    tar -tzf "$archive" | grep -qx './README.md'
    tar -tzf "$archive" | grep -qx './LICENSE'
  done
  if command -v unzip >/dev/null 2>&1; then
    unzip -Z1 kiri-x86_64-pc-windows-msvc.zip | grep -qx 'ports.exe'
    unzip -Z1 kiri-x86_64-pc-windows-msvc.zip | grep -qx 'README.md'
    unzip -Z1 kiri-x86_64-pc-windows-msvc.zip | grep -qx 'LICENSE'
  fi
)

KIRI_VERSION="$tag" KIRI_INSTALL_DIR="$install_dir" bash scripts/install.sh >/dev/null
"$install_dir/ports" --help >/dev/null

cache_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir" "$install_dir" "$cache_dir"' EXIT
npm_version="$(npm view "@gaossr/kiri@${version}" version --registry https://registry.npmjs.org/ --cache "$cache_dir")"
if [ "$npm_version" != "$version" ]; then
  echo "npm version is ${npm_version}, expected ${version}" >&2
  exit 1
fi
echo "npm @gaossr/kiri=${npm_version}"

if command -v brew >/dev/null 2>&1; then
  brew_json="$(brew info gaossr/tap/kiri --json=v2)"
  BREW_JSON="$brew_json" python3 - "$version" <<'PY'
import json
import os
import sys

expected = sys.argv[1]
formula = json.loads(os.environ["BREW_JSON"])["formulae"][0]
actual = formula["versions"]["stable"]
if actual != expected:
    raise SystemExit(f"Homebrew stable is {actual}, expected {expected}")
print(f"Homebrew stable={actual}")
PY
fi

echo "OK release verification passed for ${tag}"
