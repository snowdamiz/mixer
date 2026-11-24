#!/usr/bin/env bash
set -euo pipefail

experiment=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$experiment/../../.." && pwd)
cd "$repo"
mkdir -p verification/local
scratch=$(mktemp -d "$repo/verification/local/native-map-island.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/tmp" "$scratch/modules"
export TMPDIR="$scratch/tmp"
export CLANG_MODULE_CACHE_PATH="$scratch/modules"
export SWIFTPM_MODULECACHE_OVERRIDE="$scratch/modules"

revision=$(git rev-parse HEAD)
swift --version
printf 'Source revision %s, replay inputs SHA-256 ' "$revision"
(
  cd "$experiment"
  shasum -a 256 Package.swift Package.resolved replay.sh Sources/NativeMapReplay/*.swift
) | shasum -a 256

swift run --package-path "$experiment" --scratch-path "$scratch/build" --cache-path "$scratch/cache" \
  --config-path "$scratch/config" --security-path "$scratch/security" --manifest-cache local \
  --force-resolved-versions NativeMapReplay "$revision" "$@"
