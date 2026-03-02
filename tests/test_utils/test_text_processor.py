from app.utils.text_processor import format_output_summary, parse_output_summary


class TestFormatOutputSummary:
    """format_output_summary 関数のテスト"""

    def test_format_remove_asterisk(self):
        """フォーマット - '*' 削除"""
        input_text = "*現在の処方*: アムロジピン"
        result = format_output_summary(input_text)
        assert result == "現在の処方:アムロジピン"

    def test_format_remove_fullwidth_asterisk(self):
        """フォーマット - '＊' 削除"""
        input_text = "＊備考＊：特記事項なし"
        result = format_output_summary(input_text)
        assert result == "備考：特記事項なし"

    def test_format_remove_hash(self):
        """フォーマット - '#' 削除"""
        input_text = "# 現在の処方: アムロジピン"
        result = format_output_summary(input_text)
        assert result == "現在の処方:アムロジピン"

    def test_format_remove_halfwidth_space(self):
        """フォーマット - 半角スペース削除"""
        input_text = "備考 : 定期フォローアップ必要"
        result = format_output_summary(input_text)
        assert result == "備考:定期フォローアップ必要"

    def test_format_remove_all_special_characters(self):
        """フォーマット - 複合パターン"""
        input_text = "# *現在の処方* : アムロジピン"
        result = format_output_summary(input_text)
        assert result == "現在の処方:アムロジピン"

    def test_format_empty_string(self):
        """フォーマット - 空文字列"""
        input_text = ""
        result = format_output_summary(input_text)
        assert result == ""

    def test_format_special_characters_only(self):
        """フォーマット - 特殊文字のみ"""
        input_text = "# * ＊  "
        result = format_output_summary(input_text)
        assert result == ""

    def test_format_preserve_newlines(self):
        """フォーマット - 改行は保持"""
        input_text = "現在の処方: アムロジピン\n備考: なし"
        result = format_output_summary(input_text)
        assert result == "現在の処方:アムロジピン\n備考:なし"

    def test_format_preserve_fullwidth_characters(self):
        """フォーマット - 全角文字は保持"""
        input_text = "備考：特記事項なし"
        result = format_output_summary(input_text)
        assert result == "備考：特記事項なし"

    def test_format_multiple_special_characters(self):
        """フォーマット - 複数の特殊文字"""
        input_text = "** # 現在の処方 ** : アムロジピン"
        result = format_output_summary(input_text)
        assert result == "現在の処方:アムロジピン"


