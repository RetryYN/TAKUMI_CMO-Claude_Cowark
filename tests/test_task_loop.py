"""タスク単位のエージェントループの不変条件テスト（TDD: このファイルが先に赤くなる）。

守りたいのは4点:

1. **何ができたら終わりかを書かずに始めない**（完了条件の無いループは止まらない）
2. **級を飛ばさない・下の級に上の級の仕事をさせない**（フェーズと級は1対1）
3. **2周で通らないものは人間に返す**（3周目に入らせない＝無限ループ禁止）
4. **確かめずに完了しない**（作ったことと効いたことは別。不可逆送出は監査必須）
"""
import ast
import unittest
from pathlib import Path

from takumi.domain.task_loop import (
    MAX_ROUNDS,
    AgentTier,
    LoopPhase,
    TaskLoop,
)


def _loop(**kw) -> TaskLoop:
    kw.setdefault("task_name", "LP改善")
    kw.setdefault("completion_condition", "critic が PASS を出し、実測の直帰率が前週を下回る")
    return TaskLoop(**kw)


class TestCompletionCondition(unittest.TestCase):
    def test_完了条件が空なら作れない(self):
        with self.assertRaises(ValueError) as cm:
            _loop(completion_condition="   ")
        self.assertIn("終わり", str(cm.exception))

    def test_タスク名が空なら作れない(self):
        with self.assertRaises(ValueError):
            _loop(task_name="")


class TestPhaseTier(unittest.TestCase):
    def test_フェーズと級は1対1(self):
        self.assertEqual(LoopPhase.FRAME.tier, AgentTier.STRATEGIC)
        self.assertEqual(LoopPhase.MAKE.tier, AgentTier.ARTISAN)
        self.assertEqual(LoopPhase.CHALLENGE.tier, AgentTier.TACTICAL)
        self.assertEqual(LoopPhase.CONFIRM.tier, AgentTier.WORKER)

    def test_級が食い違う委譲は拒否する(self):
        """職人級の仕事を戦略級にやらせない（逆も同じ）。"""
        loop = _loop()
        with self.assertRaises(ValueError) as cm:
            loop.record(LoopPhase.MAKE, AgentTier.STRATEGIC, agent="cmo-strategist")
        self.assertIn("級", str(cm.exception))


class TestPhaseOrder(unittest.TestCase):
    def test_正順は通る(self):
        loop = _loop()
        loop.record(LoopPhase.FRAME, AgentTier.STRATEGIC, agent="cmo-strategist")
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic")
        loop.record(LoopPhase.CONFIRM, AgentTier.WORKER, agent="outcome-verifier")
        self.assertEqual(loop.rounds, 1)

    def test_作る前に咎められない(self):
        loop = _loop()
        with self.assertRaises(ValueError) as cm:
            loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic")
        self.assertIn("作る", str(cm.exception))

    def test_同じフェーズを続けて回せない(self):
        """作る→作る では品質は上がらない（審査を挟まない反復は自己満足）。"""
        loop = _loop()
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        with self.assertRaises(ValueError) as cm:
            loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        self.assertIn("続けて", str(cm.exception))

    def test_構えるを省略するには理由が要る(self):
        """小さいタスクで省略してよいが、黙って飛ばさせない。"""
        loop = _loop(skip_frame_reason="読み取りのみ・不可逆操作なし")
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="deliverable-writer")
        self.assertTrue(loop.frame_skipped)

    def test_理由なしで構えるを飛ばすと記録に残る(self):
        loop = _loop()
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="deliverable-writer")
        self.assertIn("構える", "".join(loop.warnings()))


class TestRounds(unittest.TestCase):
    def _one_round(self, loop: TaskLoop, verdict: str) -> None:
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic",
                    verdict=verdict)

    def test_差し戻しで周回が増える(self):
        loop = _loop(skip_frame_reason="小改修")
        self._one_round(loop, "REVISE")
        self.assertEqual(loop.rounds, 1)
        self._one_round(loop, "PASS")
        self.assertEqual(loop.rounds, 2)

    def test_三周目に入れない(self):
        loop = _loop(skip_frame_reason="小改修")
        self._one_round(loop, "REVISE")
        self._one_round(loop, "REVISE")
        with self.assertRaises(ValueError) as cm:
            loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        msg = str(cm.exception)
        self.assertIn(str(MAX_ROUNDS), msg)
        self.assertIn("人間", msg)

    def test_上限は2周(self):
        self.assertEqual(MAX_ROUNDS, 2)


class TestCompletion(unittest.TestCase):
    def test_確かめずに完了できない(self):
        loop = _loop(skip_frame_reason="小改修")
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="deliverable-writer")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="pre-send-verifier")
        with self.assertRaises(ValueError) as cm:
            loop.assert_completable()
        self.assertIn("確かめ", str(cm.exception))

    def test_差し戻しのまま完了できない(self):
        loop = _loop(skip_frame_reason="小改修")
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic",
                    verdict="REVISE")
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="design-artisan")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic",
                    verdict="REVISE")
        loop.record(LoopPhase.CONFIRM, AgentTier.WORKER, agent="outcome-verifier")
        with self.assertRaises(ValueError) as cm:
            loop.assert_completable()
        self.assertIn("REVISE", str(cm.exception))

    def test_不可逆送出は事前監査がないと完了できない(self):
        loop = _loop(skip_frame_reason="定型配信", irreversible=True)
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="deliverable-writer")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="design-critic",
                    verdict="PASS")
        loop.record(LoopPhase.CONFIRM, AgentTier.WORKER, agent="outcome-verifier")
        with self.assertRaises(ValueError) as cm:
            loop.assert_completable()
        self.assertIn("pre-send-verifier", str(cm.exception))

    def test_正しく一周すれば完了できる(self):
        loop = _loop(skip_frame_reason="定型配信", irreversible=True)
        loop.record(LoopPhase.MAKE, AgentTier.ARTISAN, agent="deliverable-writer")
        loop.record(LoopPhase.CHALLENGE, AgentTier.TACTICAL, agent="pre-send-verifier",
                    verdict="GO")
        loop.record(LoopPhase.CONFIRM, AgentTier.WORKER, agent="outcome-verifier")
        loop.assert_completable()  # 例外を投げない


class TestNoKpiTreeDependency(unittest.TestCase):
    def test_kpiツリーに依存しない(self):
        """ループの進行規則は、動かす指標とは別の層にある。"""
        import takumi.domain.task_loop as tl

        tree = ast.parse(Path(tl.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse([m for m in imported if "kpi_tree" in m])


if __name__ == "__main__":
    unittest.main()
