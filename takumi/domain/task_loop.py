"""タスク単位のエージェントループ — 1つの仕事を「構える→作る→咎める→確かめる」で回す。

**なぜコードにするか**: 匠の∞ループ（`loop.py`）はブランド・キャンペーンの粒度で、
戦略と実行を計画と計測で結ぶ。だが**個々のタスクの中にも同じ形のループがある** —
そしてそちらは今まで、成果物の種類ごとにばらばらの手順として書かれていた
（design-artisan→design-critic の2周、pre-send-verifier→承認→outcome-verifier、
設定前の並列合議）。**同じ形なのに毎回別々に書かれていると、抜ける。**

フェーズは `docs/agent-tiers.md` の級と**1対1**に対応する:

| フェーズ | 級 | 問い |
|---|---|---|
| **構える**（FRAME） | 戦略級 | 何ができたら終わりか |
| **作る**（MAKE） | 職人級 | 実際に作る |
| **咎める**（CHALLENGE） | 戦術級 | 通すか止めるか |
| **確かめる**（CONFIRM） | 作業者級 | 証跡で確定数を数える |

ここが強制するのは4つだけ:

1. **何ができたら終わりかを書かずに始めない**（完了条件の無いループは止まらない）
2. **級を飛ばさない・下の級に上の級の仕事をさせない**
3. **2周で通らないものは人間に返す**（3周目に入らせない）
4. **確かめずに完了しない**（不可逆送出は事前監査も必須）

**このループは「何を作るか」には一切関与しない。** 進め方だけを持つ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# 差し戻して作り直してよい回数。**これを超えたら設計が悪い**ので人間に返す。
# （docs/parts/page-improve.md の「最大2周」を全タスクの規則へ引き上げたもの）
MAX_ROUNDS = 2

# 咎める段で「通らなかった」を意味する判定。呼び出し側が宣言する。
REVISE_VERDICTS = ("REVISE", "NO-GO", "RETHINK", "FAIL")


class AgentTier(Enum):
    """エージェントの級。正本は `docs/agent-tiers.md`。"""

    STRATEGIC = "戦略級"
    TACTICAL = "戦術級"
    ARTISAN = "職人級"
    WORKER = "作業者級"


class LoopPhase(Enum):
    """タスクループの4フェーズ。級と1対1。"""

    FRAME = "構える"
    MAKE = "作る"
    CHALLENGE = "咎める"
    CONFIRM = "確かめる"

    @property
    def tier(self) -> AgentTier:
        return _PHASE_TIER[self]


_PHASE_TIER = {
    LoopPhase.FRAME: AgentTier.STRATEGIC,
    LoopPhase.MAKE: AgentTier.ARTISAN,
    LoopPhase.CHALLENGE: AgentTier.TACTICAL,
    LoopPhase.CONFIRM: AgentTier.WORKER,
}


@dataclass(frozen=True)
class Step:
    """1回の委譲の記録。"""

    phase: LoopPhase
    agent: str
    verdict: str | None = None

    @property
    def sent_back(self) -> bool:
        return (self.verdict or "").upper() in REVISE_VERDICTS


@dataclass
class TaskLoop:
    """1タスク分のループ（エンティティ。同一性はタスク名）。

    Attributes:
        task_name: タスク名
        completion_condition: **何ができたら終わりか**。空では作れない
        irreversible: 不可逆送出（送信・投稿・公開・配信）を含むか。**人間が宣言する**
        skip_frame_reason: 「構える」を省略する理由。省略するなら宣言させる
    """

    task_name: str
    completion_condition: str
    irreversible: bool = False
    skip_frame_reason: str = ""
    steps: list[Step] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.task_name.strip(" 　\t\n"):
            raise ValueError("タスク名が空")
        if not self.completion_condition.strip(" 　\t\n"):
            raise ValueError(
                "完了条件（completion_condition）が空 — **何ができたら終わりかを書かずに始めない**。"
                "書けないなら、それはまだタスクではなく願望であり、"
                "回すほどに「もう少し良くなるかも」で止まらなくなる"
            )

    # --- 状態 ---

    @property
    def frame_skipped(self) -> bool:
        return bool(self.skip_frame_reason.strip(" 　\t\n"))

    @property
    def rounds(self) -> int:
        """「作る」を通った回数＝周回数。"""
        return sum(1 for s in self.steps if s.phase is LoopPhase.MAKE)

    @property
    def last_challenge(self) -> Step | None:
        for s in reversed(self.steps):
            if s.phase is LoopPhase.CHALLENGE:
                return s
        return None

    def _phases(self) -> list[LoopPhase]:
        return [s.phase for s in self.steps]

    # --- 進行 ---

    def record(
        self,
        phase: LoopPhase,
        tier: AgentTier,
        *,
        agent: str,
        verdict: str | None = None,
    ) -> None:
        """1回の委譲を記録する。順序・級・周回の不変条件を破ったら ValueError。"""
        if tier is not phase.tier:
            raise ValueError(
                f"「{phase.value}」は{phase.tier.value}の仕事だが、"
                f"{tier.value}のエージェント（{agent}）に委譲しようとしている。"
                "**下の級に上の級の仕事をさせない／上の級に下の級の作業をさせない** "
                "— 級の対応は docs/agent-tiers.md"
            )

        done = self._phases()
        if done and done[-1] is phase:
            raise ValueError(
                f"「{phase.value}」を続けて回そうとしている。"
                "**審査を挟まない反復は品質を上げない**（作る→作る は自己満足、"
                "咎める→咎める は基準が無い証拠）。間に別のフェーズを通す"
            )

        if phase is LoopPhase.CHALLENGE and LoopPhase.MAKE not in done:
            raise ValueError(
                "まだ「作る」を通っていないのに「咎める」に入ろうとしている。"
                "審査対象が無い"
            )
        if phase is LoopPhase.CONFIRM and LoopPhase.CHALLENGE not in done:
            raise ValueError(
                "まだ「咎める」を通っていないのに「確かめる」に入ろうとしている。"
                "**通っていないものの成果を数えない**"
            )
        if phase is LoopPhase.MAKE and self.rounds >= MAX_ROUNDS:
            raise ValueError(
                f"{MAX_ROUNDS}周してまだ通っていない。**3周目に入らない** — "
                "ここまで通らないのは作り方ではなく設計（完了条件・前提・依頼内容）の問題で、"
                "回しても収束しない。**残った指摘を『人間レビュー事項』として添えて人間に返す**"
            )

        self.steps.append(Step(phase=phase, agent=agent, verdict=verdict))

    # --- 判定 ---

    def warnings(self) -> list[str]:
        """止めはしないが、報告に残すべきこと。"""
        found: list[str] = []
        if LoopPhase.FRAME not in self._phases() and not self.frame_skipped:
            found.append(
                "「構える」を通らずに作り始めている（省略の理由も宣言されていない）。"
                "**何ができたら終わりかが決まっていないまま作ると、"
                "咎める段の基準が後付けになる**"
            )
        return found

    def blockers(self) -> list[str]:
        """完了を止める理由を列挙する。空リスト＝完了してよい。"""
        found: list[str] = []
        done = self._phases()

        if LoopPhase.CONFIRM not in done:
            found.append(
                "「確かめる」を通っていない。**作ったことと効いたことは別** — "
                "証跡のある確定数だけを成果に数える"
            )

        last = self.last_challenge
        if last is None:
            found.append("「咎める」を通っていない（誰も止める側に立っていない）")
        elif last.sent_back:
            found.append(
                f"最後の審査が {last.verdict} のまま完了しようとしている。"
                "**差し戻しを抱えたまま引き渡さない**"
            )

        if self.irreversible and not any(
            s.phase is LoopPhase.CHALLENGE and s.agent == "pre-send-verifier"
            for s in self.steps
        ):
            found.append(
                "不可逆送出を含むタスクなのに `pre-send-verifier` の事前監査が無い。"
                "**送ったものは取り消せない** — 咎める段はこのエージェントで通す"
            )

        return found

    def assert_completable(self) -> None:
        """完了できない理由があれば ValueError を投げる。"""
        found = self.blockers()
        if found:
            raise ValueError(
                f"タスク「{self.task_name}」はまだ完了できない:\n  - " + "\n  - ".join(found)
            )
