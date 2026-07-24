#!/bin/bash
# Delvework URL Guard — PreToolUse hook（ページ単位権限）
# navigate 系ツールの遷移先URLを拒否リストと照合し、金銭発生・広告出稿・課金設定
# ページへの遷移をブロックする。誤操作・自律判断による広告出稿（＝金銭発生）の防止が目的。
#
# リストの優先順位:
#   1. knowledge/config/url-allowlist.txt … マッチしたら許可（拒否リストより優先。ユーザーが明示的に開放）
#   2. knowledge/config/url-denylist.txt  … ワークスペース固有の追加拒否
#   3. hooks/scripts/url-denylist.txt     … プラグイン同梱のデフォルト拒否

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# ペイロードから URL を抽出（claude-in-chrome navigate / playwright browser_navigate とも "url" キー）
# 複数URL（batch/タブ複数生成）に備えて全マッチを照合する（1件でも deny 該当なら遷移全体を止める）
URLS="$(printf '%s' "$STDIN_JSON" | grep -oE '"url"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -E 's/.*:[[:space:]]*"([^"]*)".*/\1/')"
[ -z "$URLS" ] && exit 0

match_list() {
  # $1: リストファイル, $2: URL。コメント・空行を除いた各パターンで照合
  local file="$1" url="$2" pat
  [ -f "$file" ] || return 1
  while IFS= read -r pat; do
    case "$pat" in ''|'#'*) continue ;; esac
    if printf '%s' "$url" | grep -qiE "$pat" 2>/dev/null; then
      return 0
    fi
  done < "$file"
  return 1
}

# 検証モード（memory/.workflow/verify_allowlist が存在する間）: リスト記載サイト以外への遷移を全て deny。
# 検証タスクが実サービス（GitHub等）へ漂流するのを機械的に防ぐ（2026-07-24 実機で github.com/login へ漂流した実測より）
VERIFY_ALLOW="$WF_DIR/verify_allowlist"
if [ -f "$VERIFY_ALLOW" ]; then
  while IFS= read -r URL; do
    [ -z "$URL" ] && continue
    if ! match_list "$VERIFY_ALLOW" "$URL"; then
      deny "【検証モード・許可サイト限定】$URL は検証の許可サイト（memory/.workflow/verify_allowlist 記載）ではありません。検証中はリスト外のサイトを訪問できません — 該当項目は SKIP(理由) として次の項目へ進んでください。"
    fi
  done <<EOF2
$URLS
EOF2
fi

while IFS= read -r URL; do
  [ -z "$URL" ] && continue
  # 1. 許可リスト（ユーザーの明示開放）が最優先
  if match_list "$PROJECT_DIR/knowledge/config/url-allowlist.txt" "$URL"; then
    continue
  fi
  # 2-3. 拒否リスト照合
  for LIST in "$PROJECT_DIR/knowledge/config/url-denylist.txt" "$SCRIPT_DIR/url-denylist.txt"; do
    if match_list "$LIST" "$URL"; then
      deny "【URL Guard】このページ（$URL）は金銭発生・広告出稿・課金設定に該当するため遷移をブロックしました。広告出稿や課金操作はAIには許可されていません。業務上必要な場合は、ユーザー本人が knowledge/config/url-allowlist.txt に該当パターンを追記して明示的に開放してください（AIが代行して追記することは禁止）。"
    fi
  done
done <<EOF
$URLS
EOF

exit 0