class TestParseOutputSummary:
    """parse_output_summary 関数のテスト"""

    def test_parse_with_colon(self):
        """パース - コロンあり形式"""
        input_text = "現在の処方: アムロジピン5mg"
        result = parse_output_summary(input_text)

        assert result["現在の処方"] == "アムロジピン5mg"
        assert result["備考"] == ""

    def test_parse_with_fullwidth_colon(self):
        """パース - 全角コロン形式"""
        input_text = "備考：特記事項なし"
        result = parse_output_summary(input_text)

        assert result["備考"] == "特記事項なし"
        assert result["現在の処方"] == ""

    def test_parse_without_colon(self):
        """パース - コロンなし形式"""
        input_text = "備考 特記事項なし"
        result = parse_output_summary(input_text)

        assert result["備考"] == "特記事項なし"

    def test_parse_alias_conversion(self):
        """パース - エイリアス変換（治療内容 → 治療経過、備考に含まれない）"""
        input_text = "治療内容: インスリン療法"
        result = parse_output_summary(input_text)

        # 治療内容は未定義のセクション（DEFAULT_SECTION_NAMESにない）
        # section_aliasesで治療経過にマッピングされるが、
        # 治療経過もDEFAULT_SECTION_NAMESにないため、結果は空
        assert result["現在の処方"] == ""
        assert result["備考"] == ""

    def test_parse_alias_conversion_others(self):
        """パース - その他エイリアス変換（その他 → 備考）"""
        input_text = "その他: 特記事項なし"
        result = parse_output_summary(input_text)

        # "その他" は "備考" にマッピングされる
        assert result["備考"] == "特記事項なし"

    def test_parse_multiline_section_content(self):
        """パース - 複数行のセクション内容"""
        input_text = """現在の処方: アムロジピン5mg
ロサルタン50mg
アスピリン100mg"""
        result = parse_output_summary(input_text)

        expected = "アムロジピン5mg\nロサルタン50mg\nアスピリン100mg"
        assert result["現在の処方"] == expected

    def test_parse_all_sections(self):
        """パース - 全セクション抽出"""
        input_text = """現在の処方: アムロジピン5mg
備考: 定期フォローアップ必要"""
        result = parse_output_summary(input_text)

        assert result["現在の処方"] == "アムロジピン5mg"
        assert result["備考"] == "定期フォローアップ必要"

    def test_parse_empty_string(self):
        """パース - 空文字列"""
        input_text = ""
        result = parse_output_summary(input_text)

        # すべてのセクションが空文字列
        assert result["現在の処方"] == ""
        assert result["備考"] == ""

    def test_parse_newline_only(self):
        """パース - 改行のみ"""
        input_text = "\n\n\n"
        result = parse_output_summary(input_text)

        # すべてのセクションが空文字列
        assert result["現在の処方"] == ""
        assert result["備考"] == ""

    def test_parse_section_name_only(self):
        """パース - セクション名のみ（内容なし）"""
        input_text = "備考:"
        result = parse_output_summary(input_text)

        assert result["備考"] == ""

    def test_parse_no_section_lines(self):
        """パース - セクション名なしの行"""
        input_text = """これはセクション名のない行
現在の処方: アムロジピン
また別の行"""
        result = parse_output_summary(input_text)

        # "これはセクション名のない行" は無視される（current_sectionがNone）
        # "また別の行" は "現在の処方" セクションに追加される
        assert result["現在の処方"] == "アムロジピン\nまた別の行"

    def test_parse_unknown_section_name(self):
        """パース - 未知のセクション名"""
        input_text = """現在の処方: アムロジピン
未知のセクション: これは無視される
備考: なし"""
        result = parse_output_summary(input_text)

        # 未知のセクションは現在のセクション（現在の処方）に継続して追加される
        assert result["現在の処方"] == "アムロジピン\n未知のセクション: これは無視される"
        assert result["備考"] == "なし"

    def test_parse_mixed_colon_formats(self):
        """パース - 混在したコロン形式"""
        input_text = """現在の処方: アムロジピン
備考：定期フォローアップ"""
        result = parse_output_summary(input_text)

        assert result["現在の処方"] == "アムロジピン"
        assert result["備考"] == "定期フォローアップ"

    def test_parse_section_with_colon_in_content(self):
        """パース - 内容にコロンを含む"""
        input_text = "備考: 注意: 血圧測定必須"
        result = parse_output_summary(input_text)

        # 最初のコロン以降がすべて内容
        assert result["備考"] == "注意: 血圧測定必須"

    def test_parse_alias_with_fullwidth_colon(self):
        """パース - エイリアス（全角コロン）その他 → 備考"""
        input_text = "補足：追加情報"
        result = parse_output_summary(input_text)

        # "補足" は "備考" にマッピング
        assert result["備考"] == "追加情報"

    def test_parse_alias_without_colon(self):
        """パース - エイリアス（コロンなし）"""
        input_text = "補足 追加の情報"
        result = parse_output_summary(input_text)

        # "補足" は "備考" にマッピング
        assert result["備考"] == "追加の情報"

    def test_parse_section_continuation(self):
        """パース - セクション継続"""
        input_text = """現在の処方: アムロジピン
継続行1
継続行2
備考: なし"""
        result = parse_output_summary(input_text)

        assert result["現在の処方"] == "アムロジピン\n継続行1\n継続行2"
        assert result["備考"] == "なし"

    def test_parse_empty_lines_between_sections(self):
        """パース - セクション間の空行"""
        input_text = """現在の処方: アムロジピン

備考: なし"""
        result = parse_output_summary(input_text)

        # 空行は無視される
        assert result["現在の処方"] == "アムロジピン"
        assert result["備考"] == "なし"

    def test_parse_whitespace_only_lines(self):
        """パース - 空白のみの行"""
        input_text = """現在の処方: アムロジピン

備考: なし"""
        result = parse_output_summary(input_text)

        # 空白のみの行は strip() で空になり無視される
        assert result["現在の処方"] == "アムロジピン"
        assert result["備考"] == "なし"

    def test_parse_complex_multiline_content(self):
        """パース - 複雑な複数行内容"""
        input_text = """現在の処方: アムロジピン5mg
- 朝食後
- 1日1回
備考: 血圧手帳記入"""
        result = parse_output_summary(input_text)

        expected = "アムロジピン5mg\n- 朝食後\n- 1日1回"
        assert result["現在の処方"] == expected
        assert result["備考"] == "血圧手帳記入"

    def test_parse_all_aliases(self):
        """パース - すべてのエイリアス確認（備考系のみ）"""
        input_text = """その他: 内容2
補足: 内容3
メモ: 内容4"""
        result = parse_output_summary(input_text)

        # "その他", "補足", "メモ" はすべて "備考" にマッピング
        # 同じセクションへの複数マッピングの場合、最後の値で上書きされる（実装の仕様）
        # 最後に出現した "メモ" の内容のみが保持される
        assert result["備考"] == "内容4"

    def test_parse_leading_trailing_spaces_in_content(self):
        """パース - 内容の前後スペース"""
        input_text = "備考:   特記事項なし   "
        result = parse_output_summary(input_text)

        # strip() されるため前後のスペースは削除される
        assert result["備考"] == "特記事項なし"

    def test_parse_no_space_after_colon(self):
        """パース - コロン直後にスペースなし"""
        input_text = "備考:特記事項なし"
        result = parse_output_summary(input_text)

        assert result["備考"] == "特記事項なし"

    def test_parse_multiple_spaces_after_section_name(self):
        """パース - セクション名後に複数スペース"""
        input_text = "備考    特記事項なし"
        result = parse_output_summary(input_text)

        # パターンマッチで空白を吸収
        assert result["備考"] == "特記事項なし"
