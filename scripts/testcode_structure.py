from datetime import datetime
from pathlib import Path


class TestStructureGenerator:
    def generate_structure(self, tests_root: Path) -> str:
        output_lines = [
            "=" * 60,
            f"テストファイル一覧: {tests_root.name}",
            f"パス: {tests_root}",
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]
        self._print_tree(tests_root, output_lines)
        return "\n".join(output_lines)

    def _print_tree(self, path: Path, lines: list[str], prefix: str = "", is_last: bool = True) -> None:
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{path.name}")

        if path.is_dir():
            children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            # テストファイル以外の.pyファイルと__pycache__を除外
            children = [
                c for c in children
                if not (c.name == "__pycache__" or (c.is_file() and not c.name.startswith("test_")))
            ]
            for i, child in enumerate(children):
                extension = "    " if is_last else "│   "
                self._print_tree(child, lines, prefix + extension, i == len(children) - 1)

    def save_to_file(self, content: str, filepath: Path) -> None:
        filepath.write_text(content, encoding="utf-8")
        print(f"テストファイル一覧を '{filepath}' に保存しました")
        print(f"ファイルの場所: {filepath.resolve()}")


def main() -> None:
    scripts_dir = Path(__file__).parent
    project_root = scripts_dir.parent
    tests_root = project_root / "tests"
    output_file = scripts_dir / "testcode_structure.txt"

    if not tests_root.exists():
        print(f"エラー: テストディレクトリ '{tests_root}' が見つかりません")
        return

    generator = TestStructureGenerator()
    content = generator.generate_structure(tests_root)
    generator.save_to_file(content, output_file)


if __name__ == "__main__":
    main()
