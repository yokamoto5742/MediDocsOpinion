# RDS パスワードローテーション追従

RDS マネージドシークレットのパスワードが自動ローテーションされても、ECS タスクを再起動せずにアプリが追従できるようにする実装手順。

## 背景・原因

- `POSTGRES_PASSWORD` は `ecs/task-definition.json` の `secrets` ブロックから RDS マネージドシークレット（`rds!db-...:password`）を **環境変数として注入** している。
- ECS が環境変数を解決するのは **コンテナ起動時の1回だけ**。シークレットがローテーションされても、稼働中コンテナの環境変数は更新されない。
- `app/core/database.py` の `engine` は import 時に1回だけ生成され、`get_settings()` は `@lru_cache` で固定される。
- 結果、ローテーション後に新規接続を張ると古いパスワードで `FATAL: password authentication failed` が発生する。

> 補足: すでに認証済みの接続はパスワード変更後も生き続けるため、失敗するのは **新規の物理接続を張るとき** のみ（プール増設・`pool_recycle`・切断後）。`pool_pre_ping` はこの追従とは無関係。

## 対策の方針

ライブプロセス内でローテーション後のパスワードを得る唯一の方法は `GetSecretValue` を直接呼ぶこと。SQLAlchemy の `do_connect` イベントで接続確立直前に Secrets Manager から最新の認証情報を注入する。

## 変更ファイル

| ファイル | 変更内容 |
| --- | --- |
| `app/core/config.py` | `db_secret_name`, `db_secret_ttl_seconds` を追加 |
| `app/core/database.py` | `_RotatingCredentials`（短TTLキャッシュ）と `do_connect` リスナーを追加 |
| `docs/iam-policies.json` | `medidocsTaskRole` に RDS シークレットの `secretsmanager:GetSecretValue` を追加（ドキュメント） |
| `ecs/task-definition.json` | `DB_SECRET_NAME` 環境変数（RDS シークレット ARN）を追加 |
| `tests/core/test_database.py` | `_RotatingCredentials` のテスト4件を追加 |

### 動作概要（`app/core/database.py`）

- `settings.db_secret_name` が設定されている場合のみ `do_connect` リスナーを登録する（ローカル開発は `.env` のパスワードでそのまま動作）。
- 接続のたびにキャッシュ（既定 TTL 300 秒）から認証情報を取得し、`cparams` の `user` / `password` を上書きする。
- `psycopg2.OperationalError`（ローテーション直後の古いパスワードを想定）の場合のみ、キャッシュを破棄して最新を再取得し **1回だけ再接続** する。
- `pool_pre_ping` は `False` のまま（変更しない）。

## 実装手順

1. `app/core/config.py` に設定フィールドを追加する。

   ```python
   db_secret_name: str | None = None
   db_secret_ttl_seconds: int = 300
   ```

2. `app/core/database.py` に `_RotatingCredentials` と `do_connect` リスナーを実装する（`settings.db_secret_name` 設定時のみ登録）。

3. `docs/iam-policies.json` の `medidocsTaskRole` に RDS シークレットへの `secretsmanager:GetSecretValue` を追記する。

4. `ecs/task-definition.json` の `environment` に `DB_SECRET_NAME`（RDS シークレット ARN）を追加する。

5. `tests/core/test_database.py` にキャッシュ/強制再取得/TTL 期限切れのテストを追加する。

6. 検証する。

   ```bash
   python -m pytest tests/ -q
   pyright app/core/database.py app/core/config.py tests/core/test_database.py
   ruff check app/core/database.py app/core/config.py tests/core/test_database.py
   ```

## デプロイ順序（重要）

アプリは `medidocsTaskRole` で動作するが、このロールは現状 Bedrock 権限のみ。IAM 反映前に `DB_SECRET_NAME` を載せると `GetSecretValue` が `AccessDeniedException`（botocore `ClientError`）を投げ、これは `psycopg2.OperationalError` ではないため except に捕まらず伝播し、**全ての新規 DB 接続が失敗する**。必ず次の順で実施する。

1. **先に** `medidocsTaskRole` へ `secretsmanager:GetSecretValue`（RDS シークレット ARN）を付与し、反映を確認する。
2. **その後** `DB_SECRET_NAME` を含むタスク定義をデプロイする。

> AccessDenied / Throttling で fail-fast するのは正しい挙動のため、try/except での握り潰しは行わない（KISS）。

## 受け入れテスト

`do_connect` の注入と「認証失敗 → 再取得 → 再接続」のリトライは実 PostgreSQL が必要で単体テストでは検証できない。ステージングで **実際に RDS シークレットをローテーションし、アプリを再起動せずに再接続すること** を確認する。これが本機能の受け入れ基準であり、`pytest` の成功だけでは追従を証明できない。

## 既存インシデントの即時復旧

このコード修正は予防策であり、IAM 付与＋デプロイ完了後に有効化される。現在ローテーションでアプリが停止している場合は、まず次を実行して復旧する（新タスクが現行シークレットを読み直す。これで直ればローテーション起因と確定できる）。

```bash
aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
```

## 補足

- **Secrets Manager 呼び出し回数**: 接続失敗時は `force_refresh=True` で無条件に再取得するため、同時失敗が多いと `GetSecretValue` が集中する。`pool_size=5 + max_overflow=10`（最大15）では上限に対し十分余裕があるため対応不要。
- **Alembic マイグレーション**: `alembic/env.py` は別経路でエンジンを生成するため本追従は効かない。デプロイ時の短時間実行（新パスワード）で完結するため問題ない。
