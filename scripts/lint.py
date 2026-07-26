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

# --list: チェックの一覧を番号・行番号つきで出す。
# 番号で他所を指す設計なので、**番号から実体に飛べる手段**が要る（引数なしなら通常の検査）。
if "--list" in sys.argv:
    _src = (ROOT / "scripts/lint.py").read_text(encoding="utf-8")
    for _i, _line in enumerate(_src.splitlines(), 1):
        _m = re.match(r"^# --- (\d+[a-z]?|結果)\.?\s*(.*?)\s*(?:---)?$", _line)
        if _m and _m.group(1) != "結果":
            print(f"  #{_m.group(1):<4} lint.py:{_i:<5} {_m.group(2)[:78]}")
    sys.exit(0)

errors: list[str] = []
warns: list[str] = []

# 追記された順に残す履歴ログ。**当時の名称のまま**が正しいので、
# 「現行の名前と一致しているか」を見る検査からは一律で外す
# （旧コマンド名・旧プラグイン名・廃止ファイルへの言及は、ここでは違反ではなく記録）。
_HISTORY_FILES = {"TESTING-HISTORY.md"}
# 記録ファイル: **壊れていた形をそのまま引用するのが仕事**なので、
# 「壊れた書き方を見つける」種類の検査（#40 併記の潰れ / #41 宙吊り参照 / #42 書き写し）から外す。
# 規約違反そのものを見る検査（#36 など）は履歴だけを外し、TESTING.md は対象に残す
# （最新ランの記述は現行の規約に従わせたい）。
_RECORD_FILES = _HISTORY_FILES | {"TESTING.md"}


def err(msg: str) -> None:
    errors.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def skill_names() -> set[str]:
    """実在するスキル名の集合（ディレクトリ名 = スキル名）。"""
    return {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}


def preloaded_skills(p: Path) -> set[str]:
    """エージェントの `skills:` preload に載っている名前。

    frontmatter() は行単位の素朴なパーサでリスト値を持てないので、
    preload だけは専用に取り出す（#21 と #34 が同じ正規表現を持っていたのを1本化）。
    """
    m = re.search(r"^skills:\s*$\n((?:\s+-\s+\S+\n)+)", read(p), re.M)
    return set(re.findall(r"-\s+(\S+)", m.group(1))) if m else set()


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

# --- 4. md 内のプラグイン内パス参照の実在
#        （2026-07-26 拡張: 対象が templates/ skills/ docs/ agents/ だけで、**手順書・hook・
#         スクリプトへの参照は検査対象外**だった。手順書の改名や hook の追加で
#         リンクが切れても lint は緑のまま通る穴だったので、実行物側も対象に入れる） ---
md_files = list(ROOT.glob("commands/*.md")) + list(ROOT.glob("procedures/*.md")) + \
    list(ROOT.glob("agents/*.md")) + list(ROOT.glob("docs/*.md")) + \
    list(ROOT.glob("skills/**/*.md")) + [ROOT / "README.md"]
pat = re.compile(
    r"(?<![\w/.])((?:templates|skills|docs|agents|procedures|hooks|scripts|tests|takumi)"
    r"/[\w./-]+\.(?:md|html|yaml|sql|json|txt|sh|py))")
for f in md_files:
    for ref in set(pat.findall(read(f))):
        if not (ROOT / ref).is_file():
            err(f"{f.relative_to(ROOT)}: 参照切れ {ref}")

# --- 5. agents frontmatter ---
# model は**エイリアスのみ**。フルモデルID（claude-opus-5 等）はバージョン固定であり、
# そのモデルが退役した日に該当エージェントが止まる（プラグインは配布物なので開発側では気づけない）。
# 一次情報:「エイリアスはプロバイダごとの推奨バージョンを指し、時間とともに更新される。
# 特定バージョンに固定したい場合はフルモデル名を使う」（model-config）。
# → 固定したくないので、ここで弾く。級との対応は #21 が docs/agent-tiers.md と突合する。
VALID_MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
for a in (ROOT / "agents").glob("*.md"):
    fm = frontmatter(a)
    for key in ("name", "description", "model", "tools"):
        if key not in fm:
            err(f"agents/{a.name}: frontmatter に {key} がない")
    if fm.get("model") and fm["model"] not in VALID_MODELS:
        err(f"agents/{a.name}: model '{fm['model']}' が不正（{sorted(VALID_MODELS)}）。"
            "**フルモデルIDの直書きはバージョン固定であり、そのモデルが退役した日に止まる** — "
            "エイリアスで書けばモデル世代の更新に自動で追従する")
    if fm.get("name") and fm["name"] != a.stem:
        err(f"agents/{a.name}: name '{fm['name']}' がファイル名と不一致")

# --- 6. skills SKILL.md frontmatter ---
for s in (ROOT / "skills").glob("*/SKILL.md"):
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
         list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("skills/**/*.md")) + \
         [ROOT / "README.md", ROOT / "hooks/scripts/session-rules.txt"]:
    if not f.is_file():
        continue
    if OLD_NAME.search(read(f)):
        err(f"{f.relative_to(ROOT)}: 旧 'delve-*' 手順名が残存（takumi-* にリネームすること）")

# --- 9. ファイル内の異常重複（同一の長い行が3回以上 = 一括置換バグの兆候） ---
import collections as _coll
for f in list(ROOT.glob("commands/*.md")) + list(ROOT.glob("procedures/*.md")) +          list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("agents/*.md")) +          list(ROOT.glob("skills/**/*.md")):
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
    "procedures/takumi-verify.md",  # (b) V43
}
ident_targets = (
    list(ROOT.glob("hooks/scripts/*")) + list(ROOT.glob("scripts/*"))
    + list(ROOT.glob("templates/*")) + list(ROOT.glob("commands/*.md"))
    + list(ROOT.glob("procedures/*.md")) + list(ROOT.glob("docs/**/*.md"))
    + list(ROOT.glob("agents/*.md")) + list(ROOT.glob("skills/**/*.md"))
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

# --- 11. 旧プラグイン名 browser-worker のパス参照（別プラグインの実体を読む事故の元。
#         2026-07-24 実機検証 F1: 旧 browser-worker が併存インストールされた環境で顕在化） ---
BW_EXEMPT = {
    "templates/task-template.yaml",      # 移植元の由来メモ
    "procedures/takumi-status.md",       # 併存環境での取り違え注意として意図的に名指し
}
for f in (list(ROOT.glob("agents/*.md")) + list(ROOT.glob("procedures/*.md"))
          + list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("commands/*.md"))
          + list(ROOT.glob("templates/*")) + [ROOT / "README.md"]):
    if not f.is_file():
        continue
    rel = str(f.relative_to(ROOT))
    if rel in BW_EXEMPT:
        continue
    try:
        if "browser-worker" in read(f):
            err(f"{rel}: 旧プラグイン名 browser-worker への参照（takumi-cmo にすること。"
                f"併存インストール環境で別プラグインの実体を読む事故になる）")
    except UnicodeDecodeError:
        pass

# --- 12. 廃止カテゴリーがテンプレの見本データに残っていないか
#         （2026-07-24 実機検証 F3: ダッシュボード雛形に求人媒体・広告分析タブが残存） ---
for f in ROOT.glob("templates/*"):
    if not f.is_file():
        continue
    try:
        body = read(f)
    except UnicodeDecodeError:
        continue
    for word in ("求人媒体", "広告分析"):
        if word in body:
            err(f"templates/{f.name}: 廃止カテゴリー『{word}』が残存"
                f"（現行カテゴリーは docs/command-registry.md が正本）")

# --- 13. skills の本数を書いた記述が実体と一致するか（2026-07-24 実機検証 F5） ---
_ref_count = len(list((ROOT / "skills").glob("*/SKILL.md")))
_ref_pat = re.compile(r"skills/(?:（|\s*全)(\d+)本")  # 「skills/（20本）」「skills/ 全20本」の両方
for f in list(ROOT.glob("procedures/*.md")) + list(ROOT.glob("docs/**/*.md")) + [ROOT / "README.md"]:
    if not f.is_file():
        continue
    for m in _ref_pat.finditer(read(f)):
        if int(m.group(1)) != _ref_count:
            err(f"{f.relative_to(ROOT)}: skills の本数が実体と不一致"
                f"（記述={m.group(1)} / 実体={_ref_count}）")

# --- 13b. コマンド・手順書の本数を書いた記述が実体と一致するか
#          （2026-07-25 検出: 台帳に「登録13本」「内部手順 17 / 手順書 30」と書かれたまま
#           コマンドが 16 本に増えていた。#13 は skills だけを見ており、他は素通りだった） ---
_n_cmd = len(commands)
_n_proc = len(procedures)
# 内部手順 = 手順書 - コマンド台帳に載っている公開手順書。
# （2026-07-26: 20本→9本に束ねるまでは 1コマンド=1手順書だったので 手順書-コマンド で
#  正しかったが、1コマンドが複数手順書を束ねる今は成り立たない）
_n_public_proc = len({en for en, jp in reg_rows if not jp.strip().startswith("（内部")})
_n_internal_proc = _n_proc - _n_public_proc
_COUNT_PATTERNS = [
    (re.compile(r"登録コマンド (\d+) 本"), lambda: _n_cmd, "登録コマンド"),
    (re.compile(r"コマンド台帳（登録(\d+)本）"), lambda: _n_cmd, "登録コマンド"),
    (re.compile(r"`commands/`（登録(\d+)本"), lambda: _n_cmd, "登録コマンド"),
    (re.compile(r"メニューに並ぶのはこの(\d+)本"), lambda: _n_cmd, "登録コマンド"),
    (re.compile(r"内部手順含め(\d+)本"), lambda: _n_proc, "手順書"),
    (re.compile(r"内部手順 (\d+) / 手順書 (\d+)"), lambda: (_n_internal_proc, _n_proc), "内部手順/手順書"),
    # 2026-07-25 の攻めスキル追加時に検出: 助数詞の「本」やスペースが無い書き方が
    # 上のパターンを全部すり抜け、takumi-verify.md V17/V34 が 13/30 のまま残っていた。
    # 「規約は機械検査とセット」の原則どおり、見つけた形は必ずパターンに足す。
    (re.compile(r"登録コマンド(\d+)（commands/）\+ 内部手順(\d+) = 手順書(\d+)"),
     lambda: (_n_cmd, _n_internal_proc, _n_proc), "登録/内部手順/手順書"),
    (re.compile(r"procedures/ 全(\d+)本"), lambda: _n_proc, "手順書"),
]
for f in list(ROOT.glob("procedures/*.md")) + list(ROOT.glob("docs/**/*.md")) + [ROOT / "README.md"]:
    if not f.is_file():
        continue
    body = read(f)
    for pat, expected, label in _COUNT_PATTERNS:
        for m in pat.finditer(body):
            exp = expected()
            got = tuple(int(g) for g in m.groups())
            want = exp if isinstance(exp, tuple) else (exp,)
            if got != want:
                err(f"{f.relative_to(ROOT)}: {label} の本数が実体と不一致"
                    f"（記述={got} / 実体={want}）— 台帳の件数は実体を数えて書く")

# --- 14. docs/parts/ の実体と index.md の突合（2026-07-25 合議で検出: parts は台帳突合の対象外だった） ---
_parts_dir = ROOT / "docs/parts"
if _parts_dir.is_dir():
    _index = ROOT / "docs/parts/index.md"
    _index_text = read(_index) if _index.is_file() else ""
    for f in sorted(_parts_dir.glob("*.md")):
        if f.name == "index.md":
            continue
        if f.name not in _index_text:
            err(f"docs/parts/index.md: 部品 {f.name} が地図に載っていない（新設したら index.md に1行追加すること）")
    # 逆方向: index が挙げる部品名の実在。docs/直下の正本（media-pipeline.md 等）と
    # ワークスペース側のファイル（queue.md 等）は部品ではないので除外する
    _not_parts = {"index.md", "queue.md", "lessons.md", "pending.md"}
    for ref in sorted(set(re.findall(r"\b([a-z0-9-]+\.md)\b", _index_text))):
        if ref in _not_parts or (ROOT / "docs" / ref).is_file():
            continue
        if not (_parts_dir / ref).is_file():
            err(f"docs/parts/index.md: 実体のない部品を参照 {ref}")

