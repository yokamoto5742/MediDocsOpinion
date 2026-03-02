import re

from app.core.constants import DEFAULT_SECTION_NAMES, SECTION_DETECTION_PATTERNS

section_aliases = {
    "その他": "備考",
    "補足": "備考",
    "メモ": "備考"
}


def format_output_summary(summary_text: str) -> str:
    """AI出力のフォーマットを整形"""
    processed_text = (
        summary_text.replace('*', '')
        .replace('＊', '')
        .replace('#', '')
        .replace(' ', '')
    )

    return processed_text


def parse_output_summary(summary_text: str) -> dict[str, str]:
    """AI出力をセクションごとに分割してパース"""
    sections = {section: "" for section in DEFAULT_SECTION_NAMES}
    lines = summary_text.split('\n')
    current_section = None

    all_section_names = list(sections.keys()) + list(section_aliases.keys())

    for line in lines:
        line = line.strip()
        if not line:
            continue

        found_section = False
        detected_section = None
        remaining_content = ""

        for section in all_section_names:
            patterns = [
                pattern.format(section=re.escape(section)) for pattern in SECTION_DETECTION_PATTERNS
            ]

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    if section in section_aliases:
                        detected_section = section_aliases[section]
                    else:
                        detected_section = section

                    if match.groups():
                        remaining_content = match.group(1).strip()
                    else:
                        remaining_content = ""

                    found_section = True
                    break

            if found_section:
                break

        if found_section:
            current_section = detected_section
            if remaining_content and current_section:
                sections[current_section] = remaining_content
        elif current_section and line:
            if sections[current_section]:
                sections[current_section] += "\n" + line
            else:
                sections[current_section] = line

    return {k: sections.get(k, "") for k in DEFAULT_SECTION_NAMES}
