import re

from app.core.constants import DEFAULT_SECTION_NAMES, SECTION_DETECTION_PATTERN

# AIが別名で出力した見出しを正規のセクション名に読み替える
SECTION_ALIASES = {
    "その他": "備考",
    "補足": "備考",
    "メモ": "備考"
}

# セクション見出しの検出パターン（グループ1: セクション名または別名、グループ2: 同じ行の内容）
_SECTION_PATTERN = re.compile(
    SECTION_DETECTION_PATTERN.format(
        sections="|".join(
            re.escape(name) for name in [*DEFAULT_SECTION_NAMES, *SECTION_ALIASES]
        )
    )
)


def format_output_summary(summary_text: str) -> str:
    """AI出力のフォーマットを整形"""
    processed_text = (
        summary_text.replace('*', '')
        .replace('＊', '')
        .replace('#', '')
    )

    # 全角文字に隣接する半角スペースのみ削除（英数字間のスペースは保持）
    processed_text = re.sub(r'(?<=[^\x00-\x7F]) +', '', processed_text)
    processed_text = re.sub(r' +(?=[^\x00-\x7F])', '', processed_text)
    # 行末の余分なスペースを削除
    processed_text = re.sub(r' +$', '', processed_text, flags=re.MULTILINE)

    return processed_text


def _match_section(line: str) -> tuple[str, str] | None:
    """行がセクション見出しなら (セクション名, 同じ行の内容) を返す"""
    match = _SECTION_PATTERN.match(line)
    if not match:
        return None
    name = match.group(1)
    return SECTION_ALIASES.get(name, name), match.group(2).strip()


def parse_output_summary(summary_text: str) -> dict[str, str]:
    """AI出力をセクションごとに分割してパース"""
    sections = {section: "" for section in DEFAULT_SECTION_NAMES}
    current_section = None

    for line in summary_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        matched = _match_section(line)
        if matched:
            current_section, content = matched
            # 見出しと同じ行に内容がある場合は、そのセクションの内容を置き換える
            if content:
                sections[current_section] = content
        elif current_section:
            # 最初の見出しより前の行はどのセクションにも属さないため捨てる
            if sections[current_section]:
                sections[current_section] += "\n" + line
            else:
                sections[current_section] = line

    return sections
