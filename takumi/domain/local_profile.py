"""ローカル検索プロフィール（Google ビジネス プロフィール等）の不変条件。

**なぜコードにするか**: ローカル検索は、ゼロ広告費の事業にとって数少ない
「掲載順位を金で買えない面」であり、だからこそ**面ごと失う事故**が最も痛い。
Google はガイドライン違反に対して「プロフィールへのアクセスを停止する権利を留保する」と
明記している（→ `skills/local-seo-jp` の出典）。停止された面は、記事のように書き直せない。

ここで機械検査にするのは、**文章の注意書きでは確実に破られる2点**:

1. **プロフィール名に、看板に無い語を足さない。**
   「渋谷 自家焙煎」を足すと一時的に効いてしまうので、誘惑が最も強い違反。
2. **対価と引き換えの口コミを依頼しない。**
   日本のステマ規制は「事業者の関与を表示すれば可」だが、
   **Google のポリシーは対価と引き換えの口コミ自体を認めない。表示では解決しない。**
   法規で許されることと、プラットフォームで許されることは別。

**この値オブジェクトは法的助言でもガイドラインの完全な写しでもない。**
ここが見るのは「明らかに止めるべき形」であり、通ったことは適法・適合の保証にならない。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .enum_guard import require_enum

_SPACES = re.compile(r"[\s　]+")


def _normalize(s: str) -> str:
    """空白（半角・全角）の差を無視するための正規化。それ以上は正規化しない。

    表記ゆれ（カタカナ・漢字・記号）まで吸収しようとすると、
    「別名を付けた」のか「同じ名前を書いた」のかの区別がつかなくなる。
    """
    return _SPACES.sub("", s)


@dataclass(frozen=True)
class ProfileName:
    """ローカル検索プロフィールに載せる名称（値オブジェクト）。

    Attributes:
        storefront_name: 看板・名刺・店頭で**実際に使っている**名称
        listed_name: プロフィールに載せようとしている名称
    """

    storefront_name: str
    listed_name: str

    def __post_init__(self) -> None:
        if not _normalize(self.storefront_name):
            raise ValueError(
                "看板名（storefront_name）が空。**看板に無い語を足していないか**は、"
                "看板名を宣言しないと判定できない。"
                "推測で「問題なし」を返さないため、ここで止める"
            )
        if not _normalize(self.listed_name):
            raise ValueError("掲載名（listed_name）が空")

    def extra_terms(self) -> list[str]:
        """看板名を取り除いた残り（＝プロフィールに足された語）。

        看板名が掲載名に含まれていない場合は、差分ではなく別名なので空を返す
        （その場合は `violations()` が「一致しない」として別に報告する）。
        """
        base = _normalize(self.storefront_name)
        listed = _normalize(self.listed_name)
        if base not in listed:
            return []
        head, _, tail = listed.partition(base)
        return [t for t in (head, tail) if t]

    def violations(self) -> list[str]:
        """止める理由を列挙する。空リスト＝止める理由が見つからなかった。"""
        found: list[str] = []
        base = _normalize(self.storefront_name)
        listed = _normalize(self.listed_name)

        if base not in listed:
            found.append(
                f"掲載名が看板名と一致しない: 看板「{self.storefront_name}」／"
                f"掲載「{self.listed_name}」。"
                "プロフィールの名称は、店頭で一貫して使っている実際の名称にする"
            )
            return found

        extra = self.extra_terms()
        if extra:
            found.append(
                f"看板に無い語がプロフィール名に足されている: {'／'.join(extra)}。"
                "所在地・キーワード・キャッチコピーを名称に含めるのはガイドライン違反で、"
                "**プロフィールの停止（＝面ごと喪失）につながる**。"
                "地域名や取扱商品は、名称ではなくカテゴリ・説明・投稿・自社サイト側で表す"
            )
        return found

    def assert_matches_storefront(self) -> None:
        """看板名と食い違っていれば ValueError を投げる。"""
        found = self.violations()
        if found:
            raise ValueError(
                "プロフィール名がガイドラインに抵触:\n  - " + "\n  - ".join(found)
            )


class SolicitationTarget(Enum):
    """口コミを頼む相手。**推測せず、呼び出し側が宣言する。**"""

    CUSTOMER = "顧客"
    EMPLOYEE = "従業員・役員"
    FORMER_EMPLOYEE = "元従業員"
    CONTRACTOR = "取引先・業務委託先"
    COMPETITOR = "競合"


# 利害の対立（conflict of interest）にあたる相手。顧客以外はすべてここに入る。
_CONFLICTED = {
    SolicitationTarget.EMPLOYEE,
    SolicitationTarget.FORMER_EMPLOYEE,
    SolicitationTarget.CONTRACTOR,
    SolicitationTarget.COMPETITOR,
}


@dataclass(frozen=True)
class ReviewSolicitation:
    """口コミの依頼ひとつ分（値オブジェクト）。

    Attributes:
        target: 頼む相手
        incentive: 対価（金銭・割引・無料提供・特典・ポイント等）を渡すか。
            **None は「未申告」であり「渡さない」ではない。**
            渡さないなら明示的に False を宣言する。
    """

    target: SolicitationTarget
    incentive: bool | None = None

    def __post_init__(self) -> None:
        require_enum(self.target, SolicitationTarget, "target（頼む相手）")

    def violations(self) -> list[str]:
        """止める理由を列挙する。空リスト＝止める理由が見つからなかった。"""
        found: list[str] = []

        if self.incentive is None:
            found.append(
                "対価の有無（incentive）が未申告のため判定不能。"
                "**未申告を「問題なし」と扱わないこと** — "
                "割引・無料提供・ポイント・次回特典も対価に当たる"
            )
        elif self.incentive:
            found.append(
                "対価と引き換えの口コミ依頼は、プラットフォームのポリシーが認めていない。"
                "**「#PR」等の表示を付けても解決しない** — "
                "日本のステマ規制は事業者の関与の表示を求めるルールであり、"
                "対価つき口コミそのものを許す根拠にはならない。"
                "特典を出したいなら、口コミの対価ではなく"
                "**口コミと切り離した提供**にする（→ `takumi/domain/premium.py` で上限を確かめる）"
            )

        if self.target in _CONFLICTED:
            found.append(
                f"依頼先「{self.target.value}」は利害の対立（conflict of interest）に当たる。"
                "従業員・元従業員・取引先による自社への口コミ、"
                "競合先への投稿は削除の対象。**社内に頼んで数を作らない**"
            )

        return found

    def assert_allowed(self) -> None:
        """止める理由があれば ValueError を投げる。"""
        found = self.violations()
        if found:
            raise ValueError(
                "口コミの依頼が許容されない、または判定不能:\n  - " + "\n  - ".join(found)
            )
