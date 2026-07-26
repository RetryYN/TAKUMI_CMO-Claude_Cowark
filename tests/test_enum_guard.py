"""ドメイン層の Enum フィールドが「文字列で渡されても黙って通らない」ことの回帰テスト。

**背景（2026-07-26 Tier 2 perfect ラン F-1）**: `PremiumOffer(kind='total', ...)` が
景品規制の上限超過を素通りさせた。`@dataclass` の型注釈は実行時に検証されないため、
`if self.kind is PremiumKind.TOTSUKE` の分岐がすべて偽になり、上限チェックを
一度も通らずに `assert_lawful()` が None を返していた。**フェイルオープン**であり、
「機械で止まる」という設計の前提そのものが崩れる欠陥。

同型の穴がドメイン層の Enum フィールド6箇所すべてにあったため、`require_enum` に
共通化して横展開した。このテストは **新しく Enum フィールドを持つクラスを足したときに
守り忘れたら落ちる** ように作ってある（下の `test_全クラスが表に載っている`）。
"""
import dataclasses
import enum
import importlib
import pkgutil
import unittest

import takumi.domain as domain_pkg
from takumi.domain.brand import Brand, BrandPartition, BrandSlug, BrandStatus
from takumi.domain.channel import Channel, ChannelKind
from takumi.domain.kpi_tree import KpiKind, KpiNode, KpiTree
from takumi.domain.local_profile import ReviewSolicitation, SolicitationTarget
from takumi.domain.premium import PremiumKind, PremiumOffer
from takumi.domain.task_loop import LoopPhase, Step

# (クラス, Enum フィールド名, 正しく作れる kwargs)
# **新しく Enum フィールドを持つ dataclass を足したらここにも足す。**
# 足し忘れは `test_全クラスが表に載っている` が検出する。
GUARDED = [
    (Brand, "status", dict(slug=BrandSlug("alpha"), name="アルファ", status=BrandStatus.ACTIVE)),
    (Channel, "kind", dict(name="ブログ", kind=ChannelKind.OWNED_MEDIA)),
    (KpiNode, "kind", dict(name="訪問数", kind=KpiKind.LEADING, children=[])),
    (ReviewSolicitation, "target", dict(target=SolicitationTarget.CUSTOMER, incentive=False)),
    (
        PremiumOffer,
        "kind",
        dict(kind=PremiumKind.TOTSUKE, transaction_value_yen=5000, premium_value_yen=100),
    ),
    (Step, "phase", dict(phase=LoopPhase.FRAME, agent="cmo-strategist")),
]

# enum でない値の例。**「それらしい文字列」を読み替える親切設計にしない**ことの確認も兼ねる
BAD_VALUES = ("totsuke", "総付景品", "active", "", None, 0, 1, ["a"])


class TestEnumGuard(unittest.TestCase):
    def test_正しい_enum_なら作れる(self):
        for cls, _field, kwargs in GUARDED:
            with self.subTest(cls=cls.__name__):
                cls(**kwargs)  # 例外が出ないこと（ガードが正当な値を誤爆しない）

    def test_enum_でない値は_ValueError(self):
        for cls, field, kwargs in GUARDED:
            for bad in BAD_VALUES:
                with self.subTest(cls=cls.__name__, bad=bad):
                    with self.assertRaises(ValueError):
                        cls(**{**kwargs, field: bad})

    def test_全クラスが表に載っている(self):
        """ドメイン層の Enum 型フィールドを持つ dataclass が GUARDED から漏れていないか。

        漏れ＝そのクラスは文字列を渡されても黙って通る可能性がある、ということ。
        """
        found = set()
        for mod_info in pkgutil.iter_modules(domain_pkg.__path__):
            module = importlib.import_module(f"takumi.domain.{mod_info.name}")
            for obj in vars(module).values():
                if not (dataclasses.is_dataclass(obj) and obj.__module__ == module.__name__):
                    continue
                for f in dataclasses.fields(obj):
                    type_name = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", "")
                    candidate = getattr(module, type_name, None)
                    if isinstance(candidate, type) and issubclass(candidate, enum.Enum):
                        found.add((obj.__name__, f.name))
        listed = {(cls.__name__, field) for cls, field, _ in GUARDED}
        self.assertEqual(
            found - listed,
            set(),
            "Enum フィールドを持つ dataclass が GUARDED 表に無い — "
            "require_enum を __post_init__ に足し、この表にも足すこと",
        )


class TestPremiumF1回帰(unittest.TestCase):
    """F-1 そのものの再現ケース。**この形でだけは二度と通してはならない。**"""

    def test_文字列_kind_で上限超過が素通りしない(self):
        # 総付景品・取引価額5,000円 → 上限1,000円。1,500円は超過。
        # enum を渡せば止まるが、文字列だと以前は assert_lawful() が None を返していた。
        with self.assertRaises(ValueError):
            PremiumOffer(
                kind="total", transaction_value_yen=5000, premium_value_yen=1500
            ).assert_lawful()

    def test_enum_なら従来どおり上限で止まる(self):
        with self.assertRaises(ValueError) as cm:
            PremiumOffer(
                kind=PremiumKind.TOTSUKE, transaction_value_yen=5000, premium_value_yen=1500
            ).assert_lawful()
        self.assertIn("総付景品の最高額を超えている", str(cm.exception))

    def test_max_premium_yen_に_その他の受け皿が無い(self):
        """新種別を足して上限を書き忘れたとき、30万円（最も緩い上限）を既定にしない。"""
        offer = PremiumOffer(
            kind=PremiumKind.TOTSUKE, transaction_value_yen=5000, premium_value_yen=100
        )
        # frozen dataclass なので object.__setattr__ で無理やり未知の種別に差し替える
        fake = enum.Enum("FakeKind", "UNKNOWN").UNKNOWN
        object.__setattr__(offer, "kind", fake)
        with self.assertRaises(ValueError) as cm:
            offer.max_premium_yen()
        self.assertIn("上限が定義されていない", str(cm.exception))

    def test_全種別に上限が定義されている(self):
        for kind in PremiumKind:
            with self.subTest(kind=kind):
                offer = PremiumOffer(
                    kind=kind, transaction_value_yen=5000, premium_value_yen=0
                )
                self.assertGreater(offer.max_premium_yen(), 0)


class Test宣言の検査を横展開(unittest.TestCase):
    """Enum 以外にも「宣言してもらう設計」がある。**宣言が本物かを検査して初めて機械保証になる。**

    2026-07-26 の監査で検出: `BrandPartition` と `KpiTree` は型注釈だけで検証が無く、
    生の値を渡すと配下の検証（slug 規約・有料指標）を丸ごと飛ばせた。
    どちらも後段で AttributeError になって落ちる＝フェイルクローズだったが、
    **なぜ落ちたのかが読めない**ので、ドメイン層の ValueError にそろえた。
    """

    def test_BrandPartition_は生の文字列を受け付けない(self):
        for bad in ("acme", "../../etc", "", None, 1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    BrandPartition(bad)

    def test_BrandPartition_は_BrandSlug_なら作れる(self):
        p = BrandPartition(BrandSlug("acme"))
        self.assertEqual(p.base, "knowledge/brands/acme")

    def test_KpiTree_は生の値を根にできない(self):
        for bad in ("訪問数", None, 1, {"name": "訪問数"}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    KpiTree(root=bad)

    def test_KpiTree_は_KpiNode_なら作れる(self):
        t = KpiTree(root=KpiNode(name="訪問数", kind=KpiKind.LEADING, children=[]))
        self.assertEqual(t.all_names(), ["訪問数"])


if __name__ == "__main__":
    unittest.main()
