# コードレビュー (2026-10-01)

対象: `app/` (Python) と `frontend/src/` (TypeScript)、および `app/templates/` 内のインラインスクリプト。
観点: 可読性・メンテナンス性・KISS。優先度の高い順に記載。

確認方法: 全ソースの通読と `npx tsc --noEmit` の実行。pytest / pyright は実行していない。

## サマリ

| # | 優先度 | 指摘 | 主な対象 |
|---|---|---|---|
| 1 | 高 | 型チェックが 25 件のエラーで失敗している | `frontend/src/app.ts`, `types.ts` |
| 2 | 高 | ストリーミング版と非ストリーミング版でロジックが二重化している | `summary_service.py`, `evaluation_service.py`, `app.ts` |
| 3 | 高 | 10〜12 個の引数を 5 層にわたって受け渡している | `api/summary.py` → `base_api.py` |
| 4 | 高 | 「ストリーミング」の階層が実際には使われていない | `base_api.py`, `gemini_api.py`, `api_factory.py` |
| 5 | 中 | `stream_with_heartbeat` が Queue と二重の結果処理で複雑 | `sse_helpers.py` |
| 6 | 中 | 評価サービスの検証・モデル解決が回りくどい | `evaluation_service.py` |
| 7 | 中 | API クライアントの初期化と例外ラップが多層 | `claude_api.py`, `gemini_api.py`, `base_api.py` |
| 8 | 中 | メッセージ定数の重複・未使用・定数化漏れ | `constants.py` ほか |
| 9 | 中 | `parse_output_summary` のパターンとフラグが冗長 | `text_processor.py`, `constants.py` |
| 10 | 中 | ORM の型付けを `Any` / `cast` / `setattr` で回避している | `models/`, `services/` |
| 11 | 低 | 小さな重複と未使用コード | 各所 |
| 12 | 低 | テンプレート内インラインスクリプトの重複 | `app/templates/*.html` |

---

## 1. [高] フロントエンドの型チェックが失敗している

`cd frontend && npx tsc --noEmit` が 25 件のエラーを出す。Vite のビルドは型チェックをしないため、気づかれないまま残っている。

原因は 3 つ。

- `window.CSRF_TOKEN` / `TAB_NAMES` / `MESSAGES` / `DOCUMENT_PURPOSE_MAPPING` / `DOCUMENT_TYPES` の型宣言がない (`app.ts:64,105,124,207` ほか)。`DOCUMENT_TYPES` だけ `(window as any)` で回避している (`app.ts:76`)。
- `FormData` に `referralPurpose` がない (`types.ts:10`、使用箇所は `app.ts:83,125,187,352`)。
- `AppState` に `updateSelectedModel` がない (`app.ts:120` で呼び出し、`app.ts:148` で定義)。

対応案:

- `frontend/src/globals.d.ts` に `interface Window { ... }` を追加し、`(window as any)` を外す。
- `FormData` に `referralPurpose: string` を追加する。なお `FormData` は DOM 標準の型名と衝突するため、`ReferralForm` などへの改名を勧める。
- `AppState` インターフェースに `updateSelectedModel(): Promise<void>` を追加する。
- `frontend/package.json` の `build` を `tsc --noEmit && vite build` にして再発を防ぐ。

## 2. [高] ストリーミング版と非ストリーミング版の二重化

同じ処理が 2 系統ずつ存在し、コード量の最大の要因になっている。

| 対象 | 重複箇所 |
|---|---|
| `summary_service.py` | `execute_summary_generation` (61-211) と `execute_summary_generation_stream` (255-415)。監査ログ → 日次制限 → サニタイズ → 検証 → モデル決定までの約 90 行が同一 |
| `evaluation_service.py` | `execute_evaluation` (121-213) と `execute_evaluation_stream` (246-329) |
| `app.ts` | `processSSEStream` / `processEvaluationSSEStream` (245-279, 451-485) は呼び出すハンドラ以外同一。`handleSSEEvent` / `handleEvaluationSSEEvent`、`startTimer` / `startEvaluationTimer`、2 つの `*Fallback` も同様 |

