import re
from typing import Tuple


# プロンプトインジェクション攻撃のパターン
PROMPT_INJECTION_PATTERNS = [
    # システムプロンプト上書き指示（英語）
    r'ignore\s+(previous|all|above|earlier)\s+(instruction|command|prompt|rule)',
    r'disregard\s+(previous|all|above|earlier)\s+(instruction|command|prompt|rule)',
    r'forget\s+(previous|all|above|earlier)\s+(instruction|command|prompt|rule)',

    # システムプロンプト上書き指示（日本語）
    r'(以前|これまで|上記|全て)の(指示|命令|プロンプト|ルール)を(無視|忘れ|破棄)',
    r'新しい(指示|命令|プロンプト|ルール)に従[いっ]?て',

    # ロールプレイング攻撃
    r'you\s+are\s+now\s+',
    r'act\s+as\s+(a|an)\s+',
    r'pretend\s+(to\s+be|you\s+are)',
    r'(あなた|君)は(今から|これから).*として(振る舞|行動)',

    # システムへの直接命令
    r'(tell|show|give|provide)\s+me\s+(the|your)\s+(system|instruction|prompt)',
    r'reveal\s+(your|the)\s+(system|instruction|prompt)',
    r'(システム|指示|プロンプト)を(教え|見せ|表示)',

    # プロンプト境界の混乱
    r'<\|im_(start|end)\|>',
    r'\[INST\]|\[/INST\]',
    r'<system>|</system>',
    r'### (System|User|Assistant):',
]


def detect_prompt_injection(text: str) -> Tuple[bool, list[str]]:
    """
    プロンプトインジェクション攻撃の疑いがあるパターンを検出

    Returns:
        (is_suspicious, matched_patterns): 疑わしい場合True、検出されたパターンのリスト
    """
    if not text:
        return False, []

    matched_patterns = []
    text_lower = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE):
            matched_patterns.append(pattern)

    # 異常な繰り返しパターンの検出（同じ文字列が10回以上連続）
    repeated_pattern = re.search(r'(.{20,}?)\1{9,}', text)
    if repeated_pattern:
        matched_patterns.append("repeated_pattern_detected")

    # 異常な長さの検出（100KB以上）
    if len(text) > 100000:
        matched_patterns.append("excessive_length")

    return len(matched_patterns) > 0, matched_patterns


def sanitize_medical_text(text: str) -> str:
    """
    医療テキストのサニタイゼーション

    XSS対策とプロンプトインジェクション軽減のため入力を整形
    医療情報の可読性を保ちつつ危険なパターンを除去
    """
    if not text:
        return text

    # スクリプトタグの完全除去
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # イベントハンドラ属性の除去
    text = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

    # 制御文字の除去（改行とタブは保持）
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    return text


def sanitize_prompt_text(text: str) -> str:
    """プロンプトテキストの基本的なサニタイゼーション"""
    if not text:
        return text

    return sanitize_medical_text(text)


def validate_medical_input(text: str, max_length: int = 100000) -> Tuple[bool, str | None]:
    """
    医療テキスト入力の検証

    プロンプトインジェクション攻撃や異常な入力を検出

    Returns:
        (is_valid, error_message): 有効な場合True、エラーメッセージ
    """
    if not text:
        return False, "入力テキストが空です"

    if len(text) > max_length:
        return False, f"入力テキストが長すぎます（最大{max_length}文字）"

    is_suspicious, _ = detect_prompt_injection(text)
    if is_suspicious:
        return False, "入力テキストに不正なパターンが検出されました"

    return True, None
