#!/bin/bash
# Agent Parallel Gate — サブエージェントの同時起動を上限（既定4体）で止める。
#
# なぜ要るか: 本体の既定は同時20体で、戦略級（opus/high・fable/medium）が20体走ると
# 費用とレート消費が跳ね上がり、途中で失敗した委譲の後始末も追えなくなる。
# 本命の強制は環境変数 CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS（本体側・利用者の環境）だが、
# **プラグインからは環境変数を設定できない**ので、こちら側で数える。
#
# 数え方: PreToolUse(Agent) で1行 append、PostToolUse(Agent) で1行 pop。
# 完了シグナルを取りこぼすと枠が残るため、TTL を過ぎた行は掃除する（デッドロック回避）。
#
# 導入手順は TESTING.md「GATE_MODE 昇格」が正本 —
# **初期は warn（注入のみ）**。誤爆ゼロを実機（V79）で確認してから deny へ昇格する。
# 並列上限は「止めそこねても事故にならない」種類の規約なので、
# **誤爆で正当な委譲を殺すほうが実害が大きい**。だから最初から deny にしない。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

MODE="${TAKUMI_PARALLEL_GATE_MODE:-warn}"
MAX="${TAKUMI_MAX_PARALLEL_AGENTS:-4}"
TTL="${TAKUMI_AGENT_SLOT_TTL:-1800}"   # 秒。これを過ぎた枠は「取りこぼし」として掃除する
SLOTS="$WF_DIR/agents_running"
EVENT="${1:-pre}"

# 対象は Agent 系のツールだけ（tool_name で判定。他ツールには一切干渉しない）
printf '%s' "$STDIN_TEXT" | grep -qE '"tool_name"[[:space:]]*:[[:space:]]*"(Agent|Task)"' || exit 0

mkdir -p "$WF_DIR" 2>/dev/null || exit 0
NOW="$(date +%s 2>/dev/null)" || exit 0

# TTL 超過の枠を掃除（取りこぼしで永久に埋まるのを防ぐ）
if [ -f "$SLOTS" ]; then
  awk -v now="$NOW" -v ttl="$TTL" '$1 ~ /^[0-9]+$/ && (now - $1) < ttl' "$SLOTS" > "$SLOTS.tmp" 2>/dev/null \
    && mv "$SLOTS.tmp" "$SLOTS" 2>/dev/null
fi

if [ "$EVENT" = "post" ]; then
  # 完了: 最も古い枠を1つ解放する（どの枠かは特定できないが、必要なのは残数だけ）
  if [ -f "$SLOTS" ]; then
    tail -n +2 "$SLOTS" > "$SLOTS.tmp" 2>/dev/null && mv "$SLOTS.tmp" "$SLOTS" 2>/dev/null
  fi
  exit 0
fi

# grep -c は0件のとき「0」を出しつつ非ゼロ終了するので、`|| echo 0` だと "0\n0" になる（実測）。
# 代入してから失敗を握りつぶし、最後に数値であることを確かめる。
RUNNING=0
if [ -f "$SLOTS" ]; then
  RUNNING="$(grep -c . "$SLOTS" 2>/dev/null)" || RUNNING=0
fi
case "$RUNNING" in ''|*[!0-9]*) RUNNING=0 ;; esac

if [ "$RUNNING" -ge "$MAX" ]; then
  MSG="【並列ゲート】サブエージェントの同時起動は最大 ${MAX} 体です（現在 ${RUNNING} 体が実行中）。前の委譲が返ってから次を起動してください。急ぐなら、いま走っている中で優先度の低いものを止めてから起動します。**実際には ${RUNNING} 体も走っていないのにここで止まったなら、それは枠の取りこぼしです** — 委譲が異常終了（Connection closed 等）すると PostToolUse が発火せず枠が残ります。memory/.workflow/agents_running の行数と実際の実行数を見比べ、合わなければ同ファイルを消してから再開してください（次のセッション開始時にも自動で消えます）。上限そのものを変えるのは利用者の環境設定（CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS）で、プラグイン側では変更できません。詳細は docs/agent-tiers.md。"
  if [ "$MODE" = "deny" ]; then
    deny "$MSG"
  else
    warn_pretool "【並列ゲート・試運転(warn)】本来ここでブロックされる操作です — $MSG"
  fi
fi

# 起動を1枠使う
printf '%s\n' "$NOW" >> "$SLOTS" 2>/dev/null
exit 0
