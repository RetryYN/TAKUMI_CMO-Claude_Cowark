"""ワークスペース検証 — 利用者の `knowledge/brands/**` をドメインモデルで検証する。

`scripts/lint.py` から呼ばれる（docs/domain-model.md・docs/開発ワークフロー.md §3）。
ドメイン層の不変条件（slug の妥当性・一意性・ゼロ広告費・KPIツリーとの紐づけ）を、
実際に運用されているファイルに対して適用する層。

読み込みは呼び出し側から注入する（`load(path) -> obj`）。ドメイン側に YAML パーサへの
依存を持ち込まないため。lint は PyYAML の `safe_load`、テストは `json.loads` を渡す。

**寛容さの方針**: 実運用の YAML は自由記述を含む。認識できるキーだけを検証し、
知らないキーでは落とさない。逆に、認識したうえで不変条件に反するものは必ず落とす。
"""
from __future__ import annotations

from pathlib import Path

from .domain.brand import BrandRegistry, BrandSlug
from .domain.channel import Channel, ChannelKind
from .domain.kpi_tree import KpiTree

_BRANDS_DIR = "knowledge/brands"
_REGISTRY = "knowledge/brands.yaml"
_ACTIVE_FILE = "knowledge/.active-brand"


def _read(path: Path, load, errors: list[str], label: str):
    """1ファイルを読む。壊れていても例外を投げず、エラー文字列にして返り値 None。"""
    try:
        return load(path)
    except Exception as e:  # パーサの例外型は注入側に依存するため広く捕える
        errors.append(f"{label}: 読み込めません（{type(e).__name__}: {e}）")
        return None


def _validate_registry(root: Path, load, errors: list[str]) -> BrandRegistry | None:
    reg_path = root / _REGISTRY
    if not reg_path.is_file():
        return None
    data = _read(reg_path, load, errors, _REGISTRY)
    if not isinstance(data, dict):
        if data is not None:
            errors.append(f"{_REGISTRY}: マッピングではありません")
        return None
    try:
        registry = BrandRegistry.from_dict(data)
    except Exception as e:
        errors.append(f"{_REGISTRY}: ブランド台帳として不正です（{e}）")
        return None

    # 台帳 ↔ 区画ディレクトリの双方向一致
    brands_dir = root / _BRANDS_DIR
    on_disk = (
        {p.name for p in brands_dir.iterdir() if p.is_dir()} if brands_dir.is_dir() else set()
    )
    registered = set(registry.slugs())
    for slug in sorted(on_disk - registered):
        errors.append(
            f"{_BRANDS_DIR}/{slug}: 区画があるのに {_REGISTRY} に登録がありません"
        )
    for slug in sorted(registered - on_disk):
        errors.append(
            f"{_REGISTRY}: {slug} が登録されているのに区画 {_BRANDS_DIR}/{slug}/ がありません"
        )

    # アクティブの永続コピーが台帳と食い違っていないか
    active_file = root / _ACTIVE_FILE
    if active_file.is_file():
        written = active_file.read_text(encoding="utf-8").strip()
        current = registry.active.slug.value if registry.active else None
        if written and written != current:
            errors.append(
                f"{_ACTIVE_FILE}: {written!r} を指していますが台帳の active は {current!r} です"
                f"（セッションを跨ぐ引き継ぎでブランドを取り違えます）"
            )
    return registry


def _validate_tree(path: Path, load, errors: list[str], label: str) -> KpiTree | None:
    data = _read(path, load, errors, label)
    if data is None:
        return None
    if not isinstance(data, dict):
        errors.append(f"{label}: マッピングではありません")
        return None
    # `root:` で包む形と、ノードを直接書く形の両方を受ける
    node = data.get("root", data)
    try:
        return KpiTree.from_dict({"root": node})
    except Exception as e:
        errors.append(f"{label}: KPIツリーとして不正です（{e}）")
        return None


def _validate_campaign(path: Path, load, errors: list[str], label: str, tree: KpiTree | None,
                       slug: str) -> None:
    data = _read(path, load, errors, label)
    if not isinstance(data, dict):
        if data is not None:
            errors.append(f"{label}: マッピングではありません")
        return

    goal = data.get("goal_kpi")
    if isinstance(goal, str) and goal.strip():
        if tree is None:
            errors.append(
                f"{label}: 目標KPI {goal!r} を検証できません — "
                f"{_BRANDS_DIR}/{slug}/strategy/kpi-tree.yaml がありません"
                f"（キャンペーンは必ず KPIツリーのノードを目標にする）"
            )
        elif goal not in tree.all_names():
            errors.append(
                f"{label}: 目標KPI {goal!r} が KPIツリーにありません"
                f"（背骨から浮いたキャンペーンは計測を上流に返せません）"
            )

    for raw in data.get("channels") or []:
        if isinstance(raw, dict):
            name, kind = raw.get("name"), raw.get("kind")
        else:
            name, kind = raw, None
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            Channel(name, ChannelKind(kind) if kind else ChannelKind.SNS)
        except ValueError as e:
            errors.append(f"{label}: 参加媒体が不正です（{e}）")


def validate_workspace(root: Path, load) -> list[str]:
    """ワークスペース `root` を検証し、違反の一覧を返す（空ならOK）。

    `knowledge/` が無ければ何も言わない（プラグインリポジトリ単体で lint を回す通常ケース）。
    """
    root = Path(root)
    errors: list[str] = []
    if not (root / "knowledge").is_dir():
        return errors

    _validate_registry(root, load, errors)

    brands_dir = root / _BRANDS_DIR
    if not brands_dir.is_dir():
        return errors

    for partition in sorted(p for p in brands_dir.iterdir() if p.is_dir()):
        slug = partition.name
        try:
            BrandSlug(slug)
        except ValueError as e:
            errors.append(f"{_BRANDS_DIR}/{slug}: 区画名が slug として不正です（{e}）")
            continue

        tree = None
        tree_path = partition / "strategy/kpi-tree.yaml"
        if tree_path.is_file():
            tree = _validate_tree(
                tree_path, load, errors, f"{_BRANDS_DIR}/{slug}/strategy/kpi-tree.yaml"
            )

        camp_dir = partition / "strategy/campaigns"
        if camp_dir.is_dir():
            for camp in sorted(camp_dir.glob("*.yaml")):
                _validate_campaign(
                    camp, load, errors,
                    f"{_BRANDS_DIR}/{slug}/strategy/campaigns/{camp.name}",
                    tree, slug,
                )
    return errors
