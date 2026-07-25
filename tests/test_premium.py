"""景品規制（景品表示法）の限度額を計算する値オブジェクトの単体テスト（TDD: 実装より先に書く）。

**なぜドメインに置くか**: 紹介キャンペーン・口コミ特典は「攻め」の主要手段だが、
日本では景品表示法の景品規制が上限を定めている。上限は**計算できる**ので、
「気をつけましょう」という文章ではなく機械検査にする（本プロダクトの一貫方針）。

限度額の出典（すべて消費者庁の一次情報。skills/referral-advocacy-jp に記載）:
- 総付景品: 取引価額 1,000円未満 → 200円 / 1,000円以上 → 取引価額の10分の2
- 一般懸賞: 取引価額 5,000円未満 → 取引価額の20倍 / 5,000円以上 → 10万円。総額は売上予定総額の2%
- 共同懸賞: 取引価額にかかわらず30万円。総額は売上予定総額の3%
"""
import unittest

from takumi.domain.premium import PremiumKind, PremiumOffer


class TestTotsukeLimit(unittest.TestCase):
    """総付景品 — もれなく提供するもの（紹介特典の大半はここに当たる）。"""

    def test_under_1000_yen_limit_is_200(self):
        offer = PremiumOffer(PremiumKind.TOTSUKE, transaction_value_yen=800, premium_value_yen=200)
        self.assertEqual(offer.max_premium_yen(), 200)
        self.assertEqual(offer.violations(), [])

    def test_under_1000_yen_over_limit_detected(self):
        offer = PremiumOffer(PremiumKind.TOTSUKE, transaction_value_yen=800, premium_value_yen=201)
        self.assertEqual(offer.max_premium_yen(), 200)
        self.assertTrue(any("最高額" in v for v in offer.violations()))

    def test_1000_yen_or_more_is_two_tenths(self):
        offer = PremiumOffer(PremiumKind.TOTSUKE, transaction_value_yen=5000, premium_value_yen=1000)
        self.assertEqual(offer.max_premium_yen(), 1000)
        self.assertEqual(offer.violations(), [])

    def test_boundary_exactly_1000(self):
        """1,000円ちょうどは「1,000円以上」側（200円ではなく200円=1000*0.2 で偶然一致するため、
        境界の取り違えが表面化しない。3,000円で確かめる）。"""
        self.assertEqual(
            PremiumOffer(PremiumKind.TOTSUKE, 1000, 200).max_premium_yen(), 200
        )
        self.assertEqual(
            PremiumOffer(PremiumKind.TOTSUKE, 3000, 600).max_premium_yen(), 600
        )

    def test_fraction_is_truncated_not_rounded_up(self):
        """端数は切り上げない（上限を1円でも超えれば違反になるため、安全側に倒す）。"""
        self.assertEqual(PremiumOffer(PremiumKind.TOTSUKE, 1001, 200).max_premium_yen(), 200)


class TestGeneralLotteryLimit(unittest.TestCase):
    """一般懸賞 — 抽選・先着・優劣で決まるもの。"""

    def test_under_5000_is_twenty_times(self):
        offer = PremiumOffer(
            PremiumKind.GENERAL_LOTTERY,
            transaction_value_yen=1000,
            premium_value_yen=20000,
            expected_sales_yen=10_000_000,
            total_premium_yen=100_000,
        )
        self.assertEqual(offer.max_premium_yen(), 20000)
        self.assertEqual(offer.violations(), [])

    def test_5000_or_more_is_capped_at_100000(self):
        offer = PremiumOffer(
            PremiumKind.GENERAL_LOTTERY, transaction_value_yen=50000, premium_value_yen=100001
        )
        self.assertEqual(offer.max_premium_yen(), 100000)
        self.assertTrue(any("最高額" in v for v in offer.violations()))

    def test_total_exceeds_two_percent_of_expected_sales(self):
        offer = PremiumOffer(
            PremiumKind.GENERAL_LOTTERY,
            transaction_value_yen=5000,
            premium_value_yen=10000,
            expected_sales_yen=1_000_000,
            total_premium_yen=30_000,  # 2% = 20,000 を超える
        )
        self.assertEqual(offer.max_total_premium_yen(), 20_000)
        self.assertTrue(any("総額" in v for v in offer.violations()))

    def test_total_within_two_percent_passes(self):
        offer = PremiumOffer(
            PremiumKind.GENERAL_LOTTERY,
            transaction_value_yen=5000,
            premium_value_yen=10000,
            expected_sales_yen=1_000_000,
            total_premium_yen=20_000,
        )
        self.assertEqual(offer.violations(), [])