重複がすでに挙動の差を生んでいる。ストリーミング経路では API 呼び出しが失敗しても `DOCUMENT_GENERATION_FAILURE` / `EVALUATION_FAILURE` の監査ログが記録されない (`sse_helpers.py:41-44` がエラーを SSE 文字列に変換し、`summary_service.py:373-374` はそれをそのまま転送するだけ)。非ストリーミング経路 (`summary_service.py:165-172`) では記録される。

### 推奨: 非ストリーミング経路を廃止する

非ストリーミング API はフロントエンドのフォールバック専用になっている。このフォールバックは効果が薄い。

- ストリーミングが 401 / 403 / 422 で失敗した場合、フォールバックも同じ理由で失敗する。
- ストリーム途中の切断でフォールバックすると、同じ文書を二重に生成し、利用量も二重に計上される。

廃止すれば `execute_summary_generation`、`execute_evaluation`、`/generate`、`/evaluate`、`generateSummaryFallback`、`evaluateOutputFallback`、`BaseAPIClient.generate_summary`、`generate_summary_with_provider` が不要になる。削減量は Python で約 250 行、TypeScript で約 60 行。対応するテスト (`tests/api/test_summary.py`、`tests/services/test_summary_service.py` など) の書き換えが必要。

### フロントエンド 

- SSE 読み取りを `readSSE(response, onEvent)` の 1 関数にまとめ、`event` と `data` のパースもそこで行う。
- タイマーは 1 組にする。生成と評価は同時に走らないため、`elapsedTime` / `timerInterval` を共有できる。
- 結果の初期値を `emptyResult()` / `emptyEvaluation()` にまとめる。同じリテラルが `app.ts:90-96,305-311,335-341,357-363` に 4 回ある。
- 評価リクエストの body も `buildEvaluationRequestBody()` に切り出す (`app.ts:420-426,530-536`)。

## 3. [高] 長い引数リストの多層受け渡し

文書生成の 10〜12 個の引数が、次の 5 層を個別の引数のまま通過する。

`api/summary.py:25-38` → `summary_service.py:61-74` → `_run_sync_generation` (214-226) → `api_factory.py:39-65` → `base_api.py:119-151` → `create_summary_prompt`

`api_factory.py:54-65` と `base_api.py:141-151` は 9〜10 個を位置引数で渡している。ほぼすべてが `str` なので、順序を間違えても型チェックで検出できない。フィールドを 1 つ追加するたびに 6 か所以上の修正が必要になる。

対応案: `SummaryRequest` (Pydantic) をそのままサービス層に渡し、サニタイズ後は `model_copy(update=...)` で差し替える。評価側も `EvaluationRequest` を渡す。

```python
# api/summary.py
return StreamingResponse(
    execute_summary_generation_stream(request, user_ip), ...
)
```

`stream_with_heartbeat` の `sync_func_args` タプル (`summary_service.py:355-367`) も、`functools.partial` かラムダ 1 つで済む。

## 4. [高] 使われていないストリーミング階層

`_run_sync_generation` (`summary_service.py:241-252`) は全チャンクを結合してから返すため、クライアントに届くのは `progress` と最終結果だけになる。チャンク単位の配信は行われていない。

そのため次のコードは実質的に意味を持たない。

- `BaseAPIClient._generate_content_stream` と `generate_summary_stream` (`base_api.py:162-216`)
- `GeminiAPIClient._generate_content_stream` (`gemini_api.py:104-126`)
- `generate_summary_stream_with_provider` (`api_factory.py:68-94`)
- `str | dict` を混在させて yield し `isinstance` で振り分ける処理 (`summary_service.py:243-247`)

対応案: ストリーミング系メソッドを削除し、`_run_sync_generation` から `client.generate_summary(...)` を呼ぶ。Gemini でストリーミング API を使う理由がある場合 (長時間応答のタイムアウト回避など) は、`gemini_api.py` にコメントで残す。

## 5. [中] `stream_with_heartbeat` の簡素化

`sse_helpers.py:35-96` は Queue、内部タスク、ループ後の `get_nowait` を組み合わせており、エラー送出のコードが 2 回出てくる (61-69, 85-93)。タスクを直接待てば Queue は不要になる。