# --- 15. domain-model.md の宣言と takumi/domain・tests の実体を突合
#         （2026-07-25 全体CHECK で検出: Strategy/Campaign/Loop が「Phase 3/4 で実装」と
#          書かれたまま実体もテストも存在しなかった。宣言だけが先行する負債を機械で止める） ---
_dm = ROOT / "docs/domain-model.md"
if _dm.is_file():
    _dm_text = read(_dm)
    _domain_src = "".join(read(p) for p in sorted((ROOT / "takumi/domain").glob("*.py")))
    _defined = set(re.findall(r"^class\s+([A-Za-z_]\w*)", _domain_src, re.M))

    def _table(heading: str) -> list[list[str]]:
        """`## <heading>` 直下の md テーブルの本文行を列リストで返す。"""
        m = re.search(rf"^##+ {re.escape(heading)}.*?$(.*?)(?=^##\s|\Z)", _dm_text, re.M | re.S)
        if not m:
            err(f"docs/domain-model.md: 見出し『{heading}』が見つからない（正本の構造が変わった）")
            return []
        rows = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line.startswith("|") or set(line) <= set("|- "):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if cols and cols[0] in ("対象", "日本語（ユビキタス）"):
                continue  # ヘッダ行
            rows.append(cols)
        return rows

    # (a) 実装状況表: 宣言したクラスが takumi/domain に実在し、宣言したテストが実在するか
    _impl_ids: set[str] = set()
    for cols in _table("実装状況"):
        if len(cols) < 3:
            continue
        target, state, tests = cols[0], cols[1], cols[2]
        ids = re.findall(r"`([A-Za-z_]\w*)`", target)
        _impl_ids.update(ids)
        # 「コード化しない」と明記した行はランタイム側の表現なので実体を要求しない
        if "コード化しない" in state:
            if re.search(r"`tests/[\w./-]+`", tests):
                err(f"docs/domain-model.md 実装状況: 『{target}』は"
                    f"コード化しない宣言なのにテストを宣言している（どちらかに寄せること）")
            continue
        for cid in ids:
            if cid not in _defined:
                err(f"docs/domain-model.md 実装状況: `{cid}` を実装済みと宣言しているが "
                    f"takumi/domain/*.py に class 定義がない（宣言だけが先行している）")
        for tp in re.findall(r"`(tests/[\w./-]+\.py)`", tests):
            if not (ROOT / tp).is_file():
                err(f"docs/domain-model.md 実装状況: 宣言されたテスト {tp} が存在しない")
        if not re.search(r"`tests/[\w./-]+\.py`", tests) and ids:
            err(f"docs/domain-model.md 実装状況: 『{target}』にテストの宣言がない"
                f"（TDD: 集約にはテストを紐づける）")

    # (b) ユビキタス言語表のコード名が実装状況表に必ず現れる（Task/Channel の取りこぼし防止）
    for cols in _table("ユビキタス言語 ↔ コードの対応"):
        if len(cols) < 2:
            continue
        for cid in re.findall(r"`([A-Za-z_]\w*)`", cols[1]):
            if cid not in _impl_ids:
                err(f"docs/domain-model.md: ユビキタス言語 `{cid}` が実装状況表にない"
                    f"（実装するか『コード化しない』と明記すること）")

    # (c) 逆方向: takumi/domain に実在する公開クラスが正本に載っているか
    for cid in sorted(_defined):
        if cid.startswith("_"):
            continue
        if f"`{cid}`" not in _dm_text:
            err(f"docs/domain-model.md: takumi/domain の `{cid}` が正本に載っていない"
                f"（ユビキタス言語と1対1にすること）")

# --- 16. ワークスペース検証（利用者の knowledge/brands/** をドメインモデルで検証）---
#     プラグインリポジトリ単体では knowledge/ が無いので何も起きない。
#     Cowork のワークスペースで回すと、台帳・区画・KPIツリー・キャンペーンの不変条件を実データに適用する。
#     対象は既定でカレントディレクトリ。`--workspace <path>` で明示指定できる。
_ws_arg = None
if "--workspace" in sys.argv:
    _i = sys.argv.index("--workspace")
    if _i + 1 < len(sys.argv):
        _ws_arg = Path(sys.argv[_i + 1])
    else:
        err("--workspace にパスが指定されていません")
_ws = _ws_arg if _ws_arg is not None else Path.cwd()
if (_ws / "knowledge").is_dir():
    try:
        import yaml  # type: ignore
    except ImportError:
        warns.append(
            f"ワークスペース検証をスキップ（PyYAML が無い）: {_ws}"
            f" — `pip install pyyaml` で有効になる"
        )
    else:
        sys.path.insert(0, str(ROOT))
        from takumi.workspace import validate_workspace

        def _load_yaml(p: Path):
            return yaml.safe_load(p.read_text(encoding="utf-8"))

        _ws_errors = validate_workspace(_ws, _load_yaml)
        for e in _ws_errors:
            err(f"[ワークスペース] {e}")
        if not _ws_errors:
            print(f"lint: ワークスペース検証 OK（{_ws}）")

# --- 17. evals.md の golden タスクが全スキル・全エージェントを覆っているか
#         （2026-07-25 全体CHECK で検出: skills 20本中16本・agents 9体中6体が未収載のまま
#          「新しい失敗事例が出たら追加する」という運用規約だけが書かれていた） ---
_evals = ROOT / "docs/evals.md"
if _evals.is_file():
    _evals_text = read(_evals)
    # 行形式: | G<n> | <対象>: <依頼内容> | <PASS基準> |
    # 対象を持たない行（ルーティング系など）は覆う側に数えないだけで、違反ではない。
    _covered = {
        m.group(1)
        for m in re.finditer(r"^\|\s*G\d+\s*\|\s*([a-z0-9-]+):", _evals_text, re.M)
    }
    _skill_names = skill_names()
    _agent_names = {a.stem for a in (ROOT / "agents").glob("*.md")}
    for name in sorted(_skill_names - _covered):
        err(f"docs/evals.md: スキル {name} の golden タスクがない"
            f"（新設したら評価タスクも1つ書く。腕落ちを測る手段が無くなる）")
    for name in sorted(_agent_names - _covered):
        err(f"docs/evals.md: エージェント {name} の golden タスクがない"
            f"（新設したら評価タスクも1つ書く。腕落ちを測る手段が無くなる）")
    # 逆方向: 実在しない対象を指す golden タスク
    for name in sorted(_covered - _skill_names - _agent_names):
        err(f"docs/evals.md: golden タスクが実在しない対象 {name} を指している")

# --- 18. 検証項目（V番号）の内部整合
#         （2026-07-26 改訂。以前は `templates/verify-task.yaml` に同じ項目を転記し、
#          両ファイルの集合一致を検査していた。だが**利用者に yaml を業務フォルダへ
#          コピーさせる運用そのものが設計の不足**（プラグインは指示だけで動くべき）なので
#          yaml を廃止し、`procedures/takumi-verify.md` を唯一の正本にした。
#          転記が無くなったので突合も要らず、代わりに**1ファイル内で壊れうること**を見る:
#          番号の重複・抜け番・判定基準の欠落） ---
_vfile = ROOT / "procedures/takumi-verify.md"
if _vfile.is_file():
    _vtext = read(_vfile)
    # 定義行: | V<n> [🔁] | <項目名> | <手順> | <期待> 。報告書の書式見本（2列目が "..."）は定義ではない
    _rows = re.findall(r"^\| (V\d+)( 🔁)? \| ([^|]*)\|([^|]*)\|([^|]*)\|", _vtext, re.M)
    _defs = [r for r in _rows if r[2].strip() != "..."]
    if not _defs:
        err("procedures/takumi-verify.md: 検証項目（| V<n> | …）が1件も無い"
            "（表の書式を変えたら lint #18 も直すこと。0件で素通りするのが最も危険）")
    else:
        _nums = [int(r[0][1:]) for r in _defs]
        for _v, _n in _coll.Counter(_nums).items():
            if _n > 1:
                err(f"procedures/takumi-verify.md: 検証項目 V{_v} が{_n}回定義されている（V番号は一意）")
        _missing = sorted(set(range(1, max(_nums) + 1)) - set(_nums))
        if _missing:
            err(f"procedures/takumi-verify.md: 検証項目の番号に抜けがある "
                f"{['V%d' % m for m in _missing]}（1..{max(_nums)} の連番で書く。"
                f"抜け番があると「その項目は落ちたのか、元から無いのか」が分からない）")
        if not any(r[1] for r in _defs):
            err("procedures/takumi-verify.md: 重点回帰セット（🔁）が1件も無い"
                "（quick モードで回す集合が空になる）")
        for _r in _defs:
            if not _r[4].strip() or not _r[3].strip():
                err(f"procedures/takumi-verify.md: {_r[0]} に手順または判定基準が書かれていない"
                    f"（**判定できない検証項目を作らない**。PASS/FAIL の分かれ目を必ず書く）")

# --- 19. 主要ディレクトリが空でないこと
#         （2026-07-25 references→skills 移設時に検出: ディレクトリ名を変えると
#          集合を舐める検査（#6/#13/#17）が空集合になり、素通りで lint OK が出てしまった。
#          「0件だから違反も0件」は最も危険な緑） ---
for _name, _pattern, _min in (
    ("commands", "commands/*.md", 6),
    ("procedures", "procedures/takumi-*.md", 25),
    ("agents", "agents/*.md", 5),
    ("skills", "skills/*/SKILL.md", 15),
    ("hooks", "hooks/scripts/*.sh", 8),
    ("docs/parts", "docs/parts/*.md", 15),
):
    _n = len(list(ROOT.glob(_pattern)))
    if _n < _min:
        err(f"{_name}: {_n}件しか見つからない（最低 {_min} 件のはず）。"
            f"ディレクトリ名の変更・移動で検査が空振りしている可能性がある")

# --- 20. スキルの接続（孤島と行き止まりを作らない）
#         （2026-07-26 の実測で検出: 参照を数えたら「どのスキルからも指されないスキル」が2本、
#          「他スキルへ一切つながらないスキル」が3本あった。原因は新設時に兄弟スキル側へ
#          張り返していないこと。文章の規約では必ず再発するので機械で止める。
#          正本は docs/skill-map.md） ---
_skill_map = ROOT / "docs" / "skill-map.md"
_skill_dirs = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
if not _skill_map.is_file():
    err("docs/skill-map.md が無い（スキル接続の正本）")
elif _skill_dirs:
    _map_text = read(_skill_map)
    _body: dict[str, str] = {}
    for _name in _skill_dirs:
        _t = read(ROOT / "skills" / _name / "SKILL.md")
        _parts = _t.split("---", 2)
        _body[_name] = _parts[2] if len(_parts) > 2 else _t

    _out = {n: {o for o in _skill_dirs if o != n and o in _body[n]} for n in _skill_dirs}
    _in = {n: {a for a in _skill_dirs if n in _out[a]} for n in _skill_dirs}

    for _name in _skill_dirs:
        if "## 接続" not in _body[_name]:
            err(f"skills/{_name}/SKILL.md: `## 接続` セクションが無い"
                "（前段／後段／併用を書く。正本は docs/skill-map.md）")
        if len(_out[_name]) < 2:
            err(f"skills/{_name}/SKILL.md: 他スキルへのリンクが {len(_out[_name])} 本しかない"
                "（**行き止まり**。開いた人が次に進めない。2本以上つなぐこと）")
        if not _in[_name]:
            err(f"skills/{_name}: どのスキルからも参照されていない（**孤島**）。"
                "手順書から到達できても、スキルを開いた人はここへ辿り着けない。"
                "前段になるスキルの `## 接続` の後段に、このスキルを足すこと")
        if f"`{_name}`" not in _map_text:
            err(f"docs/skill-map.md: skills/{_name} が接続図に載っていない")
        for _ref in set(re.findall(r"skills/([a-z0-9-]+)", _body[_name])):
            if _ref not in _skill_dirs:
                err(f"skills/{_name}/SKILL.md: 存在しないスキル `skills/{_ref}` を参照している")

# --- 21. エージェントの級（model / effort / skills preload）
#         （2026-07-26 導入。正本は docs/agent-tiers.md。
#          一次情報: プラグイン同梱エージェントは model/effort/skills/maxTurns/tools/
#          disallowedTools/memory/background/isolation のみ。hooks/mcpServers/permissionMode は
#          セキュリティ上サポートされない。effort は Haiku では非対応（公式の対応表に無い）。
#          `skills:` は名前を間違えても**デバッグログに警告が出るだけで静かにスキップされる**ので、
#          実在確認を機械でやる） ---
_tiers = ROOT / "docs" / "agent-tiers.md"
_agent_files = sorted((ROOT / "agents").glob("*.md"))
_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
_UNSUPPORTED_FM = ("hooks", "mcpServers", "permissionMode")
if not _tiers.is_file():
    err("docs/agent-tiers.md が無い（エージェントの級の正本）")
