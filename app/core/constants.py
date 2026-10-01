from enum import Enum


class ModelType(str, Enum):
    CLAUDE = "Claude"
    GEMINI = "Gemini"


# プロンプト管理
DEFAULT_DEPARTMENT = ["default"]
DEPARTMENT_DOCTORS_MAPPING = {
    "default": ["default"],
}
DOCUMENT_TYPES = ["主治医意見書", "訪問看護指示書"]

# 統計情報
DEFAULT_STATISTICS_PERIOD_DAYS = 7

# 出力結果
DEFAULT_SECTION_NAMES = ["治療経過", "特記事項", "備考"]

# app/external/api_factory.py 他
DEFAULT_DOCUMENT_TYPE = "主治医意見書"
# app/external/base_api.py
DEFAULT_SUMMARY_PROMPT = """
以下のカルテ情報を要約してください。これまでの治療内容を記載してください。
"""

# app/external/claude_api.py
# 医療文書のため事実性・再現性を優先した低めの温度
CLAUDE_GENERATION_TEMPERATURE = 0.2

# app/external/base_api.py
GROUNDING_INSTRUCTION = """## 厳守事項
- カルテ情報に記載のない情報を追加しないでください
- カルテの記載日時に沿って時系列で整理してください"""

KARTE_JSON_INSTRUCTION = """## カルテ情報の形式
- カルテ情報はJSON形式で提供されます
- 日時フィールドをもとに時系列を把握してください
- JSONのキー名をそのまま文書に転記しないでください"""

REFINEMENT_INSTRUCTION = """## 修正指示
<前回の生成結果>と<評価結果>が与えられます。評価結果の指摘を反映して、前回の生成結果を修正した文書を出力してください。指摘のない箇所は変更しないでください。"""

# app/services/evaluation_service.py
EVALUATION_GROUNDING_INSTRUCTION = """## 評価の厳守事項
- 各指摘には、根拠となるカルテの該当箇所を引用してください
- カルテに根拠のない記述があれば、ハルシネーションの可能性として必ず指摘してください"""
# app/utils/text_processor.py
# 行頭のセクション名を検出する。{sections} にはセクション名の選択肢が入る
# 括弧・コロン・後続の内容はすべて省略可能なため、次のいずれにも一致する
# 【治療経過】: 内容
# 治療経過: 内容
# 治療経過（行全体がセクション名のみ）
SECTION_DETECTION_PATTERN = r"^[【\[■●\s]*({sections})[】\]\s]*[:：]?\s*(.*)$"

# app/services/usage_service.py
# 使用統計に記録するアプリ種別
USAGE_APP_TYPE = "dischargesummary"

