#!/usr/bin/env python3
"""Delvework バナー合成テンプレート — 2026-07-23 Cowork 実機検証済みの型。
背景画像 + キャッチコピー + サブコピー + バッジを1枚のバナーに焼き込む。

  python3 banner-compose.py <入力画像> <出力.png> --headline "朝いちばんの仕事は、AIが終わらせてる。" \
      --sub "ブラウザ定常業務の自動化 — Delvework" --badge "導入事例 公開中"

処理: 16:9 センタートリミング → 1280x720 リサイズ → 下部グラデーション（可読性確保）→ テキスト焼き込み。
フォントは Noto Sans CJK を探し、無ければ環境の日本語フォントにフォールバック。
コピー文言は copywriting スキルで作成し、公開前に ad-compliance-jp チェックを通すこと（手順書参照）。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

FONT_CANDIDATES = [
    # Linux (Cowork sandbox / CI)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJKjp-Bold.otf",
    # Windows
    "C:/Windows/Fonts/NotoSansJP-Bold.ttf",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    # macOS
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    print("WARN: 日本語フォント未検出 — デフォルトフォント使用（日本語が豆腐になる可能性）", file=sys.stderr)
    return ImageFont.load_default()


def center_crop_16_9(img: Image.Image) -> Image.Image:
    w, h = img.size
    target = 16 / 9
    if w / h > target:  # 横長すぎ → 左右を落とす
        nw = int(h * target)
        x = (w - nw) // 2
        img = img.crop((x, 0, x + nw, h))
    else:  # 縦長すぎ → 上下を落とす
        nh = int(w / target)
        y = (h - nh) // 2
        img = img.crop((0, y, w, y + nh))
    return img.resize((W, H), Image.LANCZOS)


def bottom_gradient(img: Image.Image, height_ratio: float = 0.45, max_alpha: int = 200) -> Image.Image:
    """下部にテキスト可読性のための黒グラデーションを重ねる。"""
    img = img.convert("RGBA")
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(grad)
    gh = int(H * height_ratio)
    for i in range(gh):
        alpha = int(max_alpha * (i / gh) ** 1.5)
        d.line([(0, H - gh + i), (W, H - gh + i)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img, grad)


def compose(src: str, dst: str, headline: str, sub: str = "", badge: str = "",
            accent: str = "#1a6ee0") -> None:
    img = center_crop_16_9(Image.open(src))
    img = bottom_gradient(img)
    d = ImageDraw.Draw(img)

    margin = 64
    y = H - margin

    if sub:
        f_sub = load_font(30)
        sub_h = d.textbbox((0, 0), sub, font=f_sub)[3]
        y -= sub_h
        d.text((margin, y), sub, font=f_sub, fill=accent,
               stroke_width=2, stroke_fill=(255, 255, 255, 230))
        y -= 16

    f_head = load_font(58)
    head_h = d.textbbox((0, 0), headline, font=f_head)[3]
    y -= head_h
    d.text((margin, y), headline, font=f_head, fill=(255, 255, 255),
           stroke_width=3, stroke_fill=(0, 0, 0, 160))
    y -= 24

    if badge:
        f_badge = load_font(26)
        bb = d.textbbox((0, 0), badge, font=f_badge)
        pad_x, pad_y = 18, 10
        bw, bh = bb[2] + pad_x * 2, bb[3] + pad_y * 2
        y -= bh
        d.rounded_rectangle([margin, y, margin + bw, y + bh], radius=8, fill=accent)
        d.text((margin + pad_x, y + pad_y - bb[1] // 2), badge, font=f_badge, fill=(255, 255, 255))

    img.convert("RGB").save(dst, quality=95)
    print(f"saved: {dst} ({W}x{H})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--headline", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--badge", default="")
    ap.add_argument("--accent", default="#1a6ee0")
    a = ap.parse_args()
    compose(a.src, a.dst, a.headline, a.sub, a.badge, a.accent)