elif _agent_files:
    _tier_text = read(_tiers)
    _skill_names = skill_names()
    for _p in _agent_files:
        _a = _p.stem
        _fm = frontmatter(_p)
        _raw = read(_p)
        _model = _fm.get("model")
        _effort = _fm.get("effort")

        if not _model:
            err(f"agents/{_a}.md: `model` が無い（`inherit` 任せにすると級が意味を失う。"
                "docs/agent-tiers.md の表から取る）")
        elif _model == "haiku":
            if _effort:
                err(f"agents/{_a}.md: `model: haiku` に `effort: {_effort}` が付いている。"
                    "**Haiku は effort 非対応**（公式の対応表に無い）。効かない設定を置かない")
        else:
            if not _effort:
                err(f"agents/{_a}.md: `effort` が無い（`model: {_model}` は effort をサポートする。"
                    "級から決めた値を明示する — 未設定はセッション既定に流されて級が効かない）")
            elif _effort not in _EFFORTS:
                err(f"agents/{_a}.md: `effort: {_effort}` は不正（{'/'.join(sorted(_EFFORTS))}）")

        # 正本の表との突合（| `name` | 級 | `model` | `effort` | … の行）
        _row = re.search(
            rf"^\|\s*`{re.escape(_a)}`\s*\|[^|]*\|\s*`([a-z0-9-]+)`\s*\|\s*`([a-z]+)`\s*\|",
            _tier_text, re.M)
        if not _row:
            err(f"docs/agent-tiers.md: `{_a}` の配役行が無い（級・model・effort を表に載せる）")
        elif _model and (_row.group(1) != _model or (_effort or "") != _row.group(2)):
            err(f"agents/{_a}.md: 実体（{_model}/{_effort}）が docs/agent-tiers.md の表"
                f"（{_row.group(1)}/{_row.group(2)}）と食い違う")

        for _bad in _UNSUPPORTED_FM:
            if re.search(rf"^{_bad}:", _raw, re.M):
                err(f"agents/{_a}.md: `{_bad}:` はプラグイン同梱エージェントでは"
                    "サポートされない（セキュリティ上の制約）。書いても効かない")

        # skills: preload の実在確認（**間違えても静かにスキップされる**ため機械で拾う）
        for _name in sorted(preloaded_skills(_p) - _skill_names):
            err(f"agents/{_a}.md: `skills:` の `{_name}` が実在しない。"
                "**preload は名前を間違えても警告がデバッグログに出るだけで静かに落ちる** "
                "— 規範ゼロで走ることになる")

# --- 22. コマンド × タスクループ の対応表（docs/command-registry.md）
#         （2026-07-26 導入。コマンド→手順書→部品→エージェントの到達を機械で数えたら
#          旧 /エンゲージメント・旧 /カスタマイズ・旧 /ブランド の3本がエージェントに一度も
#          届いていなかった。文章を読んでいるだけでは気づけない種類の穴なので、
#          表を正本にして機械で維持する） ---
_reg_text = read(ROOT / "docs" / "command-registry.md")
_loop_sec = re.search(r"## コマンド × タスクループ.*?(?=\n## )", _reg_text, re.S)
if not _loop_sec:
    err("docs/command-registry.md: 「コマンド × タスクループ」の対応表が無い"
        "（コマンドがループのどのフェーズを回すかの正本）")
else:
    _sec = _loop_sec.group(0)
    _agent_names = {p.stem for p in (ROOT / "agents").glob("*.md")}
    for _c in sorted(p.stem for p in (ROOT / "commands").glob("*.md")):
        if not re.search(rf"^\|\s*/{re.escape(_c)}\s*\|", _sec, re.M):
            err(f"docs/command-registry.md: コマンド /{_c} が「コマンド × タスクループ」表に無い"
                "（**どのフェーズを誰が回すか**を書く。回さないなら「—」と省略の理由を書く）")
    # すべてのエージェントが、どれかのコマンドから到達できること。
    # （スキルの「孤島」検査と同じ形。エージェントを足したのにどのコマンドにも
    #  配線しない＝利用者から一生呼ばれないエージェント、を止める。
    #  名前のタイポも同時に落ちる — 綴りを間違えれば実名が表に無いことになるため）
    for _ag in sorted(_agent_names):
        if _ag not in _sec:
            err(f"docs/agent-tiers.md の `{_ag}` が「コマンド × タスクループ」表のどのコマンドにも"
                "現れない（**どのコマンドからも呼ばれないエージェント**。"
                "配線するか、表に「このコマンドの③を担う」と書くこと）")

# --- 23. hooks の「登録」と「検査」の突合（双方向）
#         （2026-07-26 全体CHECK で検出: hooks.json に登録された11本のうち navigate-warn.sh
#          だけが scripts/test-hooks.sh から一度も実行されておらず、CI が緑でもこの1本は
#          **動作未検査**だった。「登録されている」と「動作が検査されている」は別物であり、
#          hook は追加した瞬間からユーザーの全操作に割り込む。無検査で配布してはいけない） ---
_hook_test = ROOT / "scripts/test-hooks.sh"
if _hook_test.is_file():
    # コメント行は「実行した」ことにならない（言及だけで通ってしまうのを防ぐ）
    _ht_body = "\n".join(l for l in read(_hook_test).splitlines() if not l.lstrip().startswith("#"))
    _registered: set[str] = set()
    for _event, _groups in hooks["hooks"].items():
        for _g in _groups:
            for _h in _g["hooks"]:
                _m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"", _h["command"])
                if _m:
                    _registered.add(Path(_m.group(1)).name)
    for _s in sorted(_registered):
        if _s not in _ht_body:
            err(f"scripts/test-hooks.sh: hook {_s} を一度も実行していない"
                f"（hooks.json に登録済み＝利用者の操作に割り込むのに動作が無検査。"
                f"最低でも「発火する条件」「発火しない条件」の2件を書く）")
    # 逆方向: hooks/scripts/ にあるのに登録も source もされていない置き去りファイル
    _sourced = " ".join(read(p) for p in (ROOT / "hooks/scripts").glob("*.sh"))
    for _p in sorted((ROOT / "hooks/scripts").glob("*.sh")):
        if _p.name not in _registered and _p.name not in _sourced:
            err(f"hooks/scripts/{_p.name}: hooks.json に登録も他スクリプトからの source もされていない"
                f"（動かない置き去りファイル。登録するか消すこと）")

# --- 24. スキルの確からしさ（その数字はどこから来たのか）
#         （2026-07-26 全体CHECK で検出。42スキルのうち10本が確からしさについて何も
#          書いておらず、うち sns-jp は総務省調査由来の利用率6件を**出典なしで**載せていた。
#          出典が無いので**1年古くなっていたことに誰も気づけなかった**（令和6年度→令和7年度）。
#          さらに web-design/resources/lp-cro.md は「CVR最適化の**数値根拠**」と題して
#          改善率を5つ並べながら出典ゼロ — §0b が「特に危ない」と名指しした種類の数値が
#          「根拠」という名前で置かれていた。
#          **SKILL.md だけでなく配下（resources/）も対象**にする。本文が「必読」で開く以上、
#          正本と同じ強さで読まれるため） ---
_PROV_LABELS = ("一次情報", "二次情報", "未確認", "社内基準")
for _sk in sorted((ROOT / "skills").glob("**/*.md")):
    _t = read(_sk)
    _rel = _sk.relative_to(ROOT)
    if not re.search(r"^## 出典", _t, re.M):
        err(f"{_rel}: `## 出典` の節が無い（**外部出典がゼロなら「無い」と書く**。"
            f"【社内基準】として型・経験則であることを明記する。"
            f"空欄は書き忘れと区別がつかない → docs/開発ワークフロー.md §0b-2）")
    elif not any(f"【{_l}" in _t for _l in _PROV_LABELS):
        err(f"{_rel}: `## 出典` にラベルが1つも無い"
            f"（【一次情報・確認済み】【一次情報・出所は特定済み／原文は未取得（要確認）】"
            f"【二次情報・原典未取得】【未確認】【社内基準】のどれかを必ず書く。"
            f"**読み手は外部の事実と社内の型を同じ強さで受け取る** → §0b-2）")

# --- 25. 同じ数字が2箇所にあるとき、片方だけ古くなるのを止める（SNS利用率）
#         （2026-07-26 全体CHECK で検出。social-insight-jp と sns-jp が同じ全年代利用率を
#          持っており、**両方が別の壊れ方をしていた** — sns-jp は値そのものが1年古く
#          （令和6年度）、social-insight-jp は値は新しいのに**出典の年度表記が令和6年度のまま**
#          だった。数字の重複は避けられない（片方は媒体選定表、片方は社会観察の一次情報）ので、
#          **一致することを機械で保証する**） ---
_SNS_PLATFORMS = ("LINE", "YouTube", "Instagram", "X", "TikTok", "Facebook")
_si = ROOT / "skills/social-insight-jp/SKILL.md"
_sj = ROOT / "skills/sns-jp/SKILL.md"
if _si.is_file() and _sj.is_file():
    # 正本: social-insight-jp の「SNS等の利用率（全年代…）」の1項目（次の行まで続く）
    _m = re.search(r"SNS等の利用率（全年代[^）]*）[:：](.+?)(?=\n\s*\n)", read(_si), re.S)
    if not _m:
        err("skills/social-insight-jp/SKILL.md: 「SNS等の利用率（全年代…）」の項目が見つからない"
            "（**この6つの値の正本**。書式を変えたら lint #25 も直すこと）")
    else:
        _src = {p: v for p, v in re.findall(r"\b(LINE|YouTube|Instagram|X|TikTok|Facebook)\s+([\d.]+)%",
                                            _m.group(1))}
        # 引く側: sns-jp のチャネル選定表
        _dst = {p: v for p, v in re.findall(r"^\|\s*(LINE|YouTube|Instagram|X|TikTok|Facebook)\s*\|\s*([\d.]+)%",
                                            read(_sj), re.M)}
        for _p in _SNS_PLATFORMS:
            if _p not in _src:
                err(f"skills/social-insight-jp/SKILL.md: 利用率に {_p} が無い（6媒体そろえる）")
            elif _p not in _dst:
                err(f"skills/sns-jp/SKILL.md: チャネル選定表に {_p} が無い（6媒体そろえる）")
            elif _src[_p] != _dst[_p]:
                err(f"SNS利用率の {_p} が食い違っている: "
                    f"social-insight-jp={_src[_p]}% / sns-jp={_dst[_p]}% "
                    f"（**正本は social-insight-jp §2**。同じ数字が2箇所にあるので、"
                    f"**片方だけ更新すると誰も気づけない** — 実際そうなっていた）")
        # 出典の年度も一致させる（値だけ直して年度表記が古いまま、という壊れ方が実際に起きた）
        for _f, _t in ((_si, read(_si)), (_sj, read(_sj))):
            if "令和7年度" not in _t:
                err(f"{_f.relative_to(ROOT)}: SNS利用率の調査年度（令和7年度）が書かれていない"
                    f"（**値と年度はセットで更新する**。総務省の同調査は毎年6月頃に更新される）")

# --- 26. Tier 2 実機検証の未実施を可視化する（WARN・CI は落とさない）
#         実機検証は人間にしかできない（リリースチェックリスト項目5）。落とすと開発が止まるので
#         WARN に留めるが、「黙って積み上がる」状態は止める。
#         2026-07-25 の全体CHECK 時点で v2.0.0 のまま7リリース分が未検証だった。
#         （2026-07-26 に #20 から #26 へ改番。#20 が「スキルの接続」と重複しており、
#          **番号で他所を指す仕組みなのに番号自体が一意でなかった**。#27 が一意性を検査する。
#          改番して安全だったのは、この番号がどの正本からも引かれていないことを実測したため） ---
#         （2026-07-26 追記: マーカーに `env=` を足した。ローカルランでも配線は測れるが、
#          **配布判断は cloud ランでしか代替できない** — ローカルは hook 配線が環境依存（E4）で、
#          かつ永続フォルダ未接続だと knowledge/ 系が丸ごと測れない。
#          バージョンだけのマーカーでは「ローカルで通ったから配布してよい」と読める余地が残る） ---
#         （2026-07-26 追記2: マーカーに `fail=` を足した。配布判断の規定は
#          「Tier 1 緑 ＋ 直近の Tier 2 が **FAIL 0**」だが、FAIL 件数はどこにも機械可読で無く、
#          **文章でしか書かれていなかった**。第10ラン（v5.5.0）が FAIL 1 を出したことで、
#          「版と env が揃えば緑になる」＝FAIL を積んだまま配布可に見える穴が実際に見えた） ---
#         （2026-07-27 改訂: **`env=cloud` を配布条件から外し、`gates=` と `ws=` に置き換えた**。
#          cloud を要求していた理由は2つあり、**どちらも cloud/ローカルの軸ではなかった**:
#            (a)「ローカルは hook 配線が環境依存（E4）」→ **配線されているかは毎ラン測れる**。
#               env は配線の代理変数にすぎず、E4 の台帳自身が既に
#               「ローカルかどうかで decide せず、毎ラン実際に発火するかを測って判定する」と結論している。
#               **正本の結論と、機械が要求している条件が食い違っていた。**
#            (b)「永続フォルダ未接続だと knowledge/ 系が測れない」→ これは**接続の有無**の軸。
#               cloud でも未接続なら測れないし、ローカルでも接続すれば測れる。
#          実際、第13ラン（cloud）で「cloud でしか出ない」とした3件のうち2件は FUSE の癖で、
#          **第15ラン（ローカル）でも同じ FUSE の rm EPERM が再現した**。残る1件は
#          cloud 由来ですらなく lint #42 が Tier 1 で担保している。
#          **代理変数で測っていたものを、本体で測る。** ローカルでも全ゲートを実測できれば配布判断に使える） ---

