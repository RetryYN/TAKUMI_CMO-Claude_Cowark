#!/bin/bash
# Delvework Navigate Warn — PreToolUse hook（警告のみ、ブロックしない）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

if [ -f "$WF_DIR/active" ] && [ ! -f "$WF_DIR/e_done" ]; then
  warn_pretool "【Delvework】Step E（変更前記録）が未完了のままページ遷移します。変更操作の前に browser_snapshot で記録してください。"
fi

exit 0
