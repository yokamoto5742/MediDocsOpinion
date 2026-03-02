import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

DEFAULT_ENV_FILE = ".env"
DEFAULT_SECRET_NAME = "medidocs/prod"
DEFAULT_REGION = "ap-northeast-1"


def parse_env_file(env_path: str) -> dict[str, str]:
    """envファイルを解析してキーと値の辞書を返す"""
    secrets: dict[str, str] = {}
    path = Path(env_path)

    if not path.exists():
        print(f"エラー: {env_path} が見つかりません")
        sys.exit(1)

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        secrets[key.strip()] = value.strip()

    return secrets


def create_or_update_secret(
    secret_name: str,
    secrets: dict[str, str],
    region: str,
) -> None:
    """Secrets Managerにシークレットを作成または更新する"""
    client = boto3.client("secretsmanager", region_name=region)
    secret_string = json.dumps(secrets, ensure_ascii=False)

    try:
        client.create_secret(
            Name=secret_name,
            SecretString=secret_string,
        )
        print(f"シークレット '{secret_name}' を作成しました")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            client.update_secret(
                SecretId=secret_name,
                SecretString=secret_string,
            )
            print(f"シークレット '{secret_name}' を更新しました")
        else:
            raise


def delete_secret(secret_name: str, region: str) -> None:
    """Secrets Managerからシークレットを削除する"""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=False,
        )
        print(f"シークレット '{secret_name}' を削除予約しました (30日後に完全削除)")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"エラー: シークレット '{secret_name}' が見つかりません")
        else:
            raise


def get_secret(secret_name: str, region: str) -> None:
    """Secrets Managerからシークレットを取得して表示する"""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        data = json.loads(response["SecretString"])
        print(f"シークレット '{secret_name}' の内容:")
        print("---")
        for key in data:
            # 値はマスクして表示
            value = data[key]
            masked = value[:4] + "****" if len(value) > 4 else "****"
            print(f"  {key} = {masked}")
        print("---")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"エラー: シークレット '{secret_name}' が見つかりません")
        else:
            raise


def prompt_input(label: str, default: str) -> str:
    """ユーザーに入力を求める (空ならデフォルト値)"""
    result = input(f"{label} [{default}]: ").strip()
    return result if result else default


def show_menu() -> str:
    """メインメニューを表示して選択を返す"""
    print("\n=== AWS Secrets Manager 管理ツール ===")
    print("1) シークレットを作成/更新")
    print("2) シークレットを確認")
    print("3) シークレットを削除")
    print("4) .envファイルの内容をプレビュー")
    print("q) 終了")
    print("=" * 38)
    return input("選択してください: ").strip()


def handle_create(env_file: str, secret_name: str, region: str) -> None:
    """シークレットの作成/更新を実行する"""
    secrets = parse_env_file(env_file)
    if not secrets:
        print("エラー: 環境変数が見つかりません")
        return

    print(f"\nファイル: {env_file}")
    print(f"シークレット名: {secret_name}")
    print(f"リージョン: {region}")
    print(f"登録する変数数: {len(secrets)}")
    print("---")
    for key in secrets:
        print(f"  {key}")
    print("---")

    confirm = input("登録しますか? (y/N): ").strip().lower()
    if confirm != "y":
        print("キャンセルしました")
        return

    create_or_update_secret(secret_name, secrets, region)


def handle_preview(env_file: str) -> None:
    """.envファイルの内容をプレビューする"""
    secrets = parse_env_file(env_file)
    if not secrets:
        print("エラー: 環境変数が見つかりません")
        return

    print(f"\nファイル: {env_file} ({len(secrets)} 件)")
    print("---")
    for key, value in secrets.items():
        masked = value[:4] + "****" if len(value) > 4 else "****"
        print(f"  {key} = {masked}")
    print("---")


def main() -> None:
    env_file = DEFAULT_ENV_FILE
    secret_name = DEFAULT_SECRET_NAME
    region = DEFAULT_REGION

    while True:
        choice = show_menu()

        if choice == "q":
            print("終了します")
            break

        if choice in ("1", "2", "3"):
            # 共通設定の入力
            secret_name = prompt_input("シークレット名", secret_name)
            region = prompt_input("リージョン", region)

        if choice == "1":
            env_file = prompt_input(".envファイルのパス", env_file)
            handle_create(env_file, secret_name, region)
        elif choice == "2":
            get_secret(secret_name, region)
        elif choice == "3":
            confirm = input(
                f"'{secret_name}' を削除しますか? (y/N): "
            ).strip().lower()
            if confirm == "y":
                delete_secret(secret_name, region)
            else:
                print("キャンセルしました")
        elif choice == "4":
            env_file = prompt_input(".envファイルのパス", env_file)
            handle_preview(env_file)
        else:
            print("無効な選択です")


if __name__ == "__main__":
    main()
