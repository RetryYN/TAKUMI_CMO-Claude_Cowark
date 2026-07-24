#!/bin/bash
# OV Gate — 不可逆送出タスク（bulk_send 宣言済み）の完了宣言（touch k_done）を、
# outcome-verifier の独立検証記録（ov_done）なしでは通さない。
# 対象は Bash の「touch × k_done」だけ。読み取り系・通常タスク（bulk_send なし）には一切干渉しない。
# 導入手順（TESTING.md「GATE_MODE 昇格」節が正本）: 初期は warn（注入のみ）で運用し、誤爆ゼロ確認後に deny へ昇格。
# 2026-07-24 deny 昇格済み（v0.101.1 実機で matcher 発火・誤爆ゼロを確認。テストは DELVEWORK_GATE_MODE で両モードを検証）。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

GATE_MODE="${DELVEWORK_GATE_MODE:-deny}"

# 1) k_done への touch を含むコマンドだけが対象
printf '%s' "$STDIN_TEXT" | grep -q 'k_done' || exit 0
printf '%s' "$STDIN_TEXT" | grep -q 'touch' || exit 0
# 初期化・掃除（rm を含むコマンド）は免除 — delve-start 手順2 の
# `rm -f memory/.workflow/{...,k_done,...}` が前タスクの bulk_send 残留時に誤爆しデッドロックするため
printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])rm([[:space:]]|$)' && exit 0

# 2) 不可逆送出を宣言していないタスクは対象外
[ -f "$WF_DIR/bulk_send" ] || exit 0

# 3) outcome-verifier の判定記録があれば通す
[ -f "$WF_DIR/ov_done" ] && exit 0

MSG="【OV Gate】不可逆送出を含むタスク（bulk_send 宣言済み）は outcome-verifier の独立検証なしに完了できません。after_state と CP証跡を outcome-verifier サブエージェントに渡して検証させ、応答の判定要約を memory/.workflow/ov_done に書き込んで（echo '<VERIFIED n/m と1行要約>' > memory/.workflow/ov_done）から k_done してください。"
if [ "$GATE_MODE" = "deny" ]; then
  deny "$MSG"
else
  warn_pretool "【OV Gate・試運転(warn)】本来ここでブロックされる操作です — $MSG"
fi
