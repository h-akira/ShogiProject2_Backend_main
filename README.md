# Backend/main — メイン API

将棋棋譜管理アプリケーションのメイン API。ユーザー管理、棋譜 CRUD、タグ CRUD、共有棋譜の取得を提供する。

## アーキテクチャ

| 項目 | 値 |
|------|-----|
| フレームワーク | AWS Lambda Powertools (`APIGatewayRestResolver`) |
| 構成 | Lambdalith（単一 Lambda で全エンドポイントを処理） |
| ランタイム | Python 3.13 |
| データストア | Aurora DSQL（PostgreSQL 16 互換、IAM 認証、VPC 不要） |
| 認証 | Cognito Authorizer（API Gateway レベル） |
| IaC | SAM (`template.yaml`) |

## ディレクトリ構成

```
Backend/main/
├── template.yaml              # SAM テンプレート
├── requirements.txt           # 本番依存パッケージ
├── requirements-dev.txt       # 開発用依存パッケージ
├── pytest.ini                 # pytest 設定
├── migrations/
│   ├── migrate.py             # マイグレーション実行スクリプト
│   ├── requirements.txt       # マイグレーション用依存パッケージ
│   └── sql/
│       ├── 001_create_tables.sql
│       └── 002_create_indexes.sql
├── src/                       # Lambda デプロイ対象（CodeUri）
│   ├── app.py                 # エントリポイント (lambda_handler)
│   ├── routes/                # HTTP ルーティング
│   ├── services/              # ビジネスロジック
│   ├── repositories/          # DB アクセス（Aurora DSQL）
│   └── common/                # 認証・設定・例外・ユーティリティ
├── tests/
│   ├── conftest.py            # 共通フィクスチャ
│   ├── test_routes.py         # ルート層統合テスト
│   ├── test_services.py       # サービス層単体テスト
│   └── test_repositories.py   # リポジトリ層単体テスト（要 PostgreSQL）
└── docs/                      # 詳細設計ドキュメント
```

## API エンドポイント

ベースパス: `/api/v1/main`

| メソッド | パス | 概要 | 認証 |
|---------|------|------|------|
| GET | `/users/me` | ログインユーザー情報 | 要 |
| DELETE | `/users/me` | アカウント削除 | 要 |
| GET | `/kifus/recent` | 最近の棋譜一覧（最大10件） | 要 |
| POST | `/kifus` | 棋譜作成 | 要 |
| GET | `/kifus/explorer` | フォルダ階層での棋譜取得 | 要 |
| GET | `/kifus/{kid}` | 棋譜詳細 | 要 |
| PUT | `/kifus/{kid}` | 棋譜更新 | 要 |
| DELETE | `/kifus/{kid}` | 棋譜削除 | 要 |
| PUT | `/kifus/{kid}/share-code` | 共有コード再生成 | 要 |
| GET | `/shared/{share_code}` | 共有棋譜取得 | **不要** |
| GET | `/tags` | タグ一覧 | 要 |
| POST | `/tags` | タグ作成 | 要 |
| GET | `/tags/{tid}` | タグ詳細（関連棋譜含む） | 要 |
| PUT | `/tags/{tid}` | タグ更新 | 要 |
| DELETE | `/tags/{tid}` | タグ削除 | 要 |

API の詳細仕様は [docs/openapi_main.yaml](../../docs/openapi_main.yaml) を参照。

## デプロイ

### 前提条件

- インフラスタック (`stack-sgp-${env}-infra-*`) がデプロイ済みであること
  - 以下の CloudFormation Export が必要:
    - `sgp-${env}-infra-CognitoUserPoolArn`
    - `sgp-${env}-infra-CognitoUserPoolId`
    - `sgp-${env}-infra-CognitoClientId`
- AWS SAM CLI がインストール済みであること

### SAM テンプレートのリソース

| リソース | タイプ | 説明 |
|---------|-------|------|
| `DsqlCluster` | `AWS::DSQL::Cluster` | Aurora DSQL クラスタ（DeletionProtection 有効） |
| `ApiGateway` | `AWS::Serverless::Api` | API Gateway（Cognito Authorizer 付き） |
| `ApiFunction` | `AWS::Serverless::Function` | Lambda 関数 |

### パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|---------|------|
| `Env` | はい | — | 環境識別子 (`dev`, `pro`) |
| `KifuMax` | いいえ | `2000` | ユーザーあたり棋譜上限数 |
| `TagMax` | いいえ | `50` | ユーザーあたりタグ上限数 |

### デプロイコマンド

