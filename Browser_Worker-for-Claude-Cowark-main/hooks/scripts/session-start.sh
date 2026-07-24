#!/bin/bash
# Delvework Session Start — 前回未完了タスクの通知 + 環境情報

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# 注意: warn_session は exit するため、呼べるのは1回だけ。メッセージは PREFIX に集約する
PREFIX=""
if [ -f "$WF_DIR/active" ] && [ ! -f "$WF_DIR/k_done" ]; then
  task="$(cat "$WF_DIR/active" 2>/dev/null | tr -d '\n"\\')"
  PREFIX="【Delvework】前回のタスク「$task」が未完了です（k_done なし）。memory/session-log.md を確認して引き継ぐこと。 "
fi

# 永続化チェック: ワークスペースに蓄積の痕跡（knowledge/）が無い場合、
# クラウドセッションの一時領域で動いている可能性が高い（セッション終了で蓄積消失）。
# 注: .git の存在は永続化の根拠にしない（クラウドコンテナ内の clone でも .git は存在するため）
if [ ! -d "$PROJECT_DIR/knowledge" ]; then
  PREFIX="${PREFIX}【永続化警告】このワークスペースに蓄積（knowledge/）がありません。永続フォルダ未接続の可能性があり、その場合 memory/ と knowledge/ の蓄積はセッション終了で消えます。ユーザーに永続フォルダの接続を1行で推奨し、未接続のまま進める場合は蓄積系機能（skillify/feedback/watchスナップショット）の成果を必ず成果物としてユーザーに渡すこと。 "
fi

# 初期セットアップ: 未回答のときだけ1行案内（回答済みなら何も注入しない = コンテキスト消費ゼロ）
SETUP_FILE="$PROJECT_DIR/knowledge/config/setup.yaml"
if [ -d "$PROJECT_DIR/knowledge" ] && [ ! -f "$SETUP_FILE" ]; then
  PREFIX="${PREFIX}【セットアップ】初期ヒアリング未回答。最初の依頼の前に /セットアップ（procedures/delve-setup.md）を1行で案内すること（強制はしない）。 "
elif [ -f "$SETUP_FILE" ] && grep -q "completed: pending" "$SETUP_FILE" 2>/dev/null; then
  PREFIX="${PREFIX}【セットアップ】未回答の項目が残っている（setup.yaml: pending）。区切りの良いタイミングで /セットアップ の続きを1行で案内。 "
fi

# タスクPack設定（knowledge/config/packs.conf）: off のパックを通知に含める
PACKS_CONF="$PROJECT_DIR/knowledge/config/packs.conf"
if [ -f "$PACKS_CONF" ]; then
  OFF_PACKS="$(grep -E '^[a-z-]+=off' "$PACKS_CONF" 2>/dev/null | cut -d= -f1 | grep -v '^core$' | tr '\n' ',' | sed 's/,$//')"
  if [ -n "$OFF_PACKS" ]; then
    PREFIX="${PREFIX}【タスクPack】無効: ${OFF_PACKS} — 該当パックの機能は使わない・提案しない・自動発火させない（定義は procedures/delve-config.md（/カスタマイズ の機能ON/OFF）参照。ユーザーが明示要求したときのみON化を1行案内）。 "
  fi
fi

# 運用ルール本文は session-rules.txt が正本（bash文字列への直書き禁止 — 編集性とエスケープ事故防止）
RULES_FILE="$SCRIPT_DIR/session-rules.txt"
if [ -f "$RULES_FILE" ]; then
  RULES="$(tr '\n' ' ' < "$RULES_FILE")"  # エスケープは warn_session（json_escape）に一元化
  warn_session "${PREFIX}${RULES}"
fi

# フォールバック（rules ファイル欠損時）
warn_session "${PREFIX}【Delvework】session-rules.txt が見つかりません（プラグイン破損の可能性）。docs/conventions.md と各 delve コマンドの手順に従い、変更操作は必ず /タスク開始 から行うこと。"