# 配布ゲートの分母 = **既定モードが deny の hook**。warn 既定（agent-parallel-gate）は
# 「止まること」を証明できないので分母に入れない。**分母は実体から数える** —
# マーカーに書かれた分母をそのまま信じると、分母を小さく書くだけで「全数実測」に見える。
# SKIP の上限。環境由来の SKIP は実績で 8 件（V8 自然文発火・V16 Slack 未接続・
# V84 `/` メニュー不可視 ＋ ws=no の V11/V14/V18/V19/V49）。それを超える SKIP は
# 「測れなかった」ではなく「測らなかった」を疑う。上げるならこの根拠ごと更新する
_SKIP_MAX = 12

_deny_hooks = []
for _hp in sorted((ROOT / "hooks/scripts").glob("*.sh")):
    _hsrc = read(_hp)
    if not re.search(r'^\s*deny\s+"', _hsrc, re.M):
        continue  # deny を呼ばない（注入のみ）hook は対象外
    _mode_m = re.search(r'^\s*(?:GATE_)?MODE="\$\{[A-Z_]+:-(\w+)\}"', _hsrc, re.M)
    if _mode_m and _mode_m.group(1) != "deny":
        continue  # 既定 warn の試運転ゲート
    _deny_hooks.append(_hp.name)

_testing = ROOT / "TESTING.md"
if _testing.is_file():
    _marker_re = (r"<!--\s*tier2-verified:\s*([0-9.]+)\s+env=(\w+)\s+fail=(\d+)\s+skip=(\d+)"
                  r"\s+gates=(\d+)/(\d+)\s+ws=(\w+)\s*-->")
    _all = re.findall(_marker_re, read(_testing))
    # 正本は1つだけ。複数あると re.search が**最初の1つ**しか読まず、
    # 古いランのマーカーが新しいランを黙って上書きする（過去ラン節にマーカーを残すと起きる）
    if len(_all) > 1:
        err(f"TESTING.md: tier2-verified マーカーが {len(_all)} 個ある（{_all}）— "
            f"**最新ランの節に1つだけ**置く。lint は最初の1つしか読まないので、"
            f"古いマーカーが残っていると実測より緩い判定になる")
    _m = re.search(_marker_re, read(_testing))
    if not _m:
        err("TESTING.md: <!-- tier2-verified: <version> env=<cloud|local> fail=<件数> skip=<件数> "
            "gates=<実測>/<総数> ws=<yes|no> --> マーカーが無い（形式を変えたか？）。"
            "最後に実機検証したバージョン・実行環境・FAIL件数・**SKIP件数**・"
            "**実測できたゲート数**・**ワークスペース接続の有無**を機械可読で持つ。"
            "FAIL件数が無いと『版が揃っている』だけで緑に見え、"
            "ゲート数が無いと『hook が沈黙したまま通った』ランを配布可と読み違え、"
            "**SKIP件数が無いと「測らないことで FAIL 0 を作った」ランを見分けられない**")
    else:
        _ran, _env, _fail = _m.group(1), _m.group(2), int(_m.group(3))
        _skip = int(_m.group(4))
        _gate_hit, _gate_total, _ws = int(_m.group(5)), int(_m.group(6)), _m.group(7)
        if _env not in ("cloud", "local"):
            err(f"TESTING.md: tier2-verified の env={_env} は不正（cloud か local）")
        if _ws not in ("yes", "no"):
            err(f"TESTING.md: tier2-verified の ws={_ws} は不正（yes か no）")
        if _gate_total != len(_deny_hooks):
            err(f"TESTING.md: tier2-verified の gates 分母 {_gate_total} が実体と合わない"
                f"（既定 deny の hook は {len(_deny_hooks)} 本: {', '.join(_deny_hooks)}）— "
                f"**分母を小さく書けば「全数実測」に見えてしまう**ので、"
                f"分母は hooks/scripts/ の実体と一致していなければならない")
        elif _gate_hit > _gate_total:
            err(f"TESTING.md: tier2-verified の gates={_gate_hit}/{_gate_total} は分子が分母を超えている")
        # **FAIL 0 は「測らない」ことで作れる。** 2026-07-26 の第17ラン（v5.9.0）が
        # PASS 34 / FAIL 0 / SKIP 30 で、直前の第16ラン（PASS 67 / FAIL 1 / SKIP 8）の
        # **半分しか測っていないのに、当時の条件（fail=0・gates 全数・同版）をすべて満たした**。
        # 検証者自身は「実挙動は未測定」「黙って PASS にしていない」と申告していたが、
        # **ゲートはその申告を聞く口を持っていなかった**。SKIP 件数を条件に入れる。
        # 閾値は環境由来の SKIP（自然文発火の観測機会なし・Slack 未接続・`/` メニュー不可視・
        # ws=no の5件）を数えた実績値 8 に余裕を足した値。
        if _skip > _SKIP_MAX:
            warns.append(
                f"Tier 2 の最終ラン（v{_ran}）は SKIP が {_skip} 件（上限 {_SKIP_MAX} 件）— "
                f"**FAIL 0 でも配布判断の材料にならない**。"
                f"FAIL 0 は「測らない」ことでも作れるので、**測っていない量そのものを条件にする**。"
                f"環境由来（ws=no・コネクタ未接続・UI 不可視）以外の SKIP を潰してから再ランすること"
            )
        if _fail > 0:
            warns.append(
                f"Tier 2 の最終ラン（v{_ran}）に FAIL が {_fail} 件ある — **配布判断は FAIL 0 が条件**。"
                f" 直したら再ランして fail=0 に更新すること（直した“つもり”では下げない）"
            )
        if _ran != plugin["version"]:
            warns.append(
                f"Tier 2 実機検証が未実施: 最終ラン={_ran}（env={_env}） / 現行={plugin['version']}"
                f" — Cowork（**ローカルで可**）で `/匠検証 full` と言い、結果を TESTING.md に記録して"
                f" マーカーを更新すること（リリースチェックリスト項目5・人間が実行）"
            )
        elif _gate_hit < _gate_total:
            warns.append(
                f"Tier 2 の最終ラン（v{_ran} / env={_env}）で実測できたゲートが"
                f" {_gate_hit}/{_gate_total} — **配布判断は全ゲートの実測が条件**。"
                f" hook の発火は cloud でも保証されない（escalations E5）ので、"
                f" **測っていないゲートは「効いている」と仮定しない**"
                f"（既定 deny の hook: {', '.join(_deny_hooks)}）"
            )
        if _ws != "yes":
            warns.append(
                f"Tier 2 の最終ラン（v{_ran}）はワークスペース未接続（ws=no）— "
                f"**knowledge/ 系を要する項目が測れていない**（V11 ダッシュボード生成 /"
                f" V18・V19 タスク登録と実行連携 / V30 動的コマンド生成 / V31 セットアップ再質問なし）。"
                f"配布は止めないが、これらは**未検証のまま配っている**。"
                f"ローカル Cowork なら永続フォルダを1つ接続すれば測れる"
            )

# --- 27. 番号で他所を指す引用が、実在する番号を指しているか
#         （2026-07-26 全体CHECK で導入。本プロダクトは正本を**番号で**指す箇所が多い —
#          `session-rules (11)`・`Step H`・`lint #23`。**番号は改番・削除で静かにずれる**が、
#          文章としては読めてしまうので気づけない。実際 lint.py 自身の番号が #20 で重複しており、
#          「番号で指す」仕組みの土台が壊れていた。
#          いま全引用が解決することは実測済み。**この検査は「今の正しさ」ではなく
#          「これから壊れないこと」のために置く**） ---
_lint_src = read(ROOT / "scripts/lint.py")
_lint_nums = re.findall(r"^# --- (\d+[a-z]?)\.", _lint_src, re.M)
for _n, _c in _coll.Counter(_lint_nums).items():
    if _c > 1:
        err(f"scripts/lint.py: チェック番号 #{_n} が{_c}回使われている"
            f"（**番号で他所を指す仕組みなので、番号自体が一意でないと引用先が定まらない**）")
_lint_set = set(_lint_nums)

# 番号が昇順に並んでいること（2026-07-26 追加）。
# 番号で他所を指す以上、**ファイルの中でその番号を探せる**必要がある。
# 実際 #16 と #26 が本来の位置から外れており、#26 は #19 より前に置かれていた。
# 番号順に並べておけば、引用された番号から二分探索的に辿れる。
_key = lambda _s: (int(re.match(r"\d+", _s).group()), _s)
if _lint_nums != sorted(_lint_nums, key=_key):
    _first = next(i for i in range(1, len(_lint_nums))
                  if _key(_lint_nums[i]) < _key(_lint_nums[i - 1]))
    err(f"scripts/lint.py: チェック番号が昇順に並んでいない"
        f"（#{_lint_nums[_first - 1]} の次が #{_lint_nums[_first]}）。"
        f"**番号で指す仕組みなので、その番号をファイル内で探せる並びにする**。"
        f"一覧は `python3 scripts/lint.py --list`")

_rules_txt = ROOT / "hooks/scripts/session-rules.txt"
_rule_ids = set(re.findall(r"^\((\d+[a-z]?)\)", read(_rules_txt), re.M)) if _rules_txt.is_file() else set()

_steps_doc = ROOT / "docs/steps-reference.md"
_step_ids = set(re.findall(r"^\|\s*([A-Z])\s*\|", read(_steps_doc), re.M)) if _steps_doc.is_file() else set()

for _f in md_files + [ROOT / "TESTING.md"]:
    if not _f.is_file():
        continue
    _rel, _txt = _f.relative_to(ROOT), read(_f)
    for _r in set(re.findall(r"session-rules\s*\((\d+[a-z]?)\)", _txt)):
        if _rule_ids and _r not in _rule_ids:
            err(f"{_rel}: session-rules ({_r}) は実在しないルール番号"
                f"（`hooks/scripts/session-rules.txt` にある番号だけを引く）")
    for _s in set(re.findall(r"Step ([A-Z])(?![a-z])", _txt)):
        if _step_ids and _s not in _step_ids:
            err(f"{_rel}: Step {_s} は `docs/steps-reference.md` の一覧に無い")
    # lint のチェック番号: 「lint」を含む行の #n だけを見る（PR 番号と混同しない）。
    # **裸の `#N` は lint のチェック番号を意味する**という規約にして曖昧さを消す —
    # 上流の issue は `claude-code#69020` の形（リポジトリ名を前置）で書くこと。
    # 2026-07-27 に escalations E9 で上流 issue 4件を裸の `#N` で書き、
    # **同じ行に「lint #52」もあったため全部が lint 番号として照合された**。
    # 直前が英数字・ハイフン・スラッシュなら他所の番号空間とみなす。
    for _line in _txt.splitlines():
        if "lint" not in _line.lower():
            continue
        for _m in re.finditer(r"(?<![-\w/])(?<!PR )#(\d+[a-z]?)\b", _line):
            if _m.group(1) not in _lint_set:
                err(f"{_rel}: lint のチェック #{_m.group(1)} は `scripts/lint.py` に存在しない"
                    f"（改番・削除で引用が宙に浮いている）")


# --- 28. 束ねた手順書に、コマンドから本当に辿り着けるか
#         （2026-07-26 導入。コマンドを20本→9本に束ねたとき、**入口を消すのと中身を消すのは
#          別物**である。台帳に「このコマンドが束ねている」と書いてあっても、玄関の手順書に
#          振り分けを書き忘れれば、その機能は**誰からも開かれない状態で残る**（ファイルは
#          存在するので参照切れ検査には掛からない＝いちばん気づけない壊れ方）。
#          コマンド → 手順書 → 手順書 … と実際に辿って到達性を確かめる） ---
_proc_text = {p.stem: read(p) for p in procedures}
_reachable: set[str] = set()
_frontier: list[str] = []
for _c in commands:
    for _r in re.findall(r"procedures/(takumi-[a-z-]+)\.md", read(_c)):
        if _r not in _reachable:
            _reachable.add(_r)
            _frontier.append(_r)
while _frontier:
    _cur = _frontier.pop()
    for _r in re.findall(r"procedures/(takumi-[a-z-]+)\.md", _proc_text.get(_cur, "")):
        if _r not in _reachable and _r in _proc_text:
            _reachable.add(_r)
            _frontier.append(_r)
