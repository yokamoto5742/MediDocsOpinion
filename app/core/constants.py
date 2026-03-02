from enum import Enum


class ModelType(str, Enum):
    CLAUDE = "Claude"
    GEMINI_PRO = "Gemini_Pro"

# プロンプト管理
DEFAULT_DEPARTMENT = ["default", "眼科"]
DEFAULT_DOCTOR = ["default"]
DEPARTMENT_DOCTORS_MAPPING = {
    "default": ["default"],
    "眼科": ["default", "橋本義弘"],
}
DOCUMENT_TYPES = ["他院への紹介", "紹介元への逆紹介", "返書", "最終返書"]

# 統計情報
DEFAULT_STATISTICS_PERIOD_DAYS = 7

# 出力結果
DEFAULT_SECTION_NAMES = [
    "現在の処方",
    "備考",
]

# app/external/api_factory.py 他
DEFAULT_DOCUMENT_TYPE = "他院への紹介"
# app/external/base_api.py
DEFAULT_SUMMARY_PROMPT = """
以下のカルテ情報を要約してください。これまでの治療内容を記載してください。
"""
# app/utils/text_processor.py
# 【治療経過】: 内容 など(改行含む)
# 治療経過: 内容 など(改行含む)
# 治療経過（行全体がセクション名のみ）
SECTION_DETECTION_PATTERNS = [
    r'^[【\[■●\s]*{section}[】\]\s]*[:：]?\s*(.*)$',
    r'^{section}\s*[:：]?\s*(.*)$',
    r'^{section}\s*$',
]

# 診療情報提供者アプリ固有の設定
DOCUMENT_TYPE_TO_PURPOSE_MAPPING = {
    "他院への紹介": "精査加療依頼",
    "紹介元への逆紹介": "継続治療依頼",
    "返書": "受診報告",
    "最終返書": "治療経過報告",
}