class TestJointLotteryLimit(unittest.TestCase):
    """共同懸賞 — 商店街・複数事業者の共同企画。"""

    def test_max_is_300000_regardless_of_transaction_value(self):
        for value in (100, 5000, 1_000_000):
            self.assertEqual(
                PremiumOffer(PremiumKind.JOINT_LOTTERY, value, 300_000).max_premium_yen(),
                300_000,
            )

    def test_total_is_three_percent(self):
        offer = PremiumOffer(
            PremiumKind.JOINT_LOTTERY,
            transaction_value_yen=5000,
            premium_value_yen=100_000,
            expected_sales_yen=1_000_000,
            total_premium_yen=30_000,
        )
        self.assertEqual(offer.max_total_premium_yen(), 30_000)
        self.assertEqual(offer.violations(), [])


class TestUnknownTotalIsNotSilentlyPassed(unittest.TestCase):
    """総額を申告していない懸賞を「違反なし」と読ませない。

    未申告を沈黙で通すと、**測っていないものを「問題なし」と報告する**ことになる。
    これは本プロダクトが最も避けたい失敗（判定不能を「効果あり」と書かない、と同じ性質）。
    """

    def test_lottery_without_expected_sales_reports_unverifiable(self):
        offer = PremiumOffer(PremiumKind.GENERAL_LOTTERY, 5000, 10_000)
        self.assertIsNone(offer.max_total_premium_yen())
        self.assertTrue(any("判定不能" in v for v in offer.violations()))

    def test_totsuke_does_not_require_total(self):
        """総付景品には総額規制が無いので、未申告でも判定不能にならない。"""
        offer = PremiumOffer(PremiumKind.TOTSUKE, 5000, 1000)
        self.assertIsNone(offer.max_total_premium_yen())
        self.assertEqual(offer.violations(), [])


class TestAssertLawful(unittest.TestCase):
    def test_raises_with_all_reasons(self):
        offer = PremiumOffer(
            PremiumKind.GENERAL_LOTTERY,
            transaction_value_yen=5000,
            premium_value_yen=200_000,
            expected_sales_yen=1_000_000,
            total_premium_yen=100_000,
        )
        with self.assertRaises(ValueError) as ctx:
            offer.assert_lawful()
        message = str(ctx.exception)
        self.assertIn("最高額", message)
        self.assertIn("総額", message)

    def test_lawful_offer_does_not_raise(self):
        PremiumOffer(PremiumKind.TOTSUKE, 3000, 600).assert_lawful()


class TestInputGuards(unittest.TestCase):
    def test_non_positive_transaction_value_rejected(self):
        with self.assertRaises(ValueError):
            PremiumOffer(PremiumKind.TOTSUKE, 0, 100)

    def test_negative_premium_rejected(self):
        with self.assertRaises(ValueError):
            PremiumOffer(PremiumKind.TOTSUKE, 1000, -1)


class TestDiscountIsNotPremium(unittest.TestCase):
    """値引きは景品類に当たらない（消費者庁）。

    紹介特典を「ギフト券」にするか「次回割引」にするかで規制の当たり方が変わる。
    ここは AI が推測で分類すると事故るため、**種別は呼び出し側が明示する**設計にしてある。
    その事実をテストで固定し、自動分類のヘルパーを後から生やさないようにする。
    """

    def test_no_auto_classification_helper_exists(self):
        import takumi.domain.premium as premium

        self.assertFalse(
            hasattr(premium, "classify_incentive"),
            "インセンティブの自動分類は禁止（過剰検知・過小検知のいずれも法的判断を誤らせる）。"
            "種別は人間が declare する",
        )

    def test_exemption_examples_are_documented(self):
        from takumi.domain.premium import NOT_PREMIUM_EXAMPLES

        joined = "／".join(NOT_PREMIUM_EXAMPLES)
        self.assertIn("値引", joined)
        self.assertIn("割引券", joined)


if __name__ == "__main__":
    unittest.main()
