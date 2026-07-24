#!/bin/bash
# TAKUMI-CMO Brand Isolation Guard — PreToolUse:Bash|mcp__workspace__bash
# マルチブランドの記憶区画 knowledge/brands/<slug>/ への「書き込み」を、アクティブブランドの
# 区画だけに限定する。別ブランド区画への書き込み＝相互汚染を機械遮断する（ドメイン不変条件2）。
# 読み取り（cat/ls/grep 等）には干渉しない。判断はエージェント・強制は hook の原則に従う。
# 導入手順（TESTING.md「GATE_MODE 昇格」節が正本）: 初期 warn → 誤爆ゼロ確認後に deny 昇格。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

GATE_MODE="${TAKUMI_GATE_MODE:-deny}"

# ヒアドキュメント本文を除去した「コマンドの骨格」を判定対象にする。
# 検証報告・ナレッジ・lessons.md など、区画パスを**引用するだけ**の文書を書けなくなる誤爆を防ぐ
# （2026-07-25 ローカル実機検証 F3 で実測）。ただしヒアドキュメントをシェル解釈系
# （bash/sh/zsh/dash/ksh/eval）に食わせている場合は本文がコマンドなので除去しない。
# hook ペイロードは JSON なので改行が literal な \n（2文字）で来る。行単位で見るため実改行へ戻す。
CMD_TEXT="$(printf '%s' "$STDIN_TEXT" | sed 's/\\n/\
/g')"
CMD_SKELETON="$(printf '%s' "$CMD_TEXT" | awk '
  BEGIN { skip = 0; term = "" }
  {
    if (skip) {
      line = $0
      gsub(/^[ \t]+|[ \t]+$/, "", line)
      if (line == term) { skip = 0; term = "" }
      next
    }
    print
    if (match($0, /<<-?[ \t]*['"'"'"]?[A-Za-z_][A-Za-z0-9_]*['"'"'"]?/)) {
      # シェル解釈系に食わせるヒアドキュメントは本文もコマンド → 除去しない
      if ($0 ~ /(^|[^[:alnum:]_-])(bash|sh|zsh|dash|ksh|eval)([ \t]|$)/) next
      tag = substr($0, RSTART, RLENGTH)
      sub(/<<-?[ \t]*/, "", tag)
      gsub(/['"'"'"]/, "", tag)
      skip = 1; term = tag
    }
  }')"

# ブランド区画パスに触れていなければ即通過
printf '%s' "$CMD_SKELETON" | grep -qE 'knowledge/brands/[a-z0-9][a-z0-9-]*' || exit 0

# 書き込み系の指標がなければ通過（読み取りには干渉しない）
# 書き込み: リダイレクト > >> / tee / cp mv touch mkdir rmdir rm install dd / sed -i
if ! printf '%s' "$CMD_SKELETON" | grep -qE '(>>?|[[:space:]]tee[[:space:]]|(^|[^[:alnum:]_-])(cp|mv|touch|mkdir|rmdir|rm|install|dd)[[:space:]]|sed[[:space:]]+-i)'; then
  exit 0
fi

# アクティブブランド（memory/.workflow/active_brand の中身。無ければ空）
ACTIVE=""
[ -f "$WF_DIR/active_brand" ] && ACTIVE="$(tr -d '[:space:]' < "$WF_DIR/active_brand" 2>/dev/null)"

# コマンドが参照するブランド区画の slug を列挙し、アクティブ以外への書き込みを検出
VIOLATION=""
while IFS= read -r slug; do
  [ -z "$slug" ] && continue
  if [ -z "$ACTIVE" ] || [ "$slug" != "$ACTIVE" ]; then
    VIOLATION="$slug"; break
  fi
done <<EOF
$(printf '%s' "$CMD_SKELETON" | grep -oE 'knowledge/brands/[a-z0-9][a-z0-9-]*' | sed -E 's#knowledge/brands/##' | sort -u)
EOF

[ -z "$VIOLATION" ] && exit 0

if [ -z "$ACTIVE" ]; then
  MSG="【Brand Isolation Guard】アクティブブランドが未確定のまま、ブランド区画（knowledge/brands/$VIOLATION/）への書き込みが試みられました。全変更操作はアクティブブランド確定が前段です — まず /ブランド でアクティブブランドを確定してください。"
else
  MSG="【Brand Isolation Guard】アクティブブランド『$ACTIVE』以外の区画（knowledge/brands/$VIOLATION/）への書き込みはブロックされます。ブランドをまたぐ書き込み＝相互汚染を防ぐためです。対象ブランドに切り替えてから操作してください（/ブランド で切替）。"
fi

if [ "$GATE_MODE" = "deny" ]; then
  deny "$MSG"
else
  warn_pretool "【Brand Isolation Guard・試運転(warn)】本来ここでブロックされる操作です — $MSG"
fi