for _en, _jp in reg_rows:
    _jp = _jp.strip()
    if _jp.startswith("（内部"):
        continue
    if _en not in _reachable:
        err(f"procedures/{_en}.md: 台帳では /{_jp} が束ねていることになっているが、"
            f"**コマンドから辿り着けない**（玄関の手順書に振り分けを書く。"
            f"ファイルは在るので参照切れ検査には掛からない＝いちばん気づけない壊れ方）")


# --- 29. コマンド名の規約（接頭辞「匠」＋ 漢語。カタカナ・英字を使わない）
#         （2026-07-26 ユーザー決定。理由は2つ。(a) **他プラグインのコマンドと並んだとき、
#          どれが匠CMO のものか分からなくなる** — 接頭辞が揃っていればメニューで固まって並ぶ。
#          (b) 旧名はカタカナと英字が混ざっていた（リサーチ／エンゲージメント／SNS運用／
#          Webサイト）。**規約は文章で書いてあっても守られない**ので機械で強制する） ---
_KATAKANA = re.compile(r"[\u30A1-\u30FA\u30FC]")
_ASCII_WORD = re.compile(r"[A-Za-z0-9]")
for _c in commands:
    _stem = _c.stem
    if not _stem.startswith("匠"):
        err(f"commands/{_c.name}: コマンド名が「匠」で始まっていない"
            f"（**接頭辞は必須**。他プラグインのコマンドと並んだときに出所が分かるようにするため）")
    _rest = _stem[1:] if _stem.startswith("匠") else _stem
    if _KATAKANA.search(_rest):
        err(f"commands/{_c.name}: コマンド名にカタカナが入っている"
            f"（漢語にする。例: リサーチ→調査 / エンゲージメント→顧客 / セットアップ→設定）")
    if _ASCII_WORD.search(_rest):
        err(f"commands/{_c.name}: コマンド名に英数字が入っている"
            f"（漢語にする。例: SNS運用→発信 / Webサイト→発信）")


# --- 30. スキルは `/` メニューに出さない（user-invocable: false）
#         （2026-07-26 ユーザー報告で検出: コマンドを9本に束ねても、**42本のスキルが
#          スラッシュ一覧に並んで**いた。スキルは規範・知識であって利用者が打つ動作ではない。
#          一次情報（code.claude.com/docs/en/skills「Control who invokes a skill」）:
#          `user-invocable: false` は "Only Claude can invoke the skill. Use this for
#          background knowledge that isn't actionable as a command." であり、
#          **description は context に残るので自動発火は維持される**（一覧から消えるだけ） ---
for _sk in sorted((ROOT / "skills").glob("*/SKILL.md")):
    _fm = frontmatter(_sk)
    if str(_fm.get("user-invocable", "")).strip().lower() != "false":
        err(f"skills/{_sk.parent.name}/SKILL.md: frontmatter に `user-invocable: false` が無い"
            f"（スキルは**規範・知識**であって利用者が打つ動作ではない。"
            f"付けないと `/` の一覧を埋める。**Claude の自動発火は維持される**ので機能は落ちない）")


# --- 31. コマンドの入口の手触り（description / when_to_use / argument-hint）
#         （2026-07-26 導入。一次情報 code.claude.com/docs/en/skills の Frontmatter reference:
#          - `argument-hint`: "Hint shown during **autocomplete** to indicate expected arguments.
#            Example: `[issue-number]` or `[filename] [format]`"
#            → **オートコンプリート行に出る短いヒント**。実際には40〜66字の説明文を入れており、
#              用途を外していた（コマンドを選んだ瞬間に長文が入力欄に出る）
#          - `when_to_use`: "Additional context for when Claude should invoke the skill, such as
#            **trigger phrases or example requests**. Appended to `description` … and counts
#            toward the 1,536-character cap."
#            → 発火語の置き場所は専用フィールドがある
#          - `description`: "**Put the key use case first**" ） ---
_HINT_MAX = 24
_DESC_CAP = 1536
for _c in commands:
    _fm = frontmatter(_c)
    _d = _fm.get("description", "")
    _w = _fm.get("when_to_use", "")
    _h = _fm.get("argument-hint", "")
    if not _h:
        err(f"commands/{_c.name}: argument-hint が無い（引数に何を書けばよいかが分からない）")
    else:
        if not (_h.startswith("[") and _h.endswith("]")):
            err(f"commands/{_c.name}: argument-hint は `[…]` の形にする"
                f"（公式例: `[issue-number]` / `[filename] [format]`）")
        if len(_h) > _HINT_MAX:
            err(f"commands/{_c.name}: argument-hint が長すぎる（{len(_h)}字 > {_HINT_MAX}）"
                f"— **オートコンプリート行に出る短いヒント**であって説明文ではない。"
                f"説明は description に書く")
    if not _w:
        err(f"commands/{_c.name}: when_to_use が無い"
            f"（**発火語（言い方の例）の置き場所は専用フィールド**。description に全部詰めない）")
    if "Use when" not in _d:
        err(f"commands/{_c.name}: description に「Use when」が無い"
            f"（**when_to_use が効かない環境でも主要な言い方で発火できるようにする**ため、"
            f"description 側にも代表的な言い方を残す＝劣化を緩やかにする）")
    if len(_d) + len(_w) > _DESC_CAP:
        err(f"commands/{_c.name}: description + when_to_use が {len(_d)+len(_w)}字で "
            f"{_DESC_CAP} を超える（超過分は一覧で切り捨てられる）")


# --- 32. 定常タスクを黙って殺す設定を入れない（disable-model-invocation 禁止）
#         （2026-07-26 導入。一次情報 code.claude.com/docs/en/scheduled-tasks:
#          "a scheduled fire only runs skills that Claude is allowed to invoke on its own.
#           The following reach Claude as **plain text instead of executing**: …
#           Skills marked `disable-model-invocation: true`"
#          匠CMO の定常運用は発火プロンプトに `/匠計測 …` と書いて回す設計なので、これを付けると
#          **タスクは登録されているのに何も起きない**（エラーも出ず、平文が届くだけ）。
#          最も気づけない壊れ方なので機械で禁じる） ---
for _f in list((ROOT / "commands").glob("*.md")) + list((ROOT / "skills").glob("*/SKILL.md")):
    _v = str(frontmatter(_f).get("disable-model-invocation", "")).strip().lower()
    if _v in ("true", "yes", "on", "1"):
        err(f"{_f.relative_to(ROOT)}: `disable-model-invocation` を付けてはいけない"
            f"（**スケジュール発火で実行されず平文になる**＝定常タスクが登録済みのまま無言で死ぬ。"
            f"`/` の一覧から隠したいだけなら `user-invocable: false` を使う → docs/unattended-ops.md）")

# --- 33. 実在するパック名の正本が3箇所で一致していること
#         （2026-07-26 導入。Tier 2 ローカルラン D-1: session-start.sh は packs.conf の
#          パック名を**検査せずそのまま**「無効:」通知に流していた。打ち間違えると
#          「通知には切れたと出るが実際は切れていない」という、最も気づけない壊れ方になる。
#          hooks 側に名前の正本 packs-known.txt を置いたので、それが
#          ①procedures/takumi-config.md の Pack 定義表 ②procedures/takumi-sns-<媒体>.md の実在
#          と食い違ったまま古びないよう機械で縛る。**正本が3つに増えたのではなく、
#          機械が読める形が1つ増えた**ので、ズレたら落とす） ---
_known_file = ROOT / "hooks" / "scripts" / "packs-known.txt"
if not _known_file.is_file():
    err("hooks/scripts/packs-known.txt が無い（session-start.sh がパック名を検査できない）")
else:
    _known = {ln.strip() for ln in read(_known_file).splitlines()
              if ln.strip() and not ln.strip().startswith("#")}
    _cfg = ROOT / "procedures" / "takumi-config.md"
    _sec = re.search(r"^## Pack 定義.*?^(.*?)^## ", read(_cfg), re.M | re.S) if _cfg.is_file() else None
    _table = ({n for n in re.findall(r"^\|\s*([a-z][a-z0-9-]*)\s*\|", _sec.group(1), re.M)}
              - {"pack"}) if _sec else set()
    if not _table:
        err("procedures/takumi-config.md: 「## Pack 定義」の表からパック名を1つも読めない"
            "（表の形を変えたら packs-known.txt との突合が空振りする）")
    _media = {f"sns-{p.stem.replace('takumi-sns-', '')}"
              for p in (ROOT / "procedures").glob("takumi-sns-*.md")}
    _expected = _table | _media
    for _miss in sorted(_expected - _known):
        err(f"hooks/scripts/packs-known.txt: `{_miss}` が載っていない"
            f"（利用者が正しい名前で off にしても『不明なパック名』と誤って警告される）")
    for _extra in sorted(_known - _expected):
        err(f"hooks/scripts/packs-known.txt: `{_extra}` は実体が無い"
            f"（procedures/takumi-config.md の Pack 定義表にも procedures/takumi-sns-*.md にも無い）")

# --- 34. 判定の根拠にする正本は、Read ではなく preload で届けること
#         （2026-07-26 導入。Tier 2 ローカルラン E-2: **同じ環境でもエージェントによって
#          プラグイン領域の Read が通ったり拒否されたりした**（risk-forecaster/design-critic/
#          deliverable-writer は成功、pre-send-verifier は `outside this session's connected folders`）。
#          preload（skills: frontmatter）は V78 で両者とも効いていた。
#          つまり **Read は当てにできる経路ではなく、preload が唯一の保証**。
#          そこで「本文で必読を指示している skills/<name>」は preload 必須にする。
#          振り分けの案内（→ `skills/x`・併読）は対象外 — 全部載せると文脈を食い潰す） ---
_MUST_READ = ("必ず", "に従い", "に従う", "Read し", "Read する", "読み込み", "審査前に")
for _a in sorted((ROOT / "agents").glob("*.md")):
    _pre = preloaded_skills(_a)
    for _ln in read(_a).splitlines():
        if not any(_m in _ln for _m in _MUST_READ):
            continue
        for _s in re.findall(r"skills/([a-z0-9-]+)", _ln):
            if _s not in _pre:
                err(f"agents/{_a.name}: 本文が `skills/{_s}` の**必読**を指示しているのに "
                    f"`skills:` preload に無い（Read はエージェントによって拒否される — E-2 実測。"
                    f"判定の根拠にするなら preload に載せる。案内だけなら『必ず』『に従い』を外す）")

# --- 35. frontmatter が **本物の YAML として** 妥当か
#         （2026-07-26 導入。上の frontmatter() は行単位の素朴なパーサで、YAML として壊れていても
#          「それらしい dict」を返してしまう。そのせいで agents/design-artisan.md の description に
#          `model: sonnet` と地の文で書かれていた事故を**8日間見逃した** —
#          公式バリデータの言葉では「At runtime this agent loads with **empty metadata**
#          (all frontmatter fields silently dropped)」。model も effort も skills preload も
#          tools 制限も、**全部が無言で捨てられていた**。
#          同じ形の事故が procedures の argument-hint（`[a | b]（…）` が flow sequence の
#          途中で終わる）にも3件あった。CI では公式バリデータも回すが、
#          **手元で python3 scripts/lint.py だけ叩いたときにも落ちる**必要があるのでここでも見る） ---
try:
    import yaml as _yaml
except ImportError:
    _yaml = None
    warns.append("PyYAML が無いので frontmatter の YAML 妥当性を検査できない"
                 "（`pip install pyyaml`。CI では入れてある）")
if _yaml is not None:
    for _f in (sorted((ROOT / "commands").glob("*.md"))
               + sorted((ROOT / "agents").glob("*.md"))
               + sorted((ROOT / "skills").glob("*/SKILL.md"))
               + sorted((ROOT / "procedures").glob("*.md"))):
        _m = re.match(r"^---\n(.*?)\n---\n", read(_f), re.S)
        if not _m:
            continue
        try:
            _parsed = _yaml.safe_load(_m.group(1))
        except Exception as _e:
            err(f"{_f.relative_to(ROOT)}: frontmatter が YAML として壊れている"
                f"（{str(_e).splitlines()[0]}）。**実行時は frontmatter 全体が無言で捨てられる** — "
                f"値に `: ` を含めるなら全体を \" \" で囲む")
            continue
        if not isinstance(_parsed, dict):
            err(f"{_f.relative_to(ROOT)}: frontmatter が辞書にならない"
                f"（{type(_parsed).__name__}）。キー: 値 の形で書く")

