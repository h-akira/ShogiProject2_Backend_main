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
├── migrations/
│   ├── migrate.py             # マイグレーション実行スクリプト
│   ├── requirements.txt       # マイグレーション用依存パッケージ
│   └── sql/
│       ├── 001_create_tables.sql
│       └── 002_create_indexes.sql
├── src/                       # Lambda デプロイ対象（CodeUri）
│   ├── app.py                 # エントリポイント (lambda_handler)
│   ├── domain/                # ドメイン層（VO・エンティティ・Repository ABC・例外）
│   ├── application/           # アプリケーション層（ユースケース・DTO）
│   ├── infrastructure/        # インフラ層（DB 実装・Cognito クライアント）
│   ├── presentation/          # プレゼンテーション層（ルーティング・DI・例外マッピング）
│   └── common/                # 認証・設定・ユーティリティ
├── tests/
│   ├── pytest.ini             # pytest 設定
│   ├── domain/                # ドメイン層テスト（純粋 Python、IO なし）
│   ├── application/           # アプリケーション層テスト（InMemoryRepository 使用）
│   └── dsql/                  # DSQL 結合テスト（AWS 認証必須）
└── docs/                      # DDD 設計ドキュメント
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

CodeBuild の `post_build` フェーズで `sam deploy` 後に自動実行される。

### DDL の管理ルール

- SQL ファイルは `migrations/sql/` に `NNN_<説明>.sql` の命名で配置
- ファイル内は `-- STATEMENT` コメントで区切り、1 DDL ずつ別トランザクションで実行（Aurora DSQL の制約）
- 全 DDL に `IF NOT EXISTS` を付与し、冪等性を担保

## テスト

テスト方針・実行方法・テスト構成の詳細は [tests/README.md](tests/README.md) を参照。

## 設計ドキュメント

DDD（ドメイン駆動設計）に基づく設計書は `docs/` 配下を参照。

| ファイル | 内容 |
|---------|------|
| [01_domain_model.md](docs/01_domain_model.md) | ドメインモデル概要・境界づけられたコンテキスト・ユビキタス言語 |
| [02_aggregates.md](docs/02_aggregates.md) | 集約定義・Value Object・不変条件 |
| [03_use_cases.md](docs/03_use_cases.md) | ユースケース一覧・Command/Response DTO |
| [04_architecture.md](docs/04_architecture.md) | 4 層アーキテクチャ・依存ルール・DI 設計 |
| [05_testing_strategy.md](docs/05_testing_strategy.md) | DDD テストピラミッド・テスト構成 |
