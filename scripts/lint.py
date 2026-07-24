#!/usr/bin/env python3
"""TAKUMI-CMO plugin lint — 参照整合・frontmatter・JSON・バージョンの機械チェック。
CI とローカル（python3 scripts/lint.py）の両方で使う。exit 0=OK / 1=違反あり。"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def frontmatter(p: Path) -> dict:
    text = read(p)
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(("#", " ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


# --- 1. JSON妥当性とバージョン一致 ---
plugin = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
market = json.loads(read(ROOT / ".claude-plugin/marketplace.json"))
hooks = json.loads(read(ROOT / "hooks/hooks.json"))
mv = market["plugins"][0]["version"]
if plugin["version"] != mv:
    err(f"version mismatch: plugin.json={plugin['version']} marketplace.json={mv}")

# --- 2. hooks.json が参照するスクリプトの実在 ---
for event, groups in hooks["hooks"].items():
    for g in groups:
        for h in g["hooks"]:
            m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"", h["command"])
            if not m:
                err(f"hooks.json({event}): command が ${{CLAUDE_PLUGIN_ROOT}} 基準でない: {h['command']}")
            elif not (ROOT / m.group(1)).is_file():
                err(f"hooks.json({event}): スクリプト不在 {m.group(1)}")

# --- 3. commands ↔ procedures の1対1 ---
commands = sorted((ROOT / "commands").glob("*.md"))
procedures = sorted((ROOT / "procedures").glob("takumi-*.md"))
referenced_procs: set[str] = set()
for c in commands:
    fm = frontmatter(c)
    if "description" not in fm:
        err(f"{c.name}: frontmatter に description がない")
    body = read(c)
    refs = re.findall(r"procedures/(takumi-[a-z-]+\.md)", body)
    if not refs:
        err(f"commands/{c.name}: procedures/takumi-*.md への参照がない")
    for r in refs:
        referenced_procs.add(r)
        if not (ROOT / "procedures" / r).is_file():
            err(f"commands/{c.name}: 参照先 procedures/{r} が不在")
_extra_ref_sources = [ROOT / "hooks/scripts/session-rules.txt", ROOT / "README.md",
                      ROOT / "docs/command-registry.md"] + list(ROOT.glob("docs/**/*.md"))
_extra_text = "".join(read(f) for f in _extra_ref_sources if f.is_file())
for p in procedures:
    if p.name not in referenced_procs:
        # 手順書間の委譲参照・session-rules/docs からの参照（内部手順）も許容
        used = any(p.name in read(q) for q in procedures if q != p) or (p.name in _extra_text)
        if not used:
            err(f"procedures/{p.name}: どのコマンド・手順からも参照されない孤児")

# --- 4. md 内のプラグイン内パス参照の実在（templates/ references/ docs/ agents/） ---
md_files = list(ROOT.glob("commands/*.md")) + list(ROOT.glob("procedures/*.md")) + \
    list(ROOT.glob("agents/*.md")) + list(ROOT.glob("docs/*.md")) + \
    list(ROOT.glob("references/**/*.md")) + [ROOT / "README.md"]
pat = re.compile(r"(?<![\w/.])((?:templates|references|docs|agents)/[\w./-]+\.(?:md|html|yaml|sql|json|txt))")
for f in md_files:
    for ref in set(pat.findall(read(f))):
        if not (ROOT / ref).is_file():
            err(f"{f.relative_to(ROOT)}: 参照切れ {ref}")

# --- 5. agents frontmatter ---
VALID_MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
for a in (ROOT / "agents").glob("*.md"):
    fm = frontmatter(a)
    for key in ("name", "description", "model", "tools"):
        if key not in fm:
            err(f"agents/{a.name}: frontmatter に {key} がない")
    if fm.get("model") and fm["model"] not in VALID_MODELS:
        err(f"agents/{a.name}: model '{fm['model']}' が不正（{VALID_MODELS}）")
    if fm.get("name") and fm["name"] != a.stem:
        err(f"agents/{a.name}: name '{fm['name']}' がファイル名と不一致")

# --- 6. references SKILL.md frontmatter ---
for s in (ROOT / "references").glob("*/SKILL.md"):
    fm = frontmatter(s)
    for key in ("name", "description"):
        if key not in fm:
            err(f"{s.relative_to(ROOT)}: frontmatter に {key} がない")
    if fm.get("name") and fm["name"] != s.parent.name:
        err(f"{s.relative_to(ROOT)}: name '{fm.get('name')}' がディレクトリ名と不一致")

# --- 7. 台帳（command-registry）との件数突合 ---
# 台帳の行形式: | takumi-<name> | <日本語コマンド名> | ドメイン | Pack | 言い方 |
reg = read(ROOT / "docs/command-registry.md")
reg_rows = re.findall(r"^\| (takumi-[a-z-]+) \| ([^|]+?) \|", reg, re.M)
reg_jp = {jp.strip() for _, jp in reg_rows if not jp.strip().startswith("（内部")}
reg_en = {en for en, _ in reg_rows}
fs_cmds = {c.stem for c in commands}
fs_procs = {p.stem for p in procedures}
if fs_cmds - reg_jp:
    err(f"command-registry.md: 台帳に載っていないコマンド {sorted(fs_cmds - reg_jp)}")
if reg_jp - fs_cmds:
    err(f"command-registry.md: 実体のない台帳記載 {sorted(reg_jp - fs_cmds)}")
if reg_en - fs_procs:
    err(f"command-registry.md: 手順書が実在しない台帳記載 {sorted(reg_en - fs_procs)}")
if fs_procs - reg_en:
    err(f"command-registry.md: 台帳に載っていない手順書 {sorted(fs_procs - reg_en)}")

# --- 8. 旧 delve-* 名の残骸チェック（takumi-* 全面リネーム後、delve- は一切残らない。TESTING.md は履歴として除外） ---
OLD_NAME = re.compile(r"\bdelve-[a-z]", re.I)
for f in list(ROOT.glob("commands/*.md")) + list(ROOT.glob("procedures/*.md")) + \
         list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("references/**/*.md")) + \
         [ROOT / "README.md", ROOT / "hooks/scripts/session-rules.txt"]:
    if not f.is_file():
        continue
    if OLD_NAME.search(read(f)):
        err(f"{f.relative_to(ROOT)}: 旧 'delve-*' 手順名が残存（takumi-* にリネームすること）")

# --- 9. ファイル内の異常重複（同一の長い行が3回以上 = 一括置換バグの兆候） ---
import collections as _coll
for f in list(ROOT.glob("commands/*.md")) + list(ROOT.glob("procedures/*.md")) +          list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("agents/*.md")) +          list(ROOT.glob("references/**/*.md")):
    cnt = _coll.Counter(
        l.strip() for l in read(f).splitlines()
        if len(l.strip()) > 60 and not l.strip().startswith(("|---", "```", "#", ">", "-"))
    )
    for line, n in cnt.items():
        if n >= 3:
            err(f"{f.relative_to(ROOT)}: 同一行が{n}回重複（一括置換バグの疑い）: {line[:40]}…")

# --- 10. 旧 Delvework 識別子の残骸チェック（環境変数・DBファイル名・ゲート表示名。
#         世界観語としての「Delvework/Forgecraft」は下り工程の内部所作として保持するため、
#         ここで禁じるのは機械的な識別子のみ。TESTING.md は過去ログのため除外） ---
OLD_IDENTS = [
    (re.compile(r"\bDELVEWORK_[A-Z_]+"), "旧環境変数 DELVEWORK_*（TAKUMI_* にリネームすること）"),
    (re.compile(r"\bdelvework\.db\b"), "旧DBファイル名 delvework.db（takumi.db にリネームすること）"),
    (re.compile(r"\bdelve コマンド"), "旧コマンド呼称『delve コマンド』（takumi コマンド にリネームすること）"),
    (re.compile(r"Delvework"), "旧プラグイン名 Delvework（TAKUMI-CMO にリネームすること。"
                               "世界観語としての用法は WORLDVIEW_OK の正本のみ）"),
]
# 旧名を書いてよい例外は2種類だけ:
#  (a) 世界観語「Delvework（掘る）／Forgecraft（鍛える）」を定義する正本
#  (b) 「旧名が出たら FAIL」を検証項目として明記する検証の正本（旧名を名指しできないと項目が書けない）
IDENT_EXEMPT = {
    "docs/command-registry.md", "docs/parts/index.md",          # (a)
    "procedures/takumi-verify.md", "templates/verify-task.yaml",  # (b) V43
}
ident_targets = (
    list(ROOT.glob("hooks/scripts/*")) + list(ROOT.glob("scripts/*"))
    + list(ROOT.glob("templates/*")) + list(ROOT.glob("commands/*.md"))
    + list(ROOT.glob("procedures/*.md")) + list(ROOT.glob("docs/**/*.md"))
    + list(ROOT.glob("agents/*.md")) + list(ROOT.glob("references/**/*.md"))
    + [ROOT / "README.md"]
)
for f in ident_targets:
    rel = str(f.relative_to(ROOT)) if f.is_file() else ""
    if not f.is_file() or f.name == "lint.py":
        continue
    try:
        body = read(f)
    except UnicodeDecodeError:
        continue
    for pat, msg in OLD_IDENTS:
        # 例外は「旧DBファイル名」「旧プラグイン名」の2パターンのみ。
        # 環境変数（DELVEWORK_*）と旧コマンド呼称は例外ファイルでも禁止のまま。
        if rel in IDENT_EXEMPT and pat.pattern in (r"\bdelvework\.db\b", "Delvework"):
            continue
        if pat.search(body):
            err(f"{rel}: {msg}")

# --- 結果 ---
print(f"lint: commands={len(commands)} procedures={len(procedures)} "
      f"agents={len(list((ROOT/'agents').glob('*.md')))} skills={len(list((ROOT/'references').glob('*/SKILL.md')))} "
      f"version={plugin['version']}")
for w in warns:
    print(f"WARN: {w}")
if errors:
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1)
print("lint: OK")
