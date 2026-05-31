import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"実行中: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"コマンドが終了コード {result.returncode} で失敗しました")
        sys.exit(result.returncode)


def main() -> None:
    run(["uv", "lock", "--upgrade"])
    run(["uv", "sync", "--all-extras"])


if __name__ == "__main__":
    main()