```python
task = asyncio.create_task(asyncio.to_thread(sync_func, *sync_func_args))
while True:
    done, _ = await asyncio.wait({task}, timeout=heartbeat_interval)
    if done:
        break
    yield sse_event("progress", {...})
yield task.result()  # 例外は呼び出し側で捕捉し、監査ログとエラーイベントを出す
```

例外を呼び出し側に伝播させると、2 で挙げた監査ログの欠落も同時に解消できる。戻り値が「SSE 文字列または結果タプル」という混在型 (24 行目) である点も、呼び出し側の `isinstance(item, str)` 分岐の原因になっている。

あわせて、`logging.error(f"...")` (43 行目) はルートロガーを使っている。他のモジュールと同じく `logger = logging.getLogger(__name__)` に揃える (`usage_service.py:49,79` も同様)。

## 6. [中] 評価サービスの検証とモデル解決

`evaluation_service.py` に以下の回りくどさがある。

- `_resolve_evaluation_provider_and_model` は 3 要素タプル `(provider, model, error)` を返し、1 リクエストで 2 回呼ばれる (81 行目と 162 / 233 行目)。2 回目は `assert` を 3 つ並べて `None` を除外している (161-164, 234-235)。`model_selector.get_provider_and_model(settings.evaluation_model)` とほぼ同じ処理なので、そちらを再利用して `ValueError` を捕捉すれば関数ごと不要になる。
- 63 行目で `not output_summary` を早期リターンした直後に、67 行目で `if output_summary:` を再度判定している。
- `_validate_and_get_prompt` が検証、モデル設定確認、DB 取得の 3 つを担当している。
- `client._generate_content(...)` というプライベートメソッドを外部から呼んでいる (179, 239 行目)。`BaseAPIClient` に公開メソッド (`generate(system_prompt, user_prompt, model_name)` など) を用意する。
- `_run_sync_evaluation` の `document_type` 引数は使われていない (217 行目)。

`summary_service.validate_input` も同様に整理できる。

- 戻り値を `tuple[bool, str | None]` から `str | None` (エラーメッセージまたは `None`) に変える。`check_daily_limit` と同じ形になり、`error_msg or MESSAGES["ERROR"]["INPUT_ERROR"]` という補完 (107, 109, 302, 308 行目) が不要になる。
- 上限チェックが `summary_service.py:48` と `input_sanitizer.py:95` で二重になっている。
- `min_input_tokens` / `max_input_tokens` は文字数と比較されている (`len(medical_text)`)。設定名を `*_chars` にするか、コメントで明記する。

## 7. [中] API クライアントの初期化と例外処理

- `initialize()` は常に `True` を返し、戻り値はどこでも使われていない。リクエストごとに呼ばれるため、`__init__` でクライアントを生成すれば `initialize()` と `self.client is None` の検査 (`claude_api.py:51-52`, `gemini_api.py:72-73`) が両方不要になる。
- 例外が 3 重にラップされる。`_generate_content` の `except Exception` → `generate_summary` の `except Exception` → `summary_service` の `except Exception`。`claude_api.py:79` は自分で送出した `APIError` (未初期化) も再ラップする。最終的にユーザーには定型文しか返さないので、ラップは 1 か所で足りる。
- `base_api.py:155-156` の `except APIError as e: raise e` は `raise` でよい。
- `claude_api.py:63` は応答が空のときにエラーメッセージ文字列を「生成結果」として成功扱いで返す。利用量も保存される。`APIError` を送出するほうが呼び出し側の扱いが単純になる。
- `ClaudeAPIClient` の `aws_access_key_id` / `aws_secret_access_key` (`claude_api.py:18-19`) と `BaseAPIClient.api_key` (`base_api.py:32`) は参照されていない。
- `APIProvider` と `ModelType` の 2 つの Enum がある。`get_provider_and_model` は `APIProvider.X.value` (文字列) を返し、`create_client` がそれを Enum に戻している (`api_factory.py:21-25`)。`ModelType` から直接クライアントを選べば `APIProvider` と文字列変換は不要になる。
- `model_selector.py:20` の関数内 import は不要 (`prompt_service` は `models` にしか依存せず、循環しない)。
- `BaseAPIClient.get_model_name` は、呼び出し側が常に `model_name` を渡すため実行されない (`base_api.py:103-117,135-136`)。

