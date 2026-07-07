# 文書生成品質の改善 (2026-07-07)

出力する医療文書の生成品質を上げるための5つの改善を実装する。

## 1. 出力途中切れの検知

**問題:** Claude API呼び出しは `max_tokens=6000` 固定だが `stop_reason` を確認しておらず、長いカルテで出力が上限に達すると、途中で切れた文書がそのまま成功として返っていた。

**対応:** `stop_reason == "max_tokens"` を検知した場合、生成文書の末尾に警告を付加する。

> ※出力が上限に達したため、文書が途中で切れている可能性があります

- 変更ファイル: `app/external/claude_api.py`
- メッセージ定数: `MESSAGES["WARNING"]["OUTPUT_TRUNCATED"]` (`app/core/constants.py`)

## 2. 半角スペース全削除の修正

**問題:** `format_output_summary` が `.replace(' ', '')` で半角スペースをすべて削除しており、英語表記が壊れていた（例: `CRP 0.5 mg/dL` → `CRP0.5mg/dL`、`Parkinson disease` → `Parkinsondisease`）。

**対応:** 全角文字（日本語）に隣接するスペースのみ削除し、英数字間のスペースは保持する。行末の余分なスペースも削除する。

| 入力 | 変更前 | 変更後 |
|---|---|---|
| `備考 : 定期フォロー` | `備考:定期フォロー` | `備考:定期フォロー` (変わらず) |
| `CRP 0.5 mg/dL` | `CRP0.5mg/dL` | `CRP 0.5 mg/dL` |
| `Parkinson disease あり` | `Parkinsondiseaseあり` | `Parkinson diseaseあり` |

- 変更ファイル: `app/utils/text_processor.py`

## 3. プロンプト構造の改善

**問題:** プロンプトテンプレートとカルテ本文を単純連結した1つのuserメッセージで送信しており、system promptもtemperature指定もなかった。

**対応:**

- テンプレート（指示）を **system prompt** に、カルテ等のデータを **userメッセージ** に分離。指示とデータの境界が明確になり、プロンプトインジェクション耐性と指示追従が向上
- データをXMLタグで区切って送信: `<カルテ情報>` `<前回の記載>` `<追加情報>`
- system promptに grounding 指示を常時付加（`GROUNDING_INSTRUCTION`）: カルテに記載のない情報を追加しない・記載日時に沿って時系列で整理する
- Claudeに `temperature=0.2` を設定（`CLAUDE_GENERATION_TEMPERATURE`）。医療文書のため事実性・再現性を優先。Geminiはthinkingモデルの推奨に従いデフォルト温度を維持し、`system_instruction` のみ対応

- 変更ファイル: `app/external/base_api.py`、`app/external/claude_api.py`、`app/external/gemini_api.py`、`app/core/constants.py`

## 4. JSON形式カルテへの対応

**問題:** カルテはJSON形式に変換して取り込んでいるのに、プロンプト側はJSONであることをモデルに伝えていなかった。

**対応:** カルテ情報がJSONとしてパースできる場合、system promptに指示（`KARTE_JSON_INSTRUCTION`）を自動で追加する。

- JSON形式であることを明示
- 日時フィールドをもとに時系列を把握する
- JSONのキー名を文書に転記しない

- 変更ファイル: `app/external/base_api.py`（`_is_json_text` で判定）

## 5. 検証フィードバックループ

**問題:** Geminiによる評価結果は画面に表示するだけで、文書の修正につながっていなかった。

**対応:** 生成 → 評価 → 修正のループを実現した。

### 5-1. 評価プロンプトの改善

- 評価用プロンプトもsystem/user分離・XMLタグ化（`<カルテ記載>` `<前回の記載>` `<追加情報>` `<生成された出力>`）
- 根拠引用指示（`EVALUATION_GROUNDING_INSTRUCTION`）を常時付加: 各指摘にカルテの該当箇所を引用させ、カルテに根拠のない記述はハルシネーションの可能性として必ず指摘させる。DBに登録済みの評価プロンプトを編集しなくても有効

### 5-2. 指摘を反映した再生成

- 評価画面に **「指摘を反映して再生成」** ボタンを追加
- 前回の生成結果と評価結果を `<前回の生成結果>` `<評価結果>` タグでモデルに渡し、修正版を再生成する（`REFINEMENT_INSTRUCTION`）
- APIは `SummaryRequest` の `previous_summary` / `evaluation_feedback` フィールドで受け取る（両方指定時のみ有効）。既存の生成パイプライン（サニタイズ・監査ログ・日次利用制限）をそのまま通る

- 変更ファイル: `app/services/evaluation_service.py`、`app/services/summary_service.py`、`app/external/api_factory.py`、`app/schemas/summary.py`、`app/api/summary.py`、`frontend/src/app.ts`、`app/templates/components/evaluation_screen.html`
