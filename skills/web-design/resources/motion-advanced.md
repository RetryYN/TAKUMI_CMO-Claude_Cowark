# モーション実装・上級編（easing設計 / FLIP / Scroll-driven）

motion.md（基本規範）の拡張。公開仕様・研究の再構成。

## 1. easing / duration 判定テーブル

**easing の選び方（進入は減速・退出は加速が大原則）**

| 場面 | easing | 理由 |
|---|---|---|
| 要素の登場（fade-in/slide-in） | `cubic-bezier(0, 0, 0.2, 1)`（decelerate） | 素早く現れ静かに止まる=自然 |
| 要素の退出 | `cubic-bezier(0.4, 0, 1, 1)`（accelerate） | 加速して去る=消えた感 |
| 画面内の移動・変形 | `cubic-bezier(0.4, 0, 0.2, 1)`（standard） | 両端が滑らか |
| hover等の微小変化 | `ease-out` で十分 | 150ms級では差が出ない |
| 遊び・弾み（強調CTA登場等） | `cubic-bezier(0.34, 1.56, 0.64, 1)`（軽いoverstoot） | 使うのは1画面1箇所まで |

**duration の基準**

| 対象 | 目安 |
|---|---|
| hover / focus / 色変化 | 150〜200ms |
| 小要素の出入り（ボタン・チップ） | 200〜300ms |
| カード・モーダル等の中要素 | 300〜400ms |
| セクション reveal・大要素 | 400〜600ms |
| カウントアップ等の演出 | 800〜1200ms |

補正ルール: 移動距離が長い/要素が大きいほど長く（+30%目安）。退出は進入より2〜3割短く。同時要素は stagger 60〜100ms。**500ms を超える UI 応答は「遅い」と知覚される**。

## 2. FLIP テクニック（レイアウト変化を transform で再生する）

アコーディオン展開・カード拡大・リスト並べ替えなど「layout プロパティが変わる」演出を、
transform/opacity 限定ルールを守ったまま実現する唯一の一般解。

**First → Last → Invert → Play**:

```js
function flip(el, mutate){
  const first = el.getBoundingClientRect();      // First: 変化前を計測
  mutate();                                       // DOM を最終状態へ（クラス付与等）
  const last = el.getBoundingClientRect();       // Last: 変化後を計測
  const dx = first.left - last.left, dy = first.top - last.top;
  const sx = first.width / last.width, sy = first.height / last.height;
  el.animate(                                     // Invert→Play: 差分を transform で逆再生
    [{transform:`translate(${dx}px,${dy}px) scale(${sx},${sy})`},{transform:'none'}],
    {duration:300, easing:'cubic-bezier(0.4,0,0.2,1)'});
}
```

- 計測（getBoundingClientRect）はアニメ開始**前**にまとめて行う（再生中の layout 読み取り禁止）
- `transform-origin: top left` を設定してから scale する
- 子要素の歪みが目立つ場合は逆スケールの補正が必要になる — その複雑度に見合わない演出なら単純な fade に落とす判断を

## 3. Scroll-driven Animations API（IntersectionObserver の上位互換）

CSS だけでスクロール連動が書け、compositor スレッドで動くため JS 版より滑らか。

```css
/* リーディングプログレスバー */
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.progress{transform-origin:left;animation:grow linear;animation-timeline:scroll(root)}

/* ビューポート進入で reveal */
@keyframes reveal-in{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
.reveal{animation:reveal-in .5s ease-out both;
        animation-timeline:view();animation-range:entry 0% entry 60%}
```

**必ず @supports でフォールバック**（未対応ブラウザでは IntersectionObserver 版 or 即時表示）:

```css
.reveal{opacity:1}
@supports (animation-timeline: view()){
  .reveal{animation:reveal-in .5s ease-out both;
          animation-timeline:view();animation-range:entry 0% entry 60%}
}
```

## 4. reduced-motion の深化 — 「消す」ではなく「置換する」

`prefers-reduced-motion: reduce` は「アニメ全カット」より**酔わせる成分だけ除去**が正しい:

| 元の動き | reduce 時の置換 |
|---|---|
| slide / translate 系 | fade（opacity のみ）に置換 |
| scale / zoom 系 | fade に置換 |
| パララックス・背景速度差 | 完全停止（これが最大の酔い要因） |
| カウントアップ | 最終値を即時表示 |
| 色・不透明度の変化 | そのまま維持してよい |

```css
@media (prefers-reduced-motion: reduce){
  .reveal{animation:none;opacity:0;transition:opacity .4s ease}
  .reveal.in{opacity:1}   /* 移動なしの fade だけ残す */
}
```

酔いの三大要因（避ける/reduce で必ず殺す）: パララックス多用、大面積の横スワイプ遷移、前景と背景の速度差。
