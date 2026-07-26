#!/bin/bash
# TAKUMI-CMO Hook — shared functions (Cowork / Linux VM compatible)
# ワークスペースのパスは CLAUDE_PROJECT_DIR から解決する（絶対パス直書き禁止）

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
WF_DIR="${TAKUMI_WF_DIR:-$PROJECT_DIR/memory/.workflow}"

# Capture stdin (hook payload JSON) for input inspection
STDIN_JSON="$(cat 2>/dev/null || true)"

# STDIN_TEXT: ツール結果JSONは日本語が \uXXXX エスケープで来ることがあり、そのままでは
# 日本語パターン（決済/クレジットカード等）が一切マッチしない（Money Watch がサイレント無効化）。
# 日本語照合は必ず STDIN_TEXT に対して行うこと。perl → python3 → python の順で試し、無ければ生のまま。
#
# **\uXXXX が1つも無いなら変換は不要**なので、外部プロセスを起動しない。
# Bash 系ペイロードのほとんどが該当する。hook 1回あたり数ミリ秒だが、
# **Bash ツール1回につき3 hook がこれを source する**ので3倍で効く
# （2026-07-27 実測: Bash 1回 = 52.8ms のうち _common.sh が 27.9ms = 53%）。
# **判定は「変換の要否」だけで、変換そのものの中身は一切変えない。**
case "$STDIN_JSON" in
  *'\u'*)
    if command -v perl >/dev/null 2>&1; then
      # pack("U") で \uXXXX を UTF-8 バイト列に展開する。-CO は使わない（既存の生UTF-8バイトを二重エンコードして壊すため）
      STDIN_TEXT="$(printf '%s' "$STDIN_JSON" | perl -pe 's/\\u([0-9a-fA-F]{4})/pack("U",hex($1))/ge' 2>/dev/null)"
    elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
      PY="$(command -v python3 || command -v python)"
      STDIN_TEXT="$(printf '%s' "$STDIN_JSON" | "$PY" -c 'import sys,re; sys.stdout.write(re.sub(r"\\\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1),16)), sys.stdin.read()))' 2>/dev/null)"
    fi
    ;;
esac
[ -n "$STDIN_TEXT" ] || STDIN_TEXT="$STDIN_JSON"

# CMD_TEXT: 改行を実改行へ戻したテキスト。**行単位・単語境界で照合する hook は必ずこれを使う。**
# hook ペイロードは JSON なので改行が literal な `\n`（バックスラッシュ + n の2文字）で来る。
# STDIN_TEXT のまま `(^|[^[:alnum:]_-])rm` のような単語境界で照合すると、
# `\n` の "n" が英数字なので境界が成立せず、**2行目以降の `rm -rf` に一致しない**。
# 2026-07-26 に RM Guard で実測: `cd /tmp\nrm -rf outputs/` が素通りしていた
# （deny ゲートのフェイルオープン）。brand-isolation-guard は 2026-07-25 に
# 同じ変換を自前で持っていたが、共有されていなかったため RM Guard に届いていなかった。
# sed ではなく bash のパラメータ展開で置換する（外部プロセスを起こさない）。
# `\\n` は「バックスラッシュ + n の2文字」に一致する — sed 版と同じ意味。
CMD_TEXT="${STDIN_TEXT//\\n/$'\n'}"

# cmd_skeleton: ヒアドキュメント本文を落とした「コマンドの骨格」を標準出力へ。
# 検証報告・ナレッジ・lessons.md など、**危険な語を引用するだけ**の文書を書けなくなる誤爆を防ぐ
# （2026-07-25 brand-isolation-guard の F3、2026-07-26 RM Guard の O-1 で実測）。
# ただし本文を**インタプリタに食わせている**場合は本文もコマンドなので落とさない
# （`bash <<EOF` / `cat <<EOF | sh` / `python3 - <<PY` / `ssh host <<EOF`）。
_INTERP_RE='(^|[^[:alnum:]_-])(bash|sh|zsh|dash|ksh|eval|python3?|perl|ruby|node|ssh)([ \t]|$)'
cmd_skeleton() {
  printf '%s' "$CMD_TEXT" | awk -v interp="$_INTERP_RE" '
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
        if ($0 ~ interp) next
        tag = substr($0, RSTART, RLENGTH)
        sub(/<<-?[ \t]*/, "", tag)
        gsub(/['"'"'"]/, "", tag)
        skip = 1; term = tag
      }
    }'
}

# JSON文字列へ埋め込む値のエスケープ（ページ/URL由来文字列で hook 出力JSONが壊れる=フェイルオープンを防ぐ）
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037'
}

deny() {
  local msg; msg="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}' "$msg"
  exit 0
}

warn_pretool() {
  local msg; msg="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$msg"
  exit 0
}

warn_posttool() {
  local msg; msg="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}' "$msg"
  exit 0
}

warn_session() {
  local msg; msg="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' "$msg"
  exit 0
}