## 8. [中] メッセージ定数

`python-coding.md` の「UI メッセージは `constants.py` で一元管理」に対して、以下のずれがある。

- **未使用のキー (削除候補)**: `CLOUDFLARE_GATEWAY_API_ERROR`, `CLOUDFLARE_GATEWAY_NOT_INITIALIZED`, `CLOUDFLARE_GATEWAY_SETTINGS_MISSING`, `CLIENT_CLOUDFLARE_GEMINI`, `API_CREDENTIALS_MISSING`, `AWS_CREDENTIALS_MISSING`, `CLAUDE_API_CREDENTIALS_MISSING`, `GOOGLE_LOCATION_MISSING`, `GOOGLE_PROJECT_ID_MISSING`, `NO_API_CREDENTIALS`, `NO_DATA_FOUND`。
- **重複**: `DAILY_*_LIMIT_EXCEEDED` の 3 件が `ERROR` と `CONFIG` の両方にある (`constants.py:85-87,121-123`)。使われているのは `ERROR` 側のみ。
- **定数化されていない文字列**: `input_sanitizer.py:96,100`、`security.py:67,74`、`base_api.py:159,215`、`api/prompts.py:29,70` (英語の `"Prompt not found"`)、`config.py:88`。
- **`FRONTEND_MESSAGES` の手書きコピー** (`constants.py:206-263`): キーを 1 つずつ書き写しており、追加漏れが起きやすい。公開するキー名のリストから内包表記で生成できる。
- **フロントエンドのフォールバック文字列**: `window.MESSAGES?.ERROR?.API_ERROR ?? 'API エラーが発生しました'` の形で、日本語リテラルが `app.ts` に 14 か所ある。`window.MESSAGES` は `base.html:61` で必ず設定されるので、`?.` と `??` を外して定数だけを参照する。
- **アクセス方法の混在**: `get_message("AUDIT", "X")` と `MESSAGES["AUDIT"]["X"]` が混在している。プレースホルダがない場合は添字、ある場合は `get_message` に統一する。
- `api_factory.py:35-36` は同じメッセージを 2 回 `format` している。また 27-36 行目は Enum の全値を列挙したあとの到達不能な分岐になっている。

## 9. [中] `parse_output_summary` の簡素化

`text_processor.py:32-83`。

- `SECTION_DETECTION_PATTERNS` の 2 番目と 3 番目は 1 番目に包含される (1 番目の接頭辞 `[【\[■●\s]*` は 0 回でも一致し、`(.*)` は空文字にも一致する)。1 本にできる。その結果 `if match.groups():` (62 行目) は常に真になる。
- パターンを行ごと、セクションごとに `format` して組み立てている。モジュール読み込み時に 1 度だけコンパイルすればよい。
- `found_section` / `detected_section` / `remaining_content` の 3 変数と二重 `break` は、`_match_section(line) -> tuple[str, str] | None` に切り出せば不要になる。
- 77 行目の `and line` は 42 行目で空行を除外済みのため冗長。83 行目の辞書内包表記は `sections` をそのまま返すのと同じ。
- `section_aliases` (5 行目) はモジュール定数なので `SECTION_ALIASES` とする。

挙動に関する補足: 現在のパターンは行頭がセクション名で始まれば一致するため、本文中の「現在の処方薬は〜」のような行も見出しとして検出される。意図した仕様か確認を勧める。

`input_sanitizer.py:42-45` は `text.lower()` と `re.IGNORECASE` を併用している。どちらか一方でよい。

## 10. [中] ORM の型付け

- `models/prompt.py` と `models/evaluation_prompt.py` は全カラムを `Any = Column(...)` と宣言している。その影響で `cast(str, prompt_data.content)` (`evaluation_service.py:91`)、`setattr(existing, 'content', content)` (`evaluation_prompt_service.py:34-35`)、`str(prompt.selected_model)` (`prompt_service.py:56`) といった回避コードが生じている。`models/usage.py` は `Any` なしで書かれており、モデル間でも不統一。SQLAlchemy 2.0 の `Mapped[str] = mapped_column(...)` に揃えれば、これらはすべて不要になる。
- `prompt_service.py` 内で `select()` (9 行目) と `db.query()` (28 行目以降) が混在している。どちらかに統一する。
- `api/evaluation.py:72-79,93-100` は `EvaluationPromptResponse` をフィールドごとに手で詰めている。`PromptResponse` と同じく `ConfigDict(from_attributes=True)` を付ければ ORM オブジェクトをそのまま返せる。
- `evaluation_prompt_service.py:11` の `is_active == True` は `.is_(True)` にする。