```bash
cd Backend/main

sam build

sam deploy \
  --stack-name stack-sgp-dev-backend-main \
  --parameter-overrides Env=dev \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

### Outputs（CloudFormation Export）

| 出力名 | エクスポート名 | 用途 |
|-------|--------------|------|
| `ApiGatewayId` | `sgp-${env}-backend-main-ApiGatewayId` | CloudFront オリジン設定 |
| `ApiGatewayStageName` | `sgp-${env}-backend-main-ApiGatewayStageName` | CloudFront オリジンパス |
| `DsqlClusterEndpoint` | （エクスポートなし） | マイグレーションスクリプト用 |

### Lambda 環境変数

| 変数名 | ソース |
|--------|-------|
| `DSQL_CLUSTER_ENDPOINT` | `DsqlCluster.Endpoint`（自動設定） |
| `KIFU_MAX` | パラメータ `KifuMax` |
| `TAG_MAX` | パラメータ `TagMax` |
| `USER_POOL_ID` | インフラスタックからの Import |
| `CLIENT_ID` | インフラスタックからの Import |

### Lambda IAM 権限

| アクション | 対象リソース |
|-----------|-------------|
| `dsql:DbConnectAdmin` | Aurora DSQL クラスタ |
| `cognito-idp:AdminInitiateAuth` | Cognito User Pool |
| `cognito-idp:AdminDeleteUser` | Cognito User Pool |
| `cognito-idp:AdminGetUser` | Cognito User Pool |

## マイグレーション

Aurora DSQL のテーブル・インデックスは SAM では管理できないため、`migrations/migrate.py` で DDL を実行する。

### 手動実行

```bash
cd Backend/main/migrations
pip install -r requirements.txt
python migrate.py --endpoint <DSQL_CLUSTER_ENDPOINT>
```

### CI/CD 統合

CodeBuild の `post_build` フェーズで `sam deploy` 後に自動実行される。詳細は [docs/07_migration_strategy.md](docs/07_migration_strategy.md) を参照。

### DDL の管理ルール

- SQL ファイルは `migrations/sql/` に `NNN_<説明>.sql` の命名で配置
- ファイル内は `-- STATEMENT` コメントで区切り、1 DDL ずつ別トランザクションで実行（Aurora DSQL の制約）
- 全 DDL に `IF NOT EXISTS` を付与し、冪等性を担保

## テスト

### 前提条件（PostgreSQL）

リポジトリ層テスト (`test_repositories.py`) はローカル PostgreSQL が必要。未インストールの場合は自動スキップされるが、全テストを実行するには以下でインストールする。

```bash
# macOS (Homebrew)
brew install postgresql@16
```

> **Note:** Aurora DSQL は PostgreSQL 16 互換のため `postgresql@16` を推奨。常駐サービスの起動（`brew services start`）は不要 — `pytest-postgresql` がテスト実行時に一時インスタンスを自動で起動・終了する。

### 実行方法

```bash
cd Backend/main
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### テスト構成

| ファイル | 対象 | PostgreSQL |
|---------|------|-----------|
| `test_services.py` | サービス層（バリデーション、ビジネスロジック） | 不要（mock） |
| `test_routes.py` | ルート層（HTTP ステータス、レスポンス形式） | 不要（mock） |
| `test_repositories.py` | リポジトリ層（SQL クエリ） | **必要**（pytest-postgresql） |

リポジトリ層テストはローカルに PostgreSQL がインストールされていない場合は自動でスキップされる。

> **Aurora DSQL との差異:** OCC（楽観的同時実行制御）や `CREATE INDEX ASYNC` 等の DSQL 固有動作はローカル PostgreSQL では検証できない。通常の SQL（INSERT/SELECT/UPDATE/DELETE/JOIN）の正当性検証が目的。

## 設計ドキュメント

詳細設計は `docs/` 配下を参照。

| ファイル | 内容 |
|---------|------|
| [01_database_design.md](docs/01_database_design.md) | テーブル・インデックス・アクセスパターン |
| [02_directory_structure.md](docs/02_directory_structure.md) | ディレクトリ構成・レイヤー責務 |
| [03_routing_design.md](docs/03_routing_design.md) | ルーティング・各ハンドラの処理フロー |
| [04_common_modules.md](docs/04_common_modules.md) | 共通処理・バリデーション・例外体系 |
| [05_sam_template.md](docs/05_sam_template.md) | SAM テンプレートの設計詳細 |
| [06_testing_strategy.md](docs/06_testing_strategy.md) | テスト方針・テストケース一覧 |
| [07_migration_strategy.md](docs/07_migration_strategy.md) | マイグレーション方針・CI/CD 統合 |
