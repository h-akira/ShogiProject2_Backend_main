# SAM テンプレート設計

## 概要

メイン API の AWS リソースを SAM (Serverless Application Model) テンプレートで定義する。命名規約は [units_contracts.md](../../../docs/units_contracts.md) に準拠する。

| 項目 | 値 |
|------|-----|
| テンプレートファイル | `Backend/main/template.yaml` |
| スタック名 | `stack-sgp-${env}-backend-main` |
| Transform | `AWS::Serverless-2016-10-31` |

---

## Parameters

| パラメータ名 | 型 | デフォルト | 説明 |
|-------------|-----|---------|------|
| `Env` | String | なし | 環境識別子 (`dev`, `pro`) |
| `KifuMax` | String | `2000` | ユーザーあたり棋譜上限数 |
| `TagMax` | String | `50` | ユーザーあたりタグ上限数 |

### Cognito 情報の取得

Cognito 情報はインフラスタックからの CloudFormation エクスポートとして取得する。テンプレート内で `Fn::ImportValue` を直接使用する。

| エクスポート名 | 値 | 用途 |
|--------------|-----|------|
| `sgp-${Env}-infra-CognitoUserPoolArn` | User Pool ARN | API Gateway の Cognito Authorizer |
| `sgp-${Env}-infra-CognitoUserPoolId` | User Pool ID | Lambda 環境変数（アカウント削除時の Cognito 操作） |
| `sgp-${Env}-infra-CognitoClientId` | App Client ID | Lambda 環境変数（パスワード検証時の `AdminInitiateAuth`） |

---

## Globals

```yaml
Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: python3.13
  Api:
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowOrigin: "'*'"
      AllowCredentials: false
```

---

## Resources

### Aurora DSQL クラスタ (`DsqlCluster`)

[01_database_design.md](01_database_design.md) に基づくデータストア定義。

- リソースタイプ: `AWS::DSQL::Cluster`
- DeletionProtectionEnabled: `true`（本番データの誤削除を防止）

> テーブルとインデックスの作成は DDL で行う（CloudFormation ではなくアプリケーション初期化時またはマイグレーションスクリプトで実行）。DDL の詳細は [01_database_design.md](01_database_design.md) を参照。

### API Gateway (`ApiGateway`)

- リソースタイプ: `AWS::Serverless::Api`
- StageName: `Prod`
- Cognito Authorizer をデフォルト認証として設定

```yaml
ApiGateway:
  Type: AWS::Serverless::Api
  Properties:
    StageName: Prod
    Auth:
      DefaultAuthorizer: CognitoAuthorizer
      Authorizers:
        CognitoAuthorizer:
          UserPoolArn: !ImportValue
            Fn::Sub: "sgp-${Env}-infra-CognitoUserPoolArn"
          Identity:
            Header: Authorization
```

### Lambda 関数 (`ApiFunction`)

- リソースタイプ: `AWS::Serverless::Function`
- FunctionName: `lambda-sgp-${Env}-backend-main`

#### 基本設定

| 項目 | 値 |
|------|-----|
| CodeUri | `src/` |
| Handler | `app.lambda_handler` |
| Runtime | `python3.13` |

#### 環境変数

| 変数名 | 値 |
|--------|-----|
| `DSQL_CLUSTER_ENDPOINT` | `!GetAtt DsqlCluster.Endpoint` |
| `KIFU_MAX` | `!Ref KifuMax` |
| `TAG_MAX` | `!Ref TagMax` |
| `USER_POOL_ID` | `!ImportValue sgp-${Env}-infra-CognitoUserPoolId` |
| `CLIENT_ID` | `!ImportValue sgp-${Env}-infra-CognitoClientId` |

#### IAM ポリシー

| ポリシー | 対象 | 用途 |
|---------|------|------|
| インラインポリシー | Aurora DSQL クラスタ | `dsql:DbConnectAdmin`（IAM 認証での DB 接続） |
| インラインポリシー | Cognito User Pool | `cognito-idp:AdminInitiateAuth`, `cognito-idp:AdminDeleteUser`, `cognito-idp:AdminGetUser` |

Aurora DSQL のインラインポリシー:

```yaml
- Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Action:
        - dsql:DbConnectAdmin
      Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/${DsqlCluster}"
```

Cognito のインラインポリシー:

```yaml
- Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Action:
        - cognito-idp:AdminInitiateAuth
        - cognito-idp:AdminDeleteUser
        - cognito-idp:AdminGetUser
      Resource: !ImportValue
        Fn::Sub: "sgp-${Env}-infra-CognitoUserPoolArn"
```

#### API イベント定義

| イベント名 | Path | Method | Auth |
|-----------|------|--------|------|
| `UsersMe` | `/api/v1/main/users/me` | ANY | デフォルト (Cognito) |
| `KifusRecent` | `/api/v1/main/kifus/recent` | GET | デフォルト (Cognito) |
| `Kifus` | `/api/v1/main/kifus` | ANY | デフォルト (Cognito) |
| `KifusExplorer` | `/api/v1/main/kifus/explorer` | GET | デフォルト (Cognito) |
| `KifusKid` | `/api/v1/main/kifus/{kid}` | ANY | デフォルト (Cognito) |
| `KifusShareCode` | `/api/v1/main/kifus/{kid}/share-code` | PUT | デフォルト (Cognito) |
| `SharedKifu` | `/api/v1/main/shared/{share_code}` | GET | `Authorizer: NONE` |
| `Tags` | `/api/v1/main/tags` | ANY | デフォルト (Cognito) |
| `TagsTid` | `/api/v1/main/tags/{tid}` | ANY | デフォルト (Cognito) |

> `SharedKifu` のみ `Auth: Authorizer: NONE` を明示し、認証なしアクセスを許可する。

---

## Outputs

インフラスタック（CloudFront のオリジン設定）とマイグレーションスクリプトに公開する出力。

| 出力名 | エクスポート名 | 値 | 用途 |
|-------|--------------|-----|------|
| `ApiGatewayId` | `sgp-${Env}-backend-main-ApiGatewayId` | `!Ref ApiGateway` | CloudFront のオリジン設定 |
| `ApiGatewayStageName` | `sgp-${Env}-backend-main-ApiGatewayStageName` | `Prod` | CloudFront のオリジンパス |
| `DsqlClusterEndpoint` | — | `!GetAtt DsqlCluster.Endpoint` | マイグレーションスクリプトでのエンドポイント取得 |

```yaml
Outputs:
  ApiGatewayId:
    Description: API Gateway REST API ID
    Value: !Ref ApiGateway
    Export:
      Name: !Sub "sgp-${Env}-backend-main-ApiGatewayId"
  ApiGatewayStageName:
    Description: API Gateway stage name
    Value: Prod
    Export:
      Name: !Sub "sgp-${Env}-backend-main-ApiGatewayStageName"
  DsqlClusterEndpoint:
    Description: Aurora DSQL cluster endpoint for migrations
    Value: !GetAtt DsqlCluster.Endpoint
```

---

## デプロイ

```bash
sam build
sam deploy \
  --stack-name stack-sgp-dev-backend-main \
  --parameter-overrides Env=dev \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

> Cognito 情報は `Fn::ImportValue` で自動取得するため、パラメータとして渡す必要はない。インフラスタック（`stack-sgp-${env}-infra-*`）が先にデプロイされている必要がある。
