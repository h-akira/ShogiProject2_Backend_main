# Aurora DSQL SAM テンプレートリファレンス

本プロジェクトの SAM テンプレートで Aurora DSQL を利用するための技術仕様をまとめる。

---

## AWS::DSQL::Cluster

Aurora DSQL クラスタの CloudFormation リソースタイプ。

### 基本定義

```yaml
Resources:
  DsqlCluster:
    Type: AWS::DSQL::Cluster
    Properties:
      DeletionProtectionEnabled: true
      Tags:
        - Key: Project
          Value: sgp
        - Key: Env
          Value: !Ref Env
```

### プロパティ

| プロパティ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `DeletionProtectionEnabled` | Boolean | いいえ | `true` でスタック削除時のクラスタ削除を防止 |
| `Tags` | List of Tag | いいえ | リソースタグ |

> Aurora DSQL はサーバーレスのため、インスタンスサイズやストレージ容量の指定は不要。

### 戻り値

| 属性 | 取得方法 | 値 |
|------|---------|-----|
| クラスタ ID | `!Ref DsqlCluster` | クラスタ識別子 |
| エンドポイント | `!GetAtt DsqlCluster.Endpoint` | 接続用エンドポイント URL |

---

## IAM ポリシー

Lambda から Aurora DSQL に IAM 認証で接続するために必要なポリシー。

### インラインポリシー定義

```yaml
Policies:
  - Version: "2012-10-17"
    Statement:
      - Effect: Allow
        Action:
          - dsql:DbConnectAdmin
        Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/${DsqlCluster}"
```

### IAM アクション

| アクション | 説明 |
|-----------|------|
| `dsql:DbConnectAdmin` | Aurora DSQL クラスタへの管理者接続を許可（DDL + DML） |
| `dsql:DbConnect` | 通常接続（DML のみ、DDL 不可） |

> 本プロジェクトでは DDL 実行（テーブル作成等）も必要なため `DbConnectAdmin` を使用する。

### ARN 形式

```
arn:aws:dsql:<region>:<account-id>:cluster/<cluster-id>
```

---

## Lambda 環境変数

クラスタエンドポイントを Lambda の環境変数として渡す。

```yaml
ApiFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub "lambda-sgp-${Env}-backend-main"
    CodeUri: src/
    Handler: app.lambda_handler
    Runtime: python3.13
    Environment:
      Variables:
        DSQL_CLUSTER_ENDPOINT: !GetAtt DsqlCluster.Endpoint
        KIFU_MAX: !Ref KifuMax
        TAG_MAX: !Ref TagMax
        USER_POOL_ID: !ImportValue
          Fn::Sub: "sgp-${Env}-infra-CognitoUserPoolId"
        CLIENT_ID: !ImportValue
          Fn::Sub: "sgp-${Env}-infra-CognitoClientId"
    Policies:
      - Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action:
              - dsql:DbConnectAdmin
            Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/${DsqlCluster}"
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

---

## テーブル・インデックスの作成

Aurora DSQL のテーブルとインデックスは CloudFormation では定義できない。アプリケーション初期化時またはマイグレーションスクリプトで DDL を実行する。

### DDL 実行の注意点

| 制約 | 内容 |
|------|------|
| DDL と DML の混在 | 不可（別トランザクションで実行） |
| 1 トランザクション内の DDL | 1 文のみ |
| インデックス作成 | `CREATE INDEX ASYNC` を使用（非ブロッキング） |

### マイグレーション実行例

```bash
# psql で直接接続して DDL を実行する場合
# IAM 認証トークンの取得が必要
aws dsql generate-db-connect-admin-auth-token \
  --hostname <cluster-endpoint> \
  --region ap-northeast-1

# 取得したトークンをパスワードとして psql で接続
PGPASSWORD="<token>" psql \
  -h <cluster-endpoint> \
  -U admin \
  -d postgres \
  -f migration.sql
```

---

## デプロイ

```bash
cd Backend/main
sam build
sam deploy \
  --stack-name stack-sgp-dev-backend-main \
  --parameter-overrides Env=dev \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

> Cognito 情報は `Fn::ImportValue` で自動取得する。インフラスタック（`stack-sgp-${env}-infra-*`）が先にデプロイされている必要がある。

---

## 参考リンク

- [AWS::DSQL::Cluster](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
- [Aurora DSQL IAM authentication](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/security-iam.html)
- [Connecting to Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/connecting.html)
