#!/usr/bin/env python3
"""Delvework クロマキー切り抜きテンプレート — 2026-07-23 Cowork 実機検証済みの型。
グリーンバック指定で生成した画像（Gemini に「背景は #00FF00 一色」と指定）から
被写体を透過PNGとして切り抜く。ML モデル不要・決定論的・数秒で完了。

  python3 chromakey.py <入力画像> <出力.png> [--bg <合成背景色 or 画像パス>]

処理: 「緑の優勢度」から連続アルファを生成（単純な色一致より輪郭のジャギーが出ない）
      + 髪・輪郭に残る緑かぶり（スピル）の抑制。
--bg を指定すると切り抜き結果を背景に合成した確認用画像も出力する。
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def chroma_key(img: Image.Image, softness: float = 1.0) -> Image.Image:
    """緑の優勢度ベースの連続アルファでグリーンバックを抜く。"""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    # 緑の優勢度: G が R/B の最大値をどれだけ上回るか（0..255）
    dominance = g - np.maximum(r, b)

    # 優勢度 → アルファ（連続値）。しきい値2点の間を線形補間してジャギーを抑える
    lo, hi = 12.0 * softness, 72.0 * softness   # lo 未満=前景(不透明) / hi 超=背景(透明)
    alpha = np.clip((hi - dominance) / (hi - lo), 0.0, 1.0)

    # スピル抑制: 前景側でも G が R/B より突出している画素は G を抑える（緑かぶり除去）
    spill = np.clip(dominance, 0, None) * (alpha > 0.05)
    g_fixed = g - spill * 0.85
    rgb_out = np.stack([r, g_fixed, b], axis=-1)

    out = np.dstack([np.clip(rgb_out, 0, 255), alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def composite_check(fg: Image.Image, bg_spec: str) -> Image.Image:
    """確認用: 切り抜き結果を指定背景（色 or 画像）に合成する。"""
    if Path(bg_spec).is_file():
        bg = Image.open(bg_spec).convert("RGBA").resize(fg.size, Image.LANCZOS)
    else:
        bg = Image.new("RGBA", fg.size, bg_spec)
    return Image.alpha_composite(bg, fg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", help="透過PNGの出力先（.png）")
    ap.add_argument("--bg", default="", help="確認用合成の背景（色コード or 画像パス）。<dst>-check.png に出力")
    ap.add_argument("--softness", type=float, default=1.0, help="輪郭の柔らかさ（既定1.0。ジャギーが出るなら上げる）")
    a = ap.parse_args()

    cut = chroma_key(Image.open(a.src), a.softness)
    cut.save(a.dst)
    print(f"saved: {a.dst} (RGBA)")
    if a.bg:
        check_path = str(Path(a.dst).with_suffix("")) + "-check.png"
        composite_check(cut, a.bg).convert("RGB").save(check_path)
        print(f"saved: {check_path} (合成確認)")
