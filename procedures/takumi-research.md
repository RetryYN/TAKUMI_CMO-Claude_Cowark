# /リサーチ — 調査の横断入口（takumi-research）

## 0. どの媒体・対象？（曖昧なときだけ聞く）

要望から対象が読み取れなければ、質問ツールで確認する:

1. **どの媒体・対象を調べる？** — SNS（X/Instagram/TikTok/note/YouTube）/ 競合コンテンツ・訴求 / Webサイト・LP / オウンドメディア・検索market（SEO・キーワード） / その他のWeb情報
2. **何を知りたい？** — 競合の動き / トレンド・伸びてる型 / デザイン・見せ方 / 品質・数値 / 徹底的に全部 / その他

確認した対象・観点はそのセッション中は前提として保持し、同じ質問を繰り返さない（調査記録の冒頭にも書き残す）。

## 0b. 基礎分析が済んでいるか（先に確かめる）

**個別の調査（競合1社・キーワード・デザイン）は、土台の上でしか意味を持たない。**
`knowledge/brands/<slug>/knowledge/analysis/` に基礎分析が無い、または古い場合は、
**先に `docs/parts/foundation-analysis.md` を回すことを提案する**（依頼が明確に個別調査なら、
提案だけして本題に進んでよい）。

基礎分析＝**①環境（PEST/5F/3C/VRIO/バリューチェーン/クロスSWOT）→ ②STP → ③ビジネスモデルと
キャッシュフロー → ④顧客データ → ⑤調査設計**。
**③（儲かるか・現金が回るか）を飛ばした状態で施策の実行に進まない** —
構造的に儲からないモデルに集客を足せば、赤字が速く増えるだけになる。

## 1. 振り分け

| 対象 | 手順 |
|---|---|
| SNS | docs/parts/sns-research.md + 該当媒体の procedures/takumi-sns-*.md（見える範囲・制約） |
| 競合コンテンツ・訴求 | procedures/takumi-content.md のリサーチ行（competitor コンテンツ・訴求の洗い出し） |
| Webサイト・LP のデザイン | docs/parts/style-research.md |
| Webサイト・LP の品質・速度 | docs/parts/site-audit.md |
| **基礎分析**（「戦略を立てたい」「市場を知りたい」「事業を見直したい」） | **docs/parts/foundation-analysis.md**（①環境 ②STP ③ビジネスモデル/CF ④顧客データ ⑤調査設計） |
| 市場・競合・自社の環境（PEST/5F/3C/SWOT/VRIO/バリューチェーン） | `skills/market-analysis-jp` |
| 誰に売るか（セグメント・ターゲット・ポジショニング） | `skills/stp-jp` |
| **儲かるか・現金が回るか**（収益構造・損益分岐点・CCC・獲得コスト） | `skills/business-model-jp` + `takumi/domain/unit_economics.py` |
| 顧客データの集計（RFM/コホート/ファネル/ジャーニー/JTBD） | `skills/customer-analytics-jp` |
| アンケート・定量調査の設計と読み | `skills/quant-research-jp` |
| **伸びている先の分解**（「伸びてる◯◯を参考にしたい」「なぜ伸びているのか」） | **docs/parts/growth-teardown.md** + `skills/growth-teardown-jp`（作法の正本） |
| 徹底的に全部 | docs/parts/deep-research.md |
| オウンドメディア・検索市場（SEO） | procedures/takumi-ownedmedia.md のリサーチ節 + skills/seo-jp/SKILL.md（キーワード・検索意図・競合記事の読み取りのみ） |

## 2. 共通ルール

- 調査は読み取り専用（変更操作なし・ゲート不要）。bot検知・CAPTCHA・レート制限に遭遇したら即中断して報告
- 結果はレポート化するなら logical-writing + docs/conventions.md 準拠。記録先は knowledge/（styles/ audits/ sns/<媒体>/research/）
- 調査結果から制作に進む場合は該当パック（/SNS運用 /コンテンツ /Webサイト）へ引き継ぐ
