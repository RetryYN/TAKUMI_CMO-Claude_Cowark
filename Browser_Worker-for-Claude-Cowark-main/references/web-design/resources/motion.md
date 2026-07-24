# モーションデザイン規範（アニメーション生成）

design-artisan がモックアップに動きを付けるときの基準。動きは「意味の伝達装置」であり装飾ではない。

## 使ってよい場面（目的駆動）

| 目的 | 手法 | 目安 |
|---|---|---|
| スクロールでの段階的開示 | セクションのフェードイン+わずかな上方移動（16〜24px） | 400〜600ms, ease-out |
| 視線誘導 | 主CTAのみ、控えめなアテンション（登場時の一度だけ） | 1回きり。ループ点滅禁止 |
| 状態変化の伝達 | hover/focus の色・影・移動（2〜4px） | 150〜250ms |
| 数値の実感 | 実績数値のカウントアップ（ビューポート進入時に一度） | 800〜1200ms |
| 進捗の可視化 | バー・ステップの伸長 | 300〜500ms |

## 実装ルール

- **transform / opacity のみ**を動かす（layout を揺らす width/height/top のアニメ禁止）
- スクロール連動は **IntersectionObserver**（scroll イベント監視は禁止）:
  ```js
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }), {threshold: 0.15});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  ```
  ```css
  .reveal{opacity:0;transform:translateY(20px);transition:opacity .5s ease-out,transform .5s ease-out}
  .reveal.in{opacity:1;transform:none}
  ```
- **prefers-reduced-motion 必須**（アクセシビリティ・酔い対策）:
  ```css
  @media (prefers-reduced-motion: reduce){
    *,*::before,*::after{animation:none!important;transition:none!important}
    .reveal{opacity:1;transform:none}
  }
  ```
- 同時に動く要素は3つまで。カード群は 60〜100ms の stagger（時差）で
- 初回表示に必須の情報（見出し・CTA）をアニメ待ちにしない（JSなしでも読める= .reveal は JS で付与するか noscript 対応）
- 外部アニメライブラリ（GSAP/Lottie等）は使わない。CSS + 素の JS のみ（自己完結原則）

## 禁止

- 無限ループの点滅・バウンス・回転（注意の恒常的強奪）
- パララックス多用・スクロールジャック（スクロール速度の改変）
- 3秒を超える演出、スプラッシュ画面
- autoplay 動画・音声

## 納品時

- アニメーション付きモックアップは**アーティファクトとして発行**する（静的スクショでは動きを評価できないため）。共有URLと合わせて「どこがどう動くか」の一覧をレポートに記載
