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
_testing = ROOT / "TESTING.md"
if _testing.is_file():
    _marker_re = r"<!--\s*tier2-verified:\s*([0-9.]+)\s+env=(\w+)\s+fail=(\d+)\s*-->"
    _all = re.findall(_marker_re, read(_testing))
    # 正本は1つだけ。複数あると re.search が**最初の1つ**しか読まず、
    # 古いランのマーカーが新しいランを黙って上書きする（過去ラン節にマーカーを残すと起きる）
    if len(_all) > 1:
        err(f"TESTING.md: tier2-verified マーカーが {len(_all)} 個ある（{_all}）— "
            f"**最新ランの節に1つだけ**置く。lint は最初の1つしか読まないので、"
            f"古いマーカーが残っていると実測より緩い判定になる")
    _m = re.search(_marker_re, read(_testing))
    if not _m:
        err("TESTING.md: <!-- tier2-verified: <version> env=<cloud|local> fail=<件数> --> "
            "マーカーが無い（最後に実機検証したバージョン・**実行環境**・**FAIL件数**を機械可読で持つ。"
            "環境が無いと『ローカルで通った』を配布可と読み違え、"
            "FAIL件数が無いと『版が揃っている』だけで緑に見える）")
    else:
        _ran, _env, _fail = _m.group(1), _m.group(2), int(_m.group(3))
        if _env not in ("cloud", "local"):
            err(f"TESTING.md: tier2-verified の env={_env} は不正（cloud か local）")
        if _fail > 0:
            warns.append(
                f"Tier 2 の最終ラン（v{_ran}）に FAIL が {_fail} 件ある — **配布判断は FAIL 0 が条件**。"
                f" 直したら再ランして fail=0 に更新すること（直した“つもり”では下げない）"
            )
        if _ran != plugin["version"]:
            warns.append(
                f"Tier 2 実機検証が未実施: 最終ラン={_ran}（env={_env}） / 現行={plugin['version']}"
                f" — cloud Cowork で `/匠検証 full` と言い、結果を TESTING.md に記録して"
                f" マーカーを更新すること（リリースチェックリスト項目5・人間が実行）"
            )
        elif _env != "cloud":
            warns.append(
                f"Tier 2 の最終ランが env={_env}（v{_ran}）— **配布判断には cloud ランが要る**。"
                f" ローカルは hook 配線が環境依存（escalations E4）で、永続フォルダ未接続なら"
                f" knowledge/ 系（ブランド区画・ダッシュボード）を測れない"
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
    # lint のチェック番号: 「lint」を含む行の #n だけを見る（PR 番号と混同しない）
    for _line in _txt.splitlines():
        if "lint" not in _line.lower():
            continue
        for _m in re.finditer(r"(?<!PR )(?<!pull/)(?<!issues/)#(\d+[a-z]?)\b", _line):
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
_slash = re.compile(r"(?:(?<=^)|(?<=[\s（(「『]))/([ぁ-んァ-ヴー一-龠]{2,10})", re.M)
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
    _t = re.sub(r"旧 /[ぁ-んァ-ヴー一-龠]{2,10}", "", _t)  # 「旧 /素材探し」は履歴の明示
    for _mm in _slash.finditer(_t):
        if _mm.group(1) not in _cmd_names:
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