# --- 36. `/名前` と書けるのは登録コマンド9本だけ
#         （2026-07-26 導入。v5.0.0 で 20本→9本に束ねたとき、コマンド**ファイル**は lint #29 が
#          守り、台帳には移行表も作ったが、**地の文に残った旧名は誰も掃かなかった**。
#          実害は 2026-07-26 の実機ランで出た — 匠ゲートの deny 文言が
#          「旧 /タスク開始 でタスクを開始し」と、**存在しないコマンドを利用者に指示していた**。
#          スラッシュ表記は「打てば動く」という約束なので、打てないものに使わない。
#          内部手順は手順名（takumi-start）で書く。
#          除外: TESTING.md（履歴ログ。当時の名称のまま残す方針）／台帳の移行表／「旧 /◯◯」表記 ---
_cmd_names = {p.stem for p in (ROOT / "commands").glob("*.md")}
# 2026-07-26: 直前文字の集合に ` を足した。**リポジトリの主流表記は `` `/匠発信` `` であり、
# この検査はそれを一度も見ていなかった**（第12ランで廃止名がバックティック内に3件生き残っていた）。
# `*`（Markdown 太字）は足さない — `Glob **/ファイル名` のようなグロブに誤爆する。
_slash = re.compile(r"(?:(?<=^)|(?<=[\s（(「『`]))/([ぁ-んァ-ヴー一-龠]{2,10})", re.M)
# メタ構文変数（「任意の名前」を表す説明用の綴り）。実在するコマンド名ではないので対象外
_SLASH_PLACEHOLDER = {"名前", "ファイル名", "媒体名"}
for _f in sorted(ROOT.rglob("*")):
    if (not _f.is_file() or ".git" in _f.parts
            or _f.suffix not in (".md", ".sh", ".txt", ".py", ".json")):
        continue
    _rel = _f.relative_to(ROOT).as_posix()
    if _rel in _HISTORY_FILES:
        continue
    _t = read(_f)
    if _rel == "docs/command-registry.md":  # 旧名→新名の移行表は旧名が出て当然
        _t = re.sub(r"### 旧コマンド名からの対応.*?(?=\n## )", "", _t, flags=re.S)
    # 「旧 /素材探し」「旧 `/検証`」は履歴の明示（バックティックで囲む書き方も許す）
    _t = re.sub(r"旧 `?/[ぁ-んァ-ヴー一-龠]{2,10}", "", _t)
    for _mm in _slash.finditer(_t):
        if _mm.group(1) not in _cmd_names and _mm.group(1) not in _SLASH_PLACEHOLDER:
            err(f"{_rel}: `/{_mm.group(1)}` は登録コマンドに無い"
                f"（スラッシュ表記は「打てば動く」約束。登録9本以外は手順名で書く — "
                f"内部手順はスラッシュを付けず takumi-start のように書く。"
                f"旧名を残すなら「旧 」を前に付ける）")

# --- 37. 「◯◯.md の『節名』が正本」と名指しした節が実在するか
#         （2026-07-26 全体CHECK で導入。lint #27 は**番号**で指す引用を守っていたが、
#          **節名**で指す引用は誰も見ていなかった。実際 `rm-guard` / `ov-gate` /
#          `brand-isolation-guard` / `agent-parallel-gate` の4本が
#          「TESTING.md『GATE_MODE 昇格』節が正本」と書いていたのに、**その節は存在しなかった**。
#          ゲートを deny に上げてよい条件という**いちばん慎重に扱うべき手順が、
#          正本を持たないまま4箇所から参照されていた**。
#          内容の引用（「最大2周」など）は対象外 — 「節」「が正本」と明示されたものだけを見る ---
_sec_cite = re.compile(r"([A-Za-z0-9_./-]+\.md)\s*(?:の)?「([^」]{2,40})」\s*(?:節|が正本|の節)")
for _f in sorted(ROOT.rglob("*")):
    if (not _f.is_file() or ".git" in _f.parts
            or _f.suffix not in (".md", ".sh", ".py", ".txt")):
        continue
    _rel = _f.relative_to(ROOT).as_posix()
    if _rel in _HISTORY_FILES:
        continue
    for _mm in _sec_cite.finditer(read(_f)):
        _tgt, _sec = _mm.group(1), _mm.group(2)
        _p = next((c for c in (ROOT / _tgt, _f.parent / _tgt, ROOT / "docs" / _tgt)
                   if c.is_file()), None)
        if _p is None:
            err(f"{_rel}: 「{_sec}」の正本として {_tgt} を指しているが、そのファイルが無い")
            continue
        if not any(_sec in _h for _h in re.findall(r"^#{1,6}\s+(.*)$", read(_p), re.M)):
            err(f"{_rel}: {_tgt} に「{_sec}」という節が無い"
                f"（節名で正本を指すなら、その名前の見出しを実在させる。"
                f"節を改名したら参照元も直す）")

# --- 38. marketplace の plugin source が「URL で追加しても壊れない」形か
#         （2026-07-26 導入。実利用者の Cowork で「マーケットプレイスの更新に失敗しました」が出た。
#          原因は `"source": "./"`（相対パス）。一次情報:
#            「URL ベースの marketplace は **marketplace.json 自体しかダウンロードしない**。
#             サーバ上のプラグインファイルは落とさないので、相対パスは解決できない。
#             URL 配布では GitHub・npm・git URL のソースを使うこと」
#          **ただし実測の結果、明示 github に変えても直URL 追加の install は直らなかった**
#          （`ENOTDIR … scandir .../marketplaces/<name>` は marketplace のキャッシュ位置を
#           走査して落ちており、プラグインの source を見る前段。CLI 側の URL 経路の制約）。
#          それでも相対パスを禁じるのは、**Cowork の marketplace 同期がサーバ側で走り
#          各プラグインの `source.repo` を検証する**ため（上流 issue #61271 の実ログ）。
#          `"./"` には repo が無く、この検証を通れない可能性がある。
#          正しい配布経路（GitHub から marketplace を追加）は add→install→update まで実測済み。
#          詳細は docs/cowork-runtime.md §1b ---
_mkt = json.loads(read(ROOT / ".claude-plugin/marketplace.json"))
for _pl in _mkt.get("plugins", []):
    _src = _pl.get("source")
    if isinstance(_src, str):
        err(f".claude-plugin/marketplace.json: `{_pl.get('name')}` の source が相対パス "
            f"`{_src}`。**URL で marketplace を追加した利用者は install できない**"
            f"（marketplace.json しか落ちてこないので相対パスが解決しない）。"
            f'`{{"source": "github", "repo": "owner/repo"}}` の形にする')
    elif isinstance(_src, dict):
        if _src.get("source") == "github" and not re.fullmatch(r"[\w.-]+/[\w.-]+", _src.get("repo", "")):
            err(f".claude-plugin/marketplace.json: `{_pl.get('name')}` の repo が "
                f"`owner/repo` 形式でない（{_src.get('repo')!r}）")
    else:
        err(f".claude-plugin/marketplace.json: `{_pl.get('name')}` に source が無い")

# --- 39. 検証手順書に書かれた「実体の件数」が、実際の件数と一致しているか
#         （2026-07-26 の第10ラン契機で導入。takumi-verify.md 自身が
#          「この行に固定の数字を書かない — 陳腐化して**網羅したフリ**の温床になる」と
#          書いているのに、手順表の中では固定の数字を書いていた。実際に3つとも陳腐化していた:
#            V32 「9体」  → 実際 10体（1体を回さなくても「全エージェント起動 PASS」になる）
#            V33 「G1〜G9」→ 実際 G1〜G67（**perfect の「evals 全ラン」が 67 件中 9 件だった**）
#            V27 「G1〜G34」→ 実際 G1〜G67
#          数字を消すと「全部」の意味が曖昧になって別の逃げ道になるので、
#          **数字は残して機械で突き合わせる**。片方を直したらもう片方が落ちる） ---
_verify_md = ROOT / "procedures/takumi-verify.md"
if _verify_md.is_file():
    _vtext = read(_verify_md)
    _g_nums = [int(n) for n in re.findall(r"^\|\s*G(\d+)", read(ROOT / "docs/evals.md"), re.M)]
    _counts = [
        (r"`agents/\*\.md` の\*\*全数（現在 (\d+)体）\*\*",
         len(list((ROOT / "agents").glob("*.md"))), "agents/*.md の実体数"),
        (r"G1〜G(\d+)",
         max(_g_nums) if _g_nums else 0, "docs/evals.md の golden 最大番号"),
        (r"docs/parts/ の全部品（(\d+)本",
         len(list((ROOT / "docs/parts").glob("*.md"))) - 1, "docs/parts の部品数（index.md を除く）"),
        (r"skills/ 全(\d+)本",
         len(list((ROOT / "skills").glob("*/SKILL.md"))), "skills/*/SKILL.md の実体数"),
        (r"\*\*procedures/ 全(\d+)本\*\*",
         len(list((ROOT / "procedures").glob("*.md"))), "procedures/*.md の実体数"),
        # gates= の分母。手順書が実測すべき本数を書いており、**これが分母の説明そのもの**なので、
        # 実体（既定 deny の hook）とずれると検証者が少ない数を全数と信じる
        (r"既定 deny の hook 全(\d+)本",
         len(_deny_hooks), "既定モードが deny の hooks/scripts/*.sh の本数"),
    ]
    for _pat, _actual, _what in _counts:
        _hits = {int(m) for m in re.findall(_pat, _vtext)}
        if not _hits:
            err(f"procedures/takumi-verify.md: 件数の記述 `{_pat}` が見つからない"
                f"（{_what} と突き合わせる箇所。書式を変えたら lint #39 も直す）")
        for _n in sorted(_hits - {_actual}):
            err(f"procedures/takumi-verify.md: 件数が実体と合っていない — "
                f"手順書は {_n} と書いているが {_what} は {_actual}。"
                f"**少ない数を書くと「全部やった」が嘘になる**（網羅したフリ）")

# --- 40. 同じコマンド名が1行の中で「併記」されていないか
#         （2026-07-26 の第12ラン V34 で検出。v5.0.0 の 20本→9本統合で、
#          異なる手順書を指していた併記（例「旧 /コンテンツ・旧 /オウンドメディア」）を
#          **すべて `/匠発信` に一括置換した**結果、`/匠発信・/匠発信` という
#          **どちらへ行けばよいか決められない**記述が9箇所残っていた。
#          最悪の形は `procedures/takumi-research.md` の「（/匠発信 /匠発信 /匠発信）」。
#          文章としては読めてしまうので、人間の目視では最後まで見つからなかった。
#          **併記は手順書名で書く**（`/匠発信 ▸ takumi-content`）。
#          離れた位置での再出現（同じ行の別の文で同じコマンドに触れる）は正当なので、
#          **併記記号をはさんで近接している場合だけ**を見る ---
# 近接（14字以内・間に別のコマンドを挟まない）で同じ名前が再出現したら併記とみなす。
# 区切りは「・」「、」空白「または」など多様なので**区切り記号を列挙せず距離で見る**
# （最初の実装は区切り記号を列挙したため、最悪の形「/匠発信 /匠発信 /匠発信」＝空白区切りを取り逃した）。
_dup_cmd = re.compile(r"/([匠][ぁ-んァ-ヴー一-龠]{1,4})[^/\n]{0,14}?/\1(?![ぁ-んァ-ヴー一-龠])")
# 走査は**全 .md**（2026-07-26 の監査で判明: procedures/ と docs/ に限っていたため
# `skills/` に同じ壊れ方が4件残っていた。**検査の網は、壊れ方が起きうる範囲まで広げる**）
for _f in sorted(ROOT.rglob("*.md")):
    _rel = _f.relative_to(ROOT).as_posix()
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    for _line_no, _line in enumerate(read(_f).splitlines(), 1):
        _hit = _dup_cmd.search(_line)
        if _hit:
            err(f"{_rel}:{_line_no}: `/{_hit.group(1)}` が同じ行で併記されている — "
                f"**どの手順書へ行けばよいか決められない**（20本→9本統合の一括置換で潰れた形）。"
                f"`/{_hit.group(1)} ▸ takumi-<手順書名>` のように行き先まで書く")