MESSAGES: dict[str, dict[str, str]] = {
    "ERROR": {
        "API_ERROR": "API エラーが発生しました",
        "COPY_FAILED": "テキストのコピーに失敗しました",
        "CSRF_TOKEN_INVALID": "無効または期限切れのCSRFトークンです",
        "CSRF_TOKEN_REQUIRED": "CSRFトークンが必要です",
        "DAILY_INPUT_TOKEN_LIMIT_EXCEEDED": "本日の入力トークン制限（{limit}トークン）を超過しました。明日再度お試しください",
        "DAILY_OUTPUT_TOKEN_LIMIT_EXCEEDED": "本日の出力トークン制限（{limit}トークン）を超過しました。明日再度お試しください",
        "DAILY_REQUEST_LIMIT_EXCEEDED": "本日のリクエスト回数制限（{limit}回）を超過しました。明日再度お試しください",
        "EMPTY_RESPONSE": "レスポンスが空です",
        "EVALUATION_ERROR": "評価中にエラーが発生しました",
        "EVALUATION_PROMPT_DELETE_FAILED": "評価プロンプトの削除に失敗しました",
        "EVALUATION_PROMPT_LOAD_FAILED": "評価プロンプトの読み込みに失敗しました",
        "EVALUATION_PROMPT_NOT_FOUND": "{document_type}の評価プロンプトが見つかりません",
        "EVALUATION_PROMPT_SAVE_FAILED": "評価プロンプトの保存に失敗しました",
        "GEMINI_UNEXPECTED_RESPONSE": "Gemini API から想定外のレスポンスが返されました",
        "GENERIC_ERROR": "エラーが発生しました",
        "INPUT_ERROR": "入力エラーが発生しました",
        "PROMPT_CREATE_FAILED": "プロンプトの作成に失敗しました",
        "PROMPT_DELETE_FAILED": "プロンプトの削除に失敗しました",
        "PROMPT_LOAD_FAILED": "プロンプトの読み込みに失敗しました",
        "PROMPT_NOT_FOUND": "プロンプトが見つかりません",
        "PROMPT_UPDATE_FAILED": "プロンプトの更新に失敗しました",
        "RESPONSE_BODY_EMPTY": "レスポンスボディが空です",
        "STATISTICS_AGGREGATED_LOAD_FAILED": "集計データの読み込みに失敗しました",
        "STATISTICS_RECORDS_LOAD_FAILED": "使用履歴の読み込みに失敗しました",
        "USAGE_SAVE_FAILED": "使用統計の保存に失敗しました: {error}",
    },
    "CONFIG": {
        "ANTHROPIC_MODEL_MISSING": "ANTHROPIC_MODELが設定されていません。環境変数を確認してください。",
        "CLAUDE_MODEL_NOT_SET": "Claudeモデルが設定されていません",
        "CSRF_SECRET_KEY_MISSING": "CSRF_SECRET_KEY環境変数が設定されていません。アプリケーションを起動できません。",
        "EVALUATION_MODEL_MISSING": "EVALUATION_MODEL環境変数が設定されていません",
        "GEMINI_MODEL_NOT_SET": "Geminiモデルが設定されていません",
        "THRESHOLD_EXCEEDED_NO_GEMINI": "入力が長すぎますが、Geminiモデルが設定されていません",
        "UNSUPPORTED_MODEL": "サポートされていないモデル: {model}",
        "VERTEX_AI_PROJECT_MISSING": "GOOGLE_PROJECT_ID環境変数が設定されていません",
    },
    "WARNING": {
        "OUTPUT_TRUNCATED": "※出力が上限に達したため、文書が途中で切れている可能性があります",
    },
    "VALIDATION": {
        "ALL_REQUIRED_FIELDS": "すべての必須項目を入力してください",
        "EVALUATION_NO_OUTPUT": "評価対象の出力がありません",
        "EVALUATION_PROMPT_CONTENT_REQUIRED": "評価プロンプトの内容を入力してください",
        "EVALUATION_PROMPT_NOT_SET": "{document_type}の評価プロンプトが設定されていません",
        "FIELD_REQUIRED": "すべての項目を入力してください",
        "INPUT_TOO_LONG": "入力テキストが長すぎます",
        "INPUT_TOO_SHORT": "入力文字数が少なすぎます",
        "NO_INPUT": "カルテ情報を入力してください",
        "NO_PERSONAL_INFO": "患者ID・氏名・住所などの個人情報は入力しないでください",
        "PROMPT_CONTENT_REQUIRED": "プロンプト内容を入力してください",
        "SUSPICIOUS_INPUT": "入力テキストに不正なパターンが検出されました",
    },
    "SUCCESS": {
        "COPIED_TO_CLIPBOARD": "クリップボードにコピーしました",
        "EVALUATION_PROMPT_CREATED": "評価プロンプトを新規作成しました",
        "EVALUATION_PROMPT_DELETED": "評価プロンプトを削除しました",
        "EVALUATION_PROMPT_UPDATED": "評価プロンプトを更新しました",
        "PROMPT_CREATED": "プロンプトを新規作成しました",
        "PROMPT_DELETED": "プロンプトを削除しました",
        "PROMPT_SAVED": "プロンプトを保存しました",
        "PROMPT_UPDATED": "プロンプトを更新しました",
    },
    "STATUS": {
        "DOCUMENT_GENERATING": "文書を生成中...",
        "DOCUMENT_GENERATING_ELAPSED": "文書を生成中... ({elapsed}秒経過)",
        "DOCUMENT_GENERATION_START": "文書生成を開始します...",
        "EVALUATING": "評価中...",
        "EVALUATING_ELAPSED": "評価中... ({elapsed}秒経過)",
        "EVALUATION_START": "評価を開始します...",
    },
    "INFO": {
        "AI_DISCLAIMER_EVALUATION": "AIは間違えることがあります。内容はカルテでご確認ください。",
        "AI_DISCLAIMER_OUTPUT": "AIは間違えることがあります。内容はカルテでご確認ください。",
        "DEFAULT_DEPARTMENT_LABEL": "全科共通",
        "DEFAULT_DOCTOR_LABEL": "医師共通",
    },
    "CONFIRM": {
        "DELETE_EVALUATION_PROMPT": "「{document_type}」の評価プロンプトを削除してもよろしいですか？",
        "DELETE_PROMPT": "このプロンプトを削除してもよろしいですか？",
        "RE_EVALUATE": "前回の評価をクリアして再評価しますか？",
    },
    "LOG": {
        "CLIENT_DIRECT_CLAUDE": "APIクライアント選択: ClaudeAPIClient (Direct Amazon Bedrock)",
        "CLIENT_DIRECT_GEMINI": "APIクライアント選択: GeminiAPIClient (Direct Vertex AI)",
    },
    "AUDIT": {
        "DOCUMENT_GENERATION_FAILURE": "文書生成失敗",
        "DOCUMENT_GENERATION_START": "文書生成開始",
        "DOCUMENT_GENERATION_SUCCESS": "文書生成完了",
        "EVALUATION_FAILURE": "評価失敗",
        "EVALUATION_PROMPT_DELETED": "評価プロンプト削除",
        "EVALUATION_PROMPT_SAVED": "評価プロンプト保存",
        "EVALUATION_START": "評価開始",
        "EVALUATION_SUCCESS": "評価完了",
        "PROMPT_CREATED": "プロンプト作成",
        "PROMPT_DELETED": "プロンプト削除",
        "PROMPT_UPDATED": "プロンプト更新",
    },
}


