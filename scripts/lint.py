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
    # verify-task.yaml は「聞いてきたら FAIL」を書くために廃止語を名指しする（V44）
    if not f.is_file() or f.name == "verify-task.yaml":
        continue
    try:
        body = read(f)
    except UnicodeDecodeError:
        continue
    for word in ("求人媒体", "広告分析"):
        if word in body:
            err(f"templates/{f.name}: 廃止カテゴリー『{word}』が残存"
                f"（現行カテゴリーは docs/command-registry.md が正本）")

# --- 13. references の本数を書いた記述が実体と一致するか（2026-07-24 実機検証 F5） ---
_ref_count = len(list((ROOT / "references").glob("*/SKILL.md")))
_ref_pat = re.compile(r"references/（(\d+)本）")
for f in list(ROOT.glob("procedures/*.md")) + list(ROOT.glob("docs/**/*.md")) + [ROOT / "README.md"]:
    if not f.is_file():
        continue
    for m in _ref_pat.finditer(read(f)):
        if int(m.group(1)) != _ref_count:
            err(f"{f.relative_to(ROOT)}: references の本数が実体と不一致"
                f"（記述={m.group(1)} / 実体={_ref_count}）")

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

# --- 17. evals.md の golden タスクが全スキル・全エージェントを覆っているか
#         （2026-07-25 全体CHECK で検出: references 20本中16本・agents 9体中6体が未収載のまま
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
    _skill_names = {s.parent.name for s in (ROOT / "references").glob("*/SKILL.md")}
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