## 11. [低] 小さな重複と未使用コード

- `get_available_models` が `main.py:58-65` と `api/summary.py:70-81` の 2 か所にある。
- `StreamingResponse` のヘッダー dict が `api/summary.py:62-66` と `api/evaluation.py:58-62` で同一。
- `http_request.client.host if http_request.client else None` が API 層に 8 回ある。`Depends` で使える小さな関数にする。
- `statistics_service.py` は期間とモデルのフィルタを 3 関数で繰り返している (42-45, 84-89, 126-131)。`_apply_filters(query, ...)` に切り出す。
- `statistics_service.py:102-103` の三項演算子は、`"default"` と空値の両方を同じラベルにしているだけなので、`_label(value, default_label)` で 1 行にできる。
- `security.py` は HMAC 署名の計算が `generate_csrf_token` と `verify_csrf_token` で重複している。`_sign(timestamp)` にまとめれば `get_secret_key` も不要になる。
- `api/router.py` の `admin_router` と `protected_api_router` は依存関係が同一 (`require_csrf_token`)。区別する理由がなければ 1 つにし、各 API モジュールのルーターも 3 つから 2 つに減らす。コメントの「認証必須」は実態 (CSRF トークン検証) と合っていない。
- フロントエンドから呼ばれていない API: `/api/settings/departments`、`/api/settings/document-types`、`/api/summary/models`、`/api/statistics/summary`。外部利用がなければ削除候補。
- `frontend/package.json` の `aws4fetch` はソースから参照されていない。
- `app.ts:576-584` の `isActiveTab` は `getTabClass` からしか使われない 1 行関数。`app.ts:273-276` の `catch` はログを出して再送出するだけで、呼び出し元 (230-231 行目) でも同じログを出している。
- `usage_service.py:73` の `app_type="dischargesummary"` が直書きされている。紹介状アプリの値として正しいか確認のうえ、定数化を勧める。
- `settings = get_settings()` をモジュール先頭で取得する箇所と、関数内で `get_settings()` を呼ぶ箇所 (`usage_service.py:39`) が混在している。

## 12. [低] テンプレート内のインラインスクリプト

`prompts.html`、`prompts_new.html`、`prompts_edit.html`、`evaluation_prompts.html`、`evaluation_prompts_edit.html`、`statistics.html` に Alpine コンポーネントが `<script>` で直接書かれており、型チェックの対象外になっている。

- `prompts_new.html` の `savePrompt` と `prompts_edit.html` の `updatePrompt` は、遷移先とエラーメッセージ以外同一。
- 医師リストの取得処理が `app.ts:129-146`、`prompts_new.html:95-104`、`prompts.html` の 3 か所にある。
- CSRF ヘッダーの組み立ても各テンプレートで個別に書かれている (`app.ts` の `getHeaders` が使われていない)。
- これらのスクリプトは失敗時に `data.detail` を参照するが、`validation_exception_handler` が返すキーは `error_message`。422 のときはサーバーのメッセージが表示されず、常に定型文になる。

対応案: `frontend/src/` に `api.ts` (fetch ラッパーと `getHeaders`) を置き、各ページのコンポーネントを TypeScript に移す。1 と 2 を先に片付けてから着手するのがよい。

---

## 進め方

1. **1 (型エラー)** を先に直し、ビルドに型チェックを組み込む。影響範囲が小さく、以降のリファクタリングの安全網になる。
2. **2 の方針**  非ストリーミング経路を廃止する
3. **3 → 4 → 5** をまとめて実施する。同じ呼び出し経路を触るため、1 回のリファクタリングで済ませるほうが差分が小さい。
4. 6 以降は独立しているので、個別に対応できる。
