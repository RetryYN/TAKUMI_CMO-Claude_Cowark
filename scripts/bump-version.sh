#!/bin/bash
# Usage: scripts/bump-version.sh 0.46.0
# plugin.json と marketplace.json の version を同時に更新する（2重管理の乖離防止）
set -euo pipefail
VER="${1:?usage: bump-version.sh <version>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$ROOT/.claude-plugin/plugin.json" "$ROOT/.claude-plugin/marketplace.json"; do
  sed -i -E "s/\"version\": \"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$VER\"/" "$f"
done
grep -H '"version"' "$ROOT/.claude-plugin/"*.json