MESSAGES: dict[str, dict[str, str]] = {
    "ERROR": {
        "API_ERROR": "API エラーが発生しました",
        "BEDROCK_API_ERROR": "Amazon Bedrock Claude API呼び出しエラー: {error}",
        "BEDROCK_INIT_ERROR": "Amazon Bedrock Claude API初期化エラー: {error}",
        "CLAUDE_CLIENT_NOT_INITIALIZED": "Claude API クライアントが初期化されていません",
        "CLOUDFLARE_GATEWAY_API_ERROR": "Cloudflare AI Gateway経由のAPI呼び出しエラー: {error}",
        "CLOUDFLARE_GATEWAY_NOT_INITIALIZED": "Cloudflare Gateway が初期化されていません",
        "COPY_FAILED": "テキストのコピーに失敗しました",
        "EMPTY_RESPONSE": "レスポンスが空です",
        "EVALUATION_API_ERROR": "評価中にエラーが発生しました: {error}",
        "EVALUATION_ERROR": "評価中にエラーが発生しました",
        "EVALUATION_PROMPT_DELETE_FAILED": "評価プロンプトの削除に失敗しました",
        "EVALUATION_PROMPT_LOAD_FAILED": "評価プロンプトの読み込みに失敗しました",
        "EVALUATION_PROMPT_NOT_FOUND": "{document_type}の評価プロンプトが見つかりません",
        "EVALUATION_PROMPT_SAVE_FAILED": "評価プロンプトの保存に失敗しました",
        "GEMINI_CLIENT_NOT_INITIALIZED": "Gemini API クライアントが初期化されていません",
        "GENERIC_ERROR": "エラーが発生しました",
        "INPUT_ERROR": "入力エラーが発生しました",
        "MODEL_NAME_NOT_SPECIFIED": "モデル名が指定されていません",
        "PROMPT_CREATE_FAILED": "プロンプトの作成に失敗しました",
        "PROMPT_DELETE_FAILED": "プロンプトの削除に失敗しました",
        "PROMPT_LOAD_FAILED": "プロンプトの読み込みに失敗しました",
        "PROMPT_NOT_FOUND": "プロンプトが見つかりません",
        "PROMPT_UPDATE_FAILED": "プロンプトの更新に失敗しました",
        "RESPONSE_BODY_EMPTY": "レスポンスボディが空です",
        "STATISTICS_AGGREGATED_LOAD_FAILED": "集計データの読み込みに失敗しました",
        "STATISTICS_RECORDS_LOAD_FAILED": "使用履歴の読み込みに失敗しました",
        "UNSUPPORTED_API_PROVIDER": "未対応のAPIプロバイダー: {provider}",
        "USAGE_SAVE_FAILED": "使用統計の保存に失敗しました: {error}",
        "VERTEX_AI_API_ERROR": "Vertex AI API呼び出しエラー: {error}",
        "VERTEX_AI_CREDENTIALS_ERROR": "認証情報の処理中にエラーが発生しました: {error}",
        "VERTEX_AI_CREDENTIALS_FIELD_MISSING": "認証情報に必要なフィールドがありません: {error}",
        "VERTEX_AI_CREDENTIALS_JSON_PARSE_ERROR": "認証情報JSONのパースに失敗しました: {error}",
        "VERTEX_AI_INIT_ERROR": "Vertex AI初期化エラー: {error}",
    },
    "CONFIG": {
        "ANTHROPIC_MODEL_MISSING": "ANTHROPIC_MODELが設定されていません。環境変数を確認してください。",
        "API_CREDENTIALS_MISSING": "Gemini APIの認証情報が設定されていません。環境変数を確認してください。",
        "AWS_CREDENTIALS_MISSING": "AWS認証情報が設定されていません。環境変数を確認してください。",
        "CLAUDE_API_CREDENTIALS_MISSING": "Claude APIの認証情報が設定されていません。環境変数を確認してください。",
        "CLAUDE_MODEL_NOT_SET": "Claudeモデルが設定されていません",
        "CLOUDFLARE_GATEWAY_SETTINGS_MISSING": "Cloudflare AI Gatewayの設定が不完全です。環境変数を確認してください",
        "EVALUATION_MODEL_MISSING": "GEMINI_EVALUATION_MODEL環境変数が設定されていません",
        "GEMINI_MODEL_NOT_SET": "Geminiモデルが設定されていません",
        "GOOGLE_LOCATION_MISSING": "GOOGLE_LOCATION環境変数が設定されていません。",
        "GOOGLE_PROJECT_ID_MISSING": "GOOGLE_PROJECT_ID環境変数が設定されていません。",
        "NO_API_CREDENTIALS": "使用可能なAI APIの認証情報が設定されていません。環境変数を確認してください。",
        "THRESHOLD_EXCEEDED_NO_GEMINI": "入力が長すぎますが、Geminiモデルが設定されていません",
        "UNSUPPORTED_MODEL": "サポートされていないモデル: {model}",
        "VERTEX_AI_PROJECT_MISSING": "GOOGLE_PROJECT_ID環境変数が設定されていません",
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
        "NO_DATA_FOUND": "指定期間のデータがありません",
    },
    "CONFIRM": {
        "DELETE_EVALUATION_PROMPT": "「{document_type}」の評価プロンプトを削除してもよろしいですか？",
        "DELETE_PROMPT": "このプロンプトを削除してもよろしいですか？",
        "RE_EVALUATE": "前回の評価をクリアして再評価しますか？",
    },
    "LOG": {
        "CLIENT_CLOUDFLARE_GEMINI": "APIクライアント選択: CloudflareGeminiAPIClient",
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


FRONTEND_MESSAGES: dict[str, dict[str, str]] = {
    "ERROR": {
        "API_ERROR": MESSAGES["ERROR"]["API_ERROR"],
        "COPY_FAILED": MESSAGES["ERROR"]["COPY_FAILED"],
        "EVALUATION_ERROR": MESSAGES["ERROR"]["EVALUATION_ERROR"],
        "EVALUATION_PROMPT_DELETE_FAILED": MESSAGES["ERROR"]["EVALUATION_PROMPT_DELETE_FAILED"],
        "EVALUATION_PROMPT_LOAD_FAILED": MESSAGES["ERROR"]["EVALUATION_PROMPT_LOAD_FAILED"],
        "EVALUATION_PROMPT_SAVE_FAILED": MESSAGES["ERROR"]["EVALUATION_PROMPT_SAVE_FAILED"],
        "GENERIC_ERROR": MESSAGES["ERROR"]["GENERIC_ERROR"],
        "PROMPT_CREATE_FAILED": MESSAGES["ERROR"]["PROMPT_CREATE_FAILED"],
        "PROMPT_DELETE_FAILED": MESSAGES["ERROR"]["PROMPT_DELETE_FAILED"],
        "PROMPT_LOAD_FAILED": MESSAGES["ERROR"]["PROMPT_LOAD_FAILED"],
        "PROMPT_NOT_FOUND": MESSAGES["ERROR"]["PROMPT_NOT_FOUND"],
        "PROMPT_UPDATE_FAILED": MESSAGES["ERROR"]["PROMPT_UPDATE_FAILED"],
        "RESPONSE_BODY_EMPTY": MESSAGES["ERROR"]["RESPONSE_BODY_EMPTY"],
        "STATISTICS_AGGREGATED_LOAD_FAILED": MESSAGES["ERROR"]["STATISTICS_AGGREGATED_LOAD_FAILED"],
        "STATISTICS_RECORDS_LOAD_FAILED": MESSAGES["ERROR"]["STATISTICS_RECORDS_LOAD_FAILED"],
    },
    "VALIDATION": {
        "ALL_REQUIRED_FIELDS": MESSAGES["VALIDATION"]["ALL_REQUIRED_FIELDS"],
        "EVALUATION_NO_OUTPUT": MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"],
        "FIELD_REQUIRED": MESSAGES["VALIDATION"]["FIELD_REQUIRED"],
        "NO_INPUT": MESSAGES["VALIDATION"]["NO_INPUT"],
        "NO_PERSONAL_INFO": MESSAGES["VALIDATION"]["NO_PERSONAL_INFO"],
        "PROMPT_CONTENT_REQUIRED": MESSAGES["VALIDATION"]["PROMPT_CONTENT_REQUIRED"],
    },
    "SUCCESS": {
        "COPIED_TO_CLIPBOARD": MESSAGES["SUCCESS"]["COPIED_TO_CLIPBOARD"],
        "EVALUATION_PROMPT_CREATED": MESSAGES["SUCCESS"]["EVALUATION_PROMPT_CREATED"],
        "EVALUATION_PROMPT_DELETED": MESSAGES["SUCCESS"]["EVALUATION_PROMPT_DELETED"],
        "EVALUATION_PROMPT_UPDATED": MESSAGES["SUCCESS"]["EVALUATION_PROMPT_UPDATED"],
        "PROMPT_CREATED": MESSAGES["SUCCESS"]["PROMPT_CREATED"],
        "PROMPT_DELETED": MESSAGES["SUCCESS"]["PROMPT_DELETED"],
        "PROMPT_SAVED": MESSAGES["SUCCESS"]["PROMPT_SAVED"],
        "PROMPT_UPDATED": MESSAGES["SUCCESS"]["PROMPT_UPDATED"],
    },
    "INFO": {
        "AI_DISCLAIMER_EVALUATION": MESSAGES["INFO"]["AI_DISCLAIMER_EVALUATION"],
        "AI_DISCLAIMER_OUTPUT": MESSAGES["INFO"]["AI_DISCLAIMER_OUTPUT"],
        "DEFAULT_DEPARTMENT_LABEL": MESSAGES["INFO"]["DEFAULT_DEPARTMENT_LABEL"],
        "DEFAULT_DOCTOR_LABEL": MESSAGES["INFO"]["DEFAULT_DOCTOR_LABEL"],
    },
    "CONFIRM": {
        "DELETE_EVALUATION_PROMPT": MESSAGES["CONFIRM"]["DELETE_EVALUATION_PROMPT"],
        "DELETE_PROMPT": MESSAGES["CONFIRM"]["DELETE_PROMPT"],
        "RE_EVALUATE": MESSAGES["CONFIRM"]["RE_EVALUATE"],
    },
}
