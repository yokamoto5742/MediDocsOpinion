import os
import argparse
from pathlib import Path
from datetime import datetime


class ProjectStructureGenerator:
    def __init__(self):
        self.ignore_patterns = {
            '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.pytest_cache',
            '*.egg-info', 'dist', '.tox', '.coverage', 'htmlcov','.claude','.serena','alembic','scripts',
            '.venv', 'venv', '.env', 'env', 'tests','nul','logs','assets',
            '.vscode', '.idea', '*.swp', '*.swo', '*~',
            '.git', '.gitignore', '.hg', '.svn',
            '.DS_Store', 'Thumbs.db', 'desktop.ini','pytest.ini',
            'node_modules', '.npm', 'package-lock.json',
            '*.log', '*.tmp', '.cache', 'CLAUDE.md',
        }

        self.important_files = {
            'DEVELOPMENT.md', 'requirements.txt',
            'setup.py', 'pyproject.toml', 'Dockerfile',
            'config.ini', 'alembic.ini', '.env', 'Procfile'
        }

    def should_ignore(self, path):
        path_name = path.name.lower()

        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if path_name.endswith(pattern[1:]):
                    return True
            elif pattern in path_name:
                return True
        return False

    def get_file_size_str(self, size):
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size // 1024}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size // (1024 * 1024):.1f}MB"
        else:
            return f"{size // (1024 * 1024 * 1024):.1f}GB"

    def generate_structure(self, root_path=".", max_depth=None, show_size=False):
        output_lines = []
        root = Path(root_path).resolve()

        output_lines.extend([
            "=" * 60,
            f"プロジェクト構造: {root.name}",
            f"パス: {root}",
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ])

        def print_tree(path, prefix="", is_last=True, level=0):
            if max_depth is not None and level > max_depth:
                return

            if self.should_ignore(path):
                return

            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{path.name}"

            if path.is_file():
                try:
                    size = path.stat().st_size
                    if show_size:
                        line += f" ({self.get_file_size_str(size)})"

                except (OSError, PermissionError):
                    line += " (アクセス不可)"

            output_lines.append(line)

            if path.is_dir():
                try:
                    children = [p for p in path.iterdir() if not self.should_ignore(p)]

                    def sort_key(x):
                        is_file = x.is_file()
                        is_important = x.name in self.important_files
                        return is_file, not is_important, x.name.lower()

                    children.sort(key=sort_key)

                    for i, child in enumerate(children):
                        is_last_child = i == len(children) - 1
                        extension = "    " if is_last else "│   "
                        print_tree(child, prefix + extension, is_last_child, level + 1)

                except PermissionError:
                    output_lines.append(f"{prefix}    (アクセス権限なし)")

        print_tree(root)

        return "\n".join(output_lines)

    def save_to_file(self, content, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"プロジェクト構造を '{filename}' に保存しました")
            return True
        except Exception as e:
            print(f"❌ ファイル保存エラー: {e}")
            return False


def main():
    # 現在のディレクトリがscriptsの場合、親ディレクトリを対象とする
    current_dir = os.path.basename(os.getcwd())
    default_path = ".." if current_dir == "scripts" else "."

    parser = argparse.ArgumentParser(
        description="Pythonプロジェクトの構造を出力するスクリプト"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=default_path,
        help="プロジェクトのルートパス (デフォルト: プロジェクトルート)"
    )
    parser.add_argument(
        "-o", "--output",
        default="project_structure.txt",
        help="出力ファイル名 (デフォルト: project_structure.txt)"
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        help="表示する最大深度 (デフォルト: 制限なし)"
    )
    parser.add_argument(
        "--show-size",
        action="store_true",
        help="ファイルサイズを表示"
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="隠しファイルも表示"
    )

    args = parser.parse_args()

    generator = ProjectStructureGenerator()

    if args.include_hidden:
        generator.ignore_patterns = {
            pattern for pattern in generator.ignore_patterns
            if not pattern.startswith('.')
        }

    try:
        structure = generator.generate_structure(
            root_path=args.path,
            max_depth=args.depth,
            show_size=args.show_size
        )

        # ファイルに保存
        if generator.save_to_file(structure, args.output):
            print(f"ファイルの場所: {os.path.abspath(args.output)}")

    except FileNotFoundError:
        print(f"エラー: パス '{args.path}' が見つかりません")
    except PermissionError:
        print(f"エラー: パス '{args.path}' にアクセス権限がありません")
    except Exception as e:
        print(f"予期しないエラー: {e}")


def quick_structure(path=None, depth=3):
    if path is None:
        current_dir = os.path.basename(os.getcwd())
        path = ".." if current_dir == "scripts" else "."
    generator = ProjectStructureGenerator()
    structure = generator.generate_structure(path, max_depth=depth, show_size=True)
    print(structure)


def save_structure(path=None, output_file="project_structure.txt", depth=None):
    if path is None:
        current_dir = os.path.basename(os.getcwd())
        path = ".." if current_dir == "scripts" else "."
    generator = ProjectStructureGenerator()
    structure = generator.generate_structure(path, max_depth=depth, show_size=True)
    return generator.save_to_file(structure, output_file)


if __name__ == "__main__":
    main()
