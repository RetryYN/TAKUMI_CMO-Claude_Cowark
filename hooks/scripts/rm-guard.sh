#!/bin/bash
# RM Guard — 一括・再帰削除の機械ガード（PreToolUse:Bash）
# 背景: 2026-07-24 ローカル検証で Sonnet・Opus の両方が「後片付け」を拡大解釈し outputs フォルダの
# 一括削除を提案（harness の許可プロンプトで停止）。モデル差でなく指示解釈の構造問題のため機械強制する。判断はエージェント・強制は hook の原則に従い、
# 再帰削除（rm -r）・グロブ一括削除（rm *）・find -delete・git clean を機械層で止める。
# 個別ファイルの rm と memory/.workflow/ 配下のフラグ掃除には干渉しない。
# 導入手順（TESTING.md「GATE_MODE 昇格」節が正本）: 初期は warn（注入のみ）で運用し、誤爆ゼロ確認後に deny へ昇格。
# 2026-07-24 deny 昇格済み（v1.1.5 実機2ランで warn 発火・正当な個別削除の誤爆ゼロを確認。V39 実測）。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

GATE_MODE="${DELVEWORK_GATE_MODE:-deny}"

# 対象コマンド判定（該当しなければ即通過）
DANGEROUS=0
# rm の再帰フラグ（-r/-R/--recursive、-rf 等の複合も拾う）
if printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])rm[[:space:]]+(-[[:alnum:]]*[rR]|--recursive)'; then
  DANGEROUS=1
# rm のグロブ一括（rm ... * / rm dir/*.png 等）
elif printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])rm[[:space:]][^;|&]*\*'; then
  DANGEROUS=1
# find -delete / git clean / PowerShell Remove-Item -Recurse
elif printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])find[[:space:]][^;|&]*-delete'; then
  DANGEROUS=1
elif printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])git[[:space:]]+clean'; then
  DANGEROUS=1
elif printf '%s' "$STDIN_TEXT" | grep -qiE 'remove-item[^;|&]*-recurse'; then
  DANGEROUS=1
fi
[ "$DANGEROUS" = "1" ] || exit 0

# 免除: memory/.workflow/ 配下のみを対象とするフラグ掃除（再帰フラグなし）は素通し
# 例: rm -f memory/.workflow/{b4_done,e_done} / rm memory/.workflow/verify_*
if printf '%s' "$STDIN_TEXT" | grep -q 'memory/\.workflow/' && \
   ! printf '%s' "$STDIN_TEXT" | grep -qE '(^|[^[:alnum:]_-])rm[[:space:]]+(-[[:alnum:]]*[rR]|--recursive)'; then
  # rm の対象パスが .workflow 以外を含まないことを確認（含む場合はゲート対象）
  if ! printf '%s' "$STDIN_TEXT" | sed 's|memory/\.workflow/[^[:space:]]*||g' | grep -qE '(^|[^[:alnum:]_-])rm[[:space:]][^;|&]*[[:alnum:]/*]'; then
    exit 0
  fi
fi

MSG="【RM Guard】一括・再帰削除は機械ガード対象です。後片付けは自分が作成したファイルのパスを列挙し、個別に rm してください（フォルダ削除・グロブ削除は人間の明示承認が必要）。"
if [ "$GATE_MODE" = "deny" ]; then
  deny "$MSG"
else
  warn_pretool "【RM Guard・試運転(warn)】本来ここでブロックされる操作です — $MSG"
fi
