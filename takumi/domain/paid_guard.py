"""ゼロ広告費の共通判定 — 「有料前提の語」を名前から検出する。

KpiNode（指標）と Channel（媒体）の両方が使う。**過剰検知もこのガードの失敗**である:
実在するオーガニック媒体 "Threads" が "ads" の部分一致で弾かれる事故があった（2026-07-25）。
そのためラテン文字の語は**単語境界**で照合し、日本語の語だけ部分一致で見る
（日本語は語の区切りが無く、「広告費」「純広告」を一括で拾うには部分一致が要る）。
"""
from __future__ import annotations

import re

# 日本語は部分一致（語の区切りが無いため）
JA_PAID_METRICS = ("広告費", "広告予算", "出稿", "入札")
JA_PAID_CHANNELS = (
    "広告", "リスティング", "ディスプレイ", "出稿", "純広",
    "タイアップ", "アフィリエイト", "インフルエンサー", "スポンサード", "プロモ枠",
)

# ラテン文字は単語境界で照合（部分一致だと Threads→ads、cache→cac のような誤検知が出る）
EN_PAID_METRICS = (r"cac", r"ltv", r"roas", r"cpa", r"cpc", r"cpm", r"ad ?spend")
EN_PAID_CHANNELS = (r"ads", r"adwords", r"ppc", r"sponsored", r"sns ?ads")


def find_paid_token(name: str, ja_tokens, en_tokens) -> str | None:
    """有料前提の語を見つけたら返す。無ければ None。"""
    lowered = name.lower()
    squashed = lowered.replace(" ", "").replace("　", "")
    for token in ja_tokens:
        if token in squashed:
            return token
    for token in en_tokens:
        if re.search(rf"(?<![a-z]){token}(?![a-z])", lowered):
            return token
    return None