# --- 41. 地の文が名指しした `*.md` が実在するか
#         （2026-07-26 の第12ラン V34 で検出。docs/parts/design-handoff.md が
#          `notion-publish-rules.md の切り抜き規約` を根拠として指していたが、
#          **そのファイルはリポジトリのどこにも無かった**。
#          既存の参照検査（#14 index.md / #21 skills / #37 節名）は
#          **決まった台帳の中だけ**を見ており、地の文の名指しは誰も見ていなかった） ---
_md_ref = re.compile(r"(?<![\w/.-])([a-z][a-z0-9-]{2,40}\.md)")
_all_md = {p.name for p in ROOT.rglob("*.md")}
# **利用者のワークスペースに生成されるファイル**はプラグイン内に実体が無くて当然。
# ここに載っていない bare な .md 名は「プラグイン内の正本を指した」とみなす。
# 新しいワークスペース生成物を増やしたらここに足す（足さないと ERROR で気づける＝それでよい）。
_WORKSPACE_ARTIFACTS = {
    "lessons.md", "messaging.md", "winning-position.md", "artifacts-index.md",
    "queue.md", "roadmap.md", "strategy.md", "sources.md", "accounts.md",
    "browser.md", "index.md", "session-archive.md", "brand.md",
    "creatives.md", "pending.md",
}
_MD_REF_OK = {"README.md", "SKILL.md", "CLAUDE.md"}
for _f in sorted(ROOT.rglob("*.md")):  # 2026-07-26: 走査を全 .md へ広げた（#40 と同じ理由）
    _rel = _f.relative_to(ROOT).as_posix()
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    for _line_no, _line in enumerate(read(_f).splitlines(), 1):
        if "knowledge/" in _line:  # ワークスペース配下を説明している行は対象外
            continue
        for _name in sorted(set(_md_ref.findall(_line))):
            if (_name in _all_md or _name in _MD_REF_OK
                    or _name in _WORKSPACE_ARTIFACTS):
                continue
            err(f"{_rel}:{_line_no}: 実在しない `{_name}` を名指ししている"
                f"（地の文で根拠として指したファイルは実体が要る。消したなら参照も消す／"
                f"別名にしたなら追随する／ワークスペース生成物なら lint の "
                f"_WORKSPACE_ARTIFACTS に足す）")

# --- 42. 「構造の規定」を正本以外が書き写していないか
#         （2026-07-26 の第13ラン（cloud）で検出。ダッシュボードのタブの切り方について
#          `templates/dashboard-design.md` が「カテゴリー単位（2026-07-22 確定）」と
#          **却下の経緯つきで**書いているのに、`procedures/takumi-dashboard.md` だけが
#          「タスク単位」＝**その経緯で既に却下された設計**のまま取り残されていた。
#          しかも手順書自身が「大原則は templates/dashboard-design.md」と書いており、
#          **正本を指しながら中身も書き写して、書き写したほうが腐っていた**。
#          正本を指すだけなら腐らない。**書き写した瞬間に二重管理になる。** ---
_CANON_ONLY = [
    (r"タブは[^\n]{0,6}単位", "templates/dashboard-design.md", "ダッシュボードのタブの切り方"),
    # 2026-07-27 追加。配布条件は TESTING.md・開発ワークフロー・command-registry・cowork-runtime の
    # **4箇所に書き写されており**、`env=cloud` を外したとき3箇所が古いまま残った（実測）。
    # 条件そのものを書いてよいのは正本だけにして、他は指すだけにする。
    (r"Tier 1 緑 ＋", "TESTING.md", "配布判断の条件"),
]
for _pat, _canon, _what in _CANON_ONLY:
    _holders = []
    for _f in sorted(ROOT.rglob("*.md")):
        _rel = _f.relative_to(ROOT).as_posix()
        # 記録ファイルは「書き写し」の告発対象から外す（過去ランの引用を壊れた形のまま残すため）。
        # ただし**正本自身が記録ファイルのときは必ず読む** — 読み飛ばすと
        # 「正本から規定が消えている」と誤検知し、しかも書き写しの検査が丸ごと無効になる（実測）
        if ".git" in _f.parts or (_rel in _RECORD_FILES and _rel != _canon):
            continue
        if re.search(_pat, read(_f)):
            _holders.append(_rel)
    if _canon not in _holders:
        err(f"{_canon}: {_what} の規定が正本から消えている（`{_pat}` に一致する記述が無い）")
    for _h in _holders:
        if _h != _canon:
            err(f"{_h}: {_what} は `{_canon}` が正本。**書き写さずに指す**"
                f"（書き写すと二重管理になり、写したほうが腐る）")

# --- 43. 解消済みの escalation を「生きた制約」として引用していないか
#         （2026-07-26 の第14ラン（cloud）で検出。E2「ローカルスケジュールを AI から登録できない」は
#          2026-07-26 に一次情報で**解消**が確認され、`unattended-ops.md` と `takumi-task.md` は
#          改訂されたのに、**`cowork-runtime.md` だけが「登録できない（escalations E2）」のまま**だった。
#          解消したのに制約として書かれていると、**できることをやらない**ほうへ実装が引きずられる。
#          引用そのものは禁止しない — 「E2 は解消」と書くのは正しい。
#          **近くに「解消」が無い引用**だけを落とす） ---
_esc = ROOT / "docs/escalations.md"
if _esc.is_file():
    _resolved = re.findall(r"^\| (E\d+) \| \*\*解消", read(_esc), re.M)
    # 近くにこれらの語があれば「もう生きた制約ではない」と読める＝正当な引用
    _RESOLVED_OK = ("解消", "誤り", "撤回", "取り下げ", "だった")
    for _f in sorted(ROOT.rglob("*.md")):
        _rel = _f.relative_to(ROOT).as_posix()
        if ".git" in _f.parts or _rel in _HISTORY_FILES or _rel == "docs/escalations.md":
            continue
        _t = read(_f)
        for _e in _resolved:
            for _m in re.finditer(rf"escalations {_e}\b|（{_e}）|\({_e}\)", _t):
                _near = _t[max(0, _m.start() - 80):_m.end() + 80]
                if any(_w in _near for _w in _RESOLVED_OK):
                    continue
                _line = _t[:_m.start()].count("\n") + 1
                err(f"{_rel}:{_line}: {_e} は**解消済み**なのに制約として引用している"
                    f"（解消したのに制約として書かれていると、**できることをやらない**ほうへ"
                    f"実装が引きずられる。引用するなら「{_e} は解消」と併記する）")

# --- 44. ブランド区画に触れる手順書が「アクティブブランド確定」を書いているか
#         （2026-07-26 の監査で検出。`knowledge/brands/` を読み書きする手順書 17本のうち
#          **`takumi-research` だけ**が、アクティブブランドに一度も言及していなかった。
#          区画外への書き込みは Brand Isolation Guard が deny するので、
#          **前段を書いていない手順書に従うと、止められた側は理由も直し方も分からない**。
#          ゲートがあるから安全、ではない — **止まったときに何をすればよいかを手順書が持つ**べき） ---
for _f in sorted((ROOT / "procedures").glob("*.md")):
    _t = read(_f)
    if "knowledge/brands/" not in _t:
        continue
    if "アクティブブランド" not in _t and "active_brand" not in _t:
        err(f"procedures/{_f.name}: ブランド区画（knowledge/brands/）に触れているのに"
            f"**アクティブブランド確定の前段が無い** — Brand Isolation Guard の deny に当たったとき、"
            f"読み手は理由も直し方も分からない。冒頭に「前段: アクティブブランドを確定する"
            f"（未確定なら `/匠設定`）」を置く")

# --- 45. 出典ラベル（確からしさの申告）が正本の5つだけか
#         （2026-07-26 の監査で検出。`docs/開発ワークフロー.md` は5段階を定義しているのに、
#          実際には**12種類**が使われていた — 「一次情報・入手先」＝「出所は特定済み／原文は未取得」、
#          「二次情報のみ・未確認」＝「二次情報・原典未取得」のような**同義の別綴り**が増えていた。
#          さらに**正本ファイル自身が自分の表と食い違っていた**（L25 が表に無いラベルを使用）。
#          綴りが割れると、**確からしさの申告が読み手にも機械にも数えられなくなる**。
#          補足は許す — 正本のラベルで始めて ` — ` か `（` の後ろに足す形だけ ---
_LABEL_CANON = re.findall(r"^\| \*\*【([^】]+)】\*\*", read(ROOT / "docs/開発ワークフロー.md"), re.M)
if len(_LABEL_CANON) != 5:
    err(f"docs/開発ワークフロー.md: 出典ラベルの正本表が5行でない（{len(_LABEL_CANON)}行）"
        f"— #45 はこの表を正本として読む")
_label_use = re.compile(r"【([^】]*(?:情報|未確認|社内基準)[^】]*)】")
for _f in sorted(ROOT.rglob("*.md")):
    _rel = _f.relative_to(ROOT).as_posix()
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    for _line_no, _line in enumerate(read(_f).splitlines(), 1):
        for _m in _label_use.finditer(_line):
            _used = _m.group(1)
            if any(_used == _c or _used.startswith(_c + " — ") or _used.startswith(_c + "（")
                   for _c in _LABEL_CANON):
                continue
            err(f"{_rel}:{_line_no}: 出典ラベル 【{_used}】 は正本の5つに無い"
                f"（同義の別綴りを作らない — 確からしさの申告が数えられなくなる。"
                f"補足を足すなら `【<正本のラベル> — 補足】` の形にする）")

# --- 46. GATE_MODE を持つ hook が、昇格手順の正本を参照しているか
#         （2026-07-26 の監査で検出。5本中 `critic-gate` だけが正本を引かずに
#          **手順を自分の言葉で書き写して**おり、しかも**文言がずれていた**
#          — 正本は「誤爆ゼロ確認後に deny へ昇格」、こちらは「誤爆パターンを収集後、deny へ昇格」。
#          **ゲートを deny に上げてよい条件が2通り書かれている**状態で、緩いほうを読めば
#          誤爆を残したまま昇格できてしまう。#42 と同じ「書き写すと腐る」形だが、
#          対象が **deny の昇格条件** なので実害が大きい ---
for _h in sorted((ROOT / "hooks/scripts").glob("*.sh")):
    _t = read(_h)
    if "GATE_MODE" not in _t and "_GATE_MODE" not in _t:
        continue
    if "GATE_MODE 昇格" not in _t:
        err(f"hooks/scripts/{_h.name}: GATE_MODE を持つのに昇格手順の正本を参照していない"
            f"（`TESTING.md「GATE_MODE 昇格」節が正本` と引く。手順を書き写すと、"
            f"**deny に上げてよい条件が2通り**になり、緩いほうが読まれる）")

# --- 47. hook が守る規律が、対象エージェントの定義本文にも書かれているか（多層防御の二重化）
#         （2026-07-27 第15ラン G31 FAIL で検出。Critic Gate の規律は `critic-gate.sh` に**しか**無く、
#          `agents/design-artisan.md` には critic / 審査 / 提示 のいずれの語も1件も無かった。
#          E5 のとおり **hook の発火は保証されない**ので、沈黙した環境では
#          「審査前に完成品を渡さない」を守るものが**1枚も無くなる**。
#          escalations の「設計上の帰結」は『hook が効かなくても壊れない』を掲げているのに、
#          このゲートだけ帰結が適用されていなかった。
#          **文章で「多層防御」と書いてあるだけでは層は増えない** — 層があることを機械で数える） ---
#         **語が1つ出てくるだけでは足りない**（意図的破壊で実測）: 「design-critic 未審査と書く」の
#         1行だけでも語は出現し、検査は黙る。規律の実体は「**ゲートが沈黙していても出さない**」という
#         条件のほうなので、審査先の名前と沈黙時の条件を**両方**要求する。
_DUAL_GUARDED = [
    # (hook, 二重化すべきエージェント, 本文に必要な語（全部要る）, 何の規律か)
    ("critic-gate.sh", "design-artisan.md", ("design-critic", "沈黙"),
     "design-critic の PASS 前に生成物を完成品として渡さない（ゲートが沈黙していても）"),
]
for _hook, _agent, _needles, _what in _DUAL_GUARDED:
    _ap = ROOT / "agents" / _agent
    if not _ap.is_file():
        err(f"lint #47 の表が実体とずれている: agents/{_agent} が無い")
        continue
    _at = read(_ap)
    _missing = [n for n in _needles if n not in _at]
    if _missing:
        err(f"agents/{_agent}: {_hook} が守る規律「{_what}」が本文に無い"
            f"（不足: {' / '.join(_missing)}）— hook の発火は保証されない（escalations E5）ので、"
            f"**沈黙した環境では守るものが1枚も無くなる**。エージェント側の自己規律として二重化すること")

# --- 48. 「G1〜G42」のような**範囲表記**が実体の最大番号を指しているか
#         （2026-07-27 第15ラン所見4。`docs/evals.md` の運用節が「G1〜G42」のままで、
#          実体は G67 だった。#39 は同じ検査を `takumi-verify.md` にしかかけておらず、
#          **同じ壊れ方が別ファイルで起きていた**（#40 の走査範囲が狭かったのと同じ形）。
#          範囲表記は**書き写した瞬間に二重管理**になり、番号を足しても誰も直しに来ない。
#          記録ファイル（過去ランの記述）は当時の範囲が正しいので対象外 ---
_g_max = max([int(n) for n in re.findall(r"^\|\s*G(\d+)", read(ROOT / "docs/evals.md"), re.M)] or [0])
for _f in sorted(ROOT.rglob("*.md")):
    _rel = _f.relative_to(ROOT).as_posix()
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    for _n in {int(m) for m in re.findall(r"G1〜G(\d+)", read(_f))}:
        if _n != _g_max:
            err(f"{_rel}: 範囲表記 `G1〜G{_n}` が実体と合っていない（docs/evals.md の最大は G{_g_max}）— "
                f"**少ない範囲を書くと「全部やった」が嘘になる**。範囲を書き写したら、"
                f"golden を足すたびに直しに来なければならない")

