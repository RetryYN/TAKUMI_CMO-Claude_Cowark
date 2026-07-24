#!/bin/bash
# Critic Gate — design-artisan 生成中（critic_pending）のビジュアル成果物を、
# design-critic の PASS 記録（critic_pass）なしで人間・外部へ渡す出口をふさぐ。
# 対象は「ファイルを人間・外部に渡す出口」のみ（投稿系ブラウザ操作は workflow-gate/psv ゲートの層）。
# フラグ運用: 委譲直後に critic_pending を touch（同時に critic_pass を rm — 前回 PASS の鮮度切れ防止）。
# critic が PASS を返したら critic_pending を rm し、PASS の1行要約を critic_pass に書き込む。
# 導入手順: 初期は warn で運用し、誤爆パターンを knowledge/config/critic-suppress.txt（grep -E 正規表現・
# 1行1パターン・# はコメント。緩める方向の追記はユーザー確認必須）に収集後、deny へ昇格。
# 2026-07-24 deny 昇格済み（v0.101.1 実機で matcher 発火・誤爆ゼロを確認）。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

GATE_MODE="${DELVEWORK_GATE_MODE:-deny}"

# 1) デザイン生成中でなければ素通し
[ -f "$WF_DIR/critic_pending" ] || exit 0

# 2) ビジュアル成果物（拡張子）を含まない送付（テキスト・ログ等）は干渉しない
printf '%s' "$STDIN_TEXT" | grep -qiE '\.(html|png|jpe?g|webp|svg|gif|pptx)' || exit 0

# 3) critic PASS 記録があれば通す
[ -f "$WF_DIR/critic_pass" ] && exit 0

# 4) 抑制リスト照会（例: デバッグ用スクショ・QA中間画像）
SUPPRESS="$PROJECT_DIR/knowledge/config/critic-suppress.txt"
if [ -f "$SUPPRESS" ]; then
  while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    case "$pat" in \#*) continue ;; esac
    printf '%s' "$STDIN_TEXT" | grep -qE "$pat" && exit 0
  done < "$SUPPRESS"
fi

MSG="【Critic Gate】design-artisan の生成物は design-critic の PASS まで人間に送付・投稿できません。design-critic にレビューさせ、REVISE なら FIX を design-artisan に再投入し、PASS 後に memory/.workflow/critic_pass に PASS の1行要約を書き込んで（同時に critic_pending を rm）から送付してください。"
if [ "$GATE_MODE" = "deny" ]; then
  deny "$MSG"
else
  warn_pretool "【Critic Gate・試運転(warn)】本来ここでブロックされる操作です — $MSG"
fi