def get_message(category: str, key: str, **kwargs: str) -> str:
    """カテゴリとキーからメッセージを取得しプレースホルダーを置換"""
    msg = MESSAGES[category][key]
    if kwargs:
        return msg.format(**kwargs)
    return msg


# フロントエンドに公開するメッセージのキー（カテゴリごと）
# テンプレートと TypeScript から参照するものだけを列挙する
FRONTEND_MESSAGE_KEYS: dict[str, list[str]] = {
    "ERROR": [
        "API_ERROR",
        "COPY_FAILED",
        "EVALUATION_PROMPT_DELETE_FAILED",
        "EVALUATION_PROMPT_LOAD_FAILED",
        "EVALUATION_PROMPT_SAVE_FAILED",
        "GENERIC_ERROR",
        "PROMPT_CREATE_FAILED",
        "PROMPT_DELETE_FAILED",
        "PROMPT_LOAD_FAILED",
        "PROMPT_NOT_FOUND",
        "PROMPT_UPDATE_FAILED",
        "RESPONSE_BODY_EMPTY",
        "STATISTICS_AGGREGATED_LOAD_FAILED",
        "STATISTICS_RECORDS_LOAD_FAILED",
    ],
    "VALIDATION": [
        "ALL_REQUIRED_FIELDS",
        "EVALUATION_NO_OUTPUT",
        "FIELD_REQUIRED",
        "NO_INPUT",
        "NO_PERSONAL_INFO",
        "PROMPT_CONTENT_REQUIRED",
    ],
    "SUCCESS": [
        "COPIED_TO_CLIPBOARD",
        "EVALUATION_PROMPT_CREATED",
        "EVALUATION_PROMPT_DELETED",
        "EVALUATION_PROMPT_UPDATED",
        "PROMPT_CREATED",
        "PROMPT_DELETED",
        "PROMPT_SAVED",
        "PROMPT_UPDATED",
    ],
    "INFO": [
        "AI_DISCLAIMER_EVALUATION",
        "AI_DISCLAIMER_OUTPUT",
        "DEFAULT_DEPARTMENT_LABEL",
        "DEFAULT_DOCTOR_LABEL",
    ],
    "CONFIRM": [
        "DELETE_EVALUATION_PROMPT",
        "DELETE_PROMPT",
        "RE_EVALUATE",
    ],
}

FRONTEND_MESSAGES: dict[str, dict[str, str]] = {
    category: {key: MESSAGES[category][key] for key in keys}
    for category, keys in FRONTEND_MESSAGE_KEYS.items()
}