# --- 49. 簡体字が混入していないか
#         （2026-07-27 第15ラン所見5。`skills/design-evidence-jp` に「説得を长さに頼らない」。
#          日本語の文中に1文字だけ混ざるので**読んでも気づけない**（「長」と「长」）。
#          本プロダクトはコードを除き日本語が原則なので、字種の取り違えは規約違反そのもの。
#          対象は日本語で書かれる文書だけ（コード中の文字列は対象外）。
#          **簡体字専用の字だけを見る。** 最初の実装は `国` を入れて9ファイルを誤爆させた —
#          `国` は日本の新字体でもあり、**日中で同じ字は判別材料にならない**。
#          この表は網羅ではなく「よく混ざる字」の列挙で、見つけたら足していく ---
_SIMPLIFIED = "长门问时东车马鸟语说读书对话间关开发图馆网页应该动员产业务实现变换级别"
for _f in sorted(list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.yaml"))):
    _rel = _f.relative_to(ROOT).as_posix()
    # 記録ファイルは対象外 — 検出した混入を**そのままの形で引用する**のが記録の役目で、
    # 直すと何が起きたのか読めなくなる（#40/#41/#42/#48 と同じ扱い）
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    _hits = sorted({c for c in read(_f) if c in _SIMPLIFIED})
    if _hits:
        err(f"{_rel}: 簡体字が混入している（{' '.join(_hits)}）— "
            f"日本語の文中に1文字だけ混ざると**読んでも気づけない**。日本語の字体に直すこと")

# --- 50. 常時ロードの予算（session-rules.txt は毎セッション全文が文脈に載る）
#         （2026-07-27 のトークン効率レビューで導入。ルール(3) が1行 4,094字まで育っており、
#          **ファイル全体 9,365字の 44% が1行**だった。中身はスキル索引と各スキルの具体値で、
#          **調べた15項目すべてが正本側にも存在**＝二重管理。しかも本ファイルの1行目自身が
#          「詳細な値・手順はここに複製せず正本を Read」と書いていた — **規約が自分の中で破られていた**。
#          索引が不要なのは、42本の `SKILL.md` の `description`（`Use when` / `Not for`）を
#          プラットフォームが常時読める形で載せているため。**同じ情報に3回払っていた。**
#          上限は「いま通る値のすぐ上」に置く（ラチェット）。増やすときは
#          **「正本を開かなかったときに効かないと困るか」を説明してから**上限ごと上げる ---
_RULES_MAX_TOTAL = 7_400   # 全体（字）
_RULES_MAX_LINE = 760      # 1行（字）— 1行が肥大すると読み手も差分も追えなくなる
if _rules_txt.is_file():
    _rt = read(_rules_txt)
    if len(_rt) > _RULES_MAX_TOTAL:
        err(f"hooks/scripts/session-rules.txt が {len(_rt):,}字（上限 {_RULES_MAX_TOTAL:,}字）— "
            f"**毎セッション全文が文脈に載る**ので、長くなるほど本題に使える文脈が減る。"
            f"索引・具体値・手順は正本を指すだけにする。"
            f"**ここに置いてよいのは「正本を開かなかったときに効かないと困るもの」だけ**")
    for _i, _l in enumerate(_rt.splitlines(), 1):
        if len(_l) > _RULES_MAX_LINE:
            err(f"hooks/scripts/session-rules.txt 行{_i}: {len(_l):,}字（上限 {_RULES_MAX_LINE:,}字）— "
                f"1つのルールに詰め込みすぎ。**正本へ切り出すか、別番号のルールに分ける**"
                f"（過去にルール(3)が 4,094字まで育ち、中身は全項目が正本と二重管理だった）")

# --- 51. 委譲1回あたりの preload 予算（`skills:` は**スキル全文**が起動時に注入される）
#         （2026-07-27 のトークン効率レビューで導入。実測: cmo-strategist が6本 40,251字、
#          privacy-auditor が3本 28,400字。同時上限4体を重い順に使うと 12万字を超える。
#          preload は E6（委譲先が正本を Read できない環境がある）への対策で**買っているものがある**ため
#          削らないが、**黙って増えるのは止める**。増やすなら「Read では届かない判定根拠か」を
#          説明したうえで上限ごと上げる。#34 は「必読なら preload 必須」の側だけを見ており、
#          **増える方向にしか効かない検査だった** ---
_PRELOAD_MAX = 44_000
for _a in sorted((ROOT / "agents").glob("*.md")):
    _n = sum(len(read(ROOT / f"skills/{_s}/SKILL.md"))
             for _s in preloaded_skills(_a) if (ROOT / f"skills/{_s}/SKILL.md").is_file())
    if _n > _PRELOAD_MAX:
        err(f"agents/{_a.name}: `skills:` preload の合計が {_n:,}字（上限 {_PRELOAD_MAX:,}字）— "
            f"**スキル全文が起動時に注入される**ので、委譲1回ぶんの文脈をそのまま食う。"
            f"判定の根拠でないスキルは外すか、詳細を `resources/` へ寄せて SKILL.md を薄くする"
            f"（`skills/web-design` が先例）。`python3 scripts/context-budget.py` で内訳を見る")

# --- 52. version を上げずに配布物を変えていないか
#         （2026-07-27 に実測で発覚。v5.7.0 へ繰り上げた**後**に
#          `hooks/scripts/session-rules.txt` と `_common.sh` を変えており、
#          **同じ 5.7.0 で中身が2種類ある**状態になっていた。
#          **Cowork は version フィールドの変化でしか更新を検知しない**ので、
#          先に同期した利用者には修正が**永久に届かない**。
#          リリースチェックリスト項目2 は文章で規定していたが、機械検査が無かった。
#          対象は「利用者の環境に配られて実行時に読まれるもの」だけ —
#          `scripts/` `tests/` は開発側、ルート直下の .md（TESTING.md 等）は記録。
#          **マーカー更新のコミットは version を上げてはいけない**規定があるので、
#          記録ファイルを対象に入れると規定同士が噛み合わなくなる ---
_SHIPPED = ("commands", "procedures", "agents", "skills", "hooks", "templates", "takumi", "docs")
try:
    import subprocess as _sp

    def _git(*a):
        return _sp.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=10)

    if _git("rev-parse", "--git-dir").returncode == 0:
        if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
            # **扱えないものを扱えるふりで検査しない** — 浅いクローンでは履歴を辿れないので、
            # 黙って通すのではなく「検査できなかった」ことを言う
            warns.append("lint #52（version 繰り上げ漏れ）を実行できない: 浅いクローン。"
                         "CI なら actions/checkout に `fetch-depth: 0` を付ける")
        else:
            _vcommit = _git("log", "-1", "--format=%H", "--",
                            ".claude-plugin/plugin.json").stdout.strip()
            if _vcommit:
                _changed = [f for f in _git("diff", "--name-only", f"{_vcommit}..HEAD",
                                            "--", *_SHIPPED).stdout.splitlines() if f.strip()]
                if _changed:
                    warns.append(
                        f"version={plugin['version']} を繰り上げた後に配布物が {len(_changed)} 件変わっている"
                        f"（{', '.join(_changed[:4])}{' …' if len(_changed) > 4 else ''}）— "
                        f"**Cowork は version の変化でしか更新を検知しない**ので、"
                        f"先に同期した利用者には届かない。配布する前に version を繰り上げること"
                        f"（リリースチェックリスト項目2）")
except Exception:
    pass  # git が無い環境では検査しない（開発は git 前提だが、動かなくなるほうが害）

# --- 53. V78（preload 実測）の probe が、本当に preload の有無を弁別できるか
#         （2026-07-26 第16ラン V78 FAIL の切り分けで導入。旧 probe は2つとも
#          **答えがエージェント本文に書いてあった**:
#            `outcome-verifier` に「KPIツリーに無い指標を返してよいか」と聞いていたが、
#            その答えは `agents/outcome-verifier.md` に「有料指標は KPIツリーに存在しない前提」とある。
#            `design-critic` に「コントラスト比の具体値」を聞いていたが、`4.5` は同エージェント本文にあり、
#            かつ WCAG の一般知識でもある。
#          **preload が死んでいても満点で答えられる問いで、preload の生死を測っていた。**
#          probe は「preload 先にあり、かつエージェント本文に無い語」でなければ意味を持たない —
#          文章で決めても腐るので、語そのものを表に持って機械で確かめる ---
_V78_PROBES = [
    # (エージェント, preload 先スキル, probe の弁別語)
    ("outcome-verifier", "kpi-design-jp", "虚栄の指標を見分ける4つの問い"),
    ("design-critic", "psych-ux-jp", "楽天型"),
]
for _ag, _sk, _needle in _V78_PROBES:
    _ap, _sp = ROOT / "agents" / f"{_ag}.md", ROOT / "skills" / _sk / "SKILL.md"
    if not (_ap.is_file() and _sp.is_file()):
        err(f"lint #53 の表が実体とずれている: {_ag} / {_sk}")
        continue
    if _needle not in read(_sp):
        err(f"V78 の probe「{_needle}」が skills/{_sk}/SKILL.md に無い — "
            f"**preload 先に無い語を聞いても、答えられないのが正常**になってしまう")
    if _needle in read(_ap):
        err(f"V78 の probe「{_needle}」が agents/{_ag}.md にも書いてある — "
            f"**preload が届いていなくても答えられる**ので、preload の生死を測れない")
    if _sk not in preloaded_skills(_ap):
        err(f"V78 の probe は skills/{_sk} を測る前提だが、agents/{_ag}.md の "
            f"`skills:` preload に載っていない")
    if _needle not in read(ROOT / "procedures/takumi-verify.md"):
        err(f"V78 の probe「{_needle}」が procedures/takumi-verify.md に書かれていない — "
            f"**検証者が実際に使う語と、ここで弁別性を保証している語がずれる**")

# --- 54. `fable` の代替に `sonnet`（速い側）を指定していないか
#         （2026-07-26 利用者の指摘で発覚。`docs/agent-tiers.md` は design-artisan について
#          「**fable の段を下げると成果物の質が直接落ちる**」と書いた**4行後に**
#          `model: sonnet` を明示して再委譲、と書いていた。**正本が自分の中で矛盾していた。**
#          `agents/risk-forecaster.md` には最初から「**判断を担う役なので sonnet への降格はしない**」と
#          あり、**同じ規則が design-artisan にだけ適用されていなかった**。
#          しかも同じ指示が8箇所に書き写されており、全部が sonnet のままだった。
#          規則: **fable が使えないときは、その級の「深く考える側」（= opus）へ横移動する。速い側へ降ろさない。**
#          モデル名の列挙行（`sonnet / opus / haiku / fable` のような一覧）は対象外 —
#          **代替を指示している文脈だけを見る** ---
_FALLBACK_CTX = ("再委譲", "フォールバック", "不可なら", "起動できな", "使えない場合", "降格")
for _f in sorted(ROOT.rglob("*.md")):
    _rel = _f.relative_to(ROOT).as_posix()
    if ".git" in _f.parts or _rel in _RECORD_FILES:
        continue
    for _ln, _line in enumerate(read(_f).splitlines(), 1):
        if "fable" not in _line or "sonnet" not in _line:
            continue
        if not any(_c in _line for _c in _FALLBACK_CTX):
            continue  # モデル名の一覧・級の表など、代替を指示していない行
        # **`sonnet` の直後に来る否定だけ**を取り除いてから、裸の `sonnet` が残るかを見る。
        # 行のどこかに否定語があれば免除、という作り方では
        # 「`model: sonnet` を明示して再委譲する（…速い側へ降ろさない）」が素通りした（実測）。
        # 否定は**その sonnet を否定しているとき**だけ効く
        _bare = re.sub(r"sonnet[^。]{0,12}?(への?)?(降格(は)?しない|降ろさない|使わない|置かない)",
                       "", _line)
        if "sonnet" not in _bare:
            continue
        err(f"{_rel}:{_ln}: `fable` の代替に `sonnet` を指定している — "
            f"**fable を選んだ理由（審美・生成の当たり）が代替で失われる**。"
            f"その級の「深く考える側」（`opus`）へ横移動すること"
            f"（正本 docs/agent-tiers.md。速い側へ降ろさない）")

# --- 結果 ---
print(f"lint: commands={len(commands)} procedures={len(procedures)} "
      f"agents={len(list((ROOT/'agents').glob('*.md')))} skills={len(list((ROOT/'skills').glob('*/SKILL.md')))} "
      f"version={plugin['version']}")
for w in warns:
    print(f"WARN: {w}")
if errors:
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1)
print("lint: OK")
