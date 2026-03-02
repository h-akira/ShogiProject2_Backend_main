import json
import os

# Set environment variables before any application imports
os.environ["DSQL_CLUSTER_ENDPOINT"] = "localhost"
os.environ["KIFU_MAX"] = "2000"
os.environ["TAG_MAX"] = "50"
os.environ["USER_POOL_ID"] = "ap-northeast-1_TestPool"
os.environ["CLIENT_ID"] = "test-client-id"
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

import pytest
import boto3
from moto import mock_aws


@pytest.fixture
def aws_mock():
  with mock_aws():
    yield


@pytest.fixture
def cognito_resources(aws_mock):
  client = boto3.client("cognito-idp", region_name="ap-northeast-1")
  pool = client.create_user_pool(PoolName="test-pool")
  pool_id = pool["UserPool"]["Id"]
  app_client = client.create_user_pool_client(
    UserPoolId=pool_id,
    ClientName="test-client",
    ExplicitAuthFlows=["ADMIN_NO_SRP_AUTH"],
  )
  client_id = app_client["UserPoolClient"]["ClientId"]
  os.environ["USER_POOL_ID"] = pool_id
  os.environ["CLIENT_ID"] = client_id
  yield {"pool_id": pool_id, "client_id": client_id}


def make_apigw_event(
  method: str,
  path: str,
  body: dict | None = None,
  username: str | None = None,
  query_params: dict | None = None,
  path_params: dict | None = None,
) -> dict:
  event = {
    "httpMethod": method,
    "path": path,
    "body": json.dumps(body) if body else None,
    "queryStringParameters": query_params,
    "pathParameters": path_params,
    "headers": {"Content-Type": "application/json"},
    "requestContext": {},
    "multiValueHeaders": {},
    "multiValueQueryStringParameters": query_params if query_params else None,
    "isBase64Encoded": False,
    "resource": path,
    "stageVariables": None,
  }
  if username:
    event["requestContext"] = {
      "authorizer": {
        "claims": {
          "cognito:username": username,
          "email": f"{username}@example.com",
          "email_verified": "true",
        },
      },
    }
  return event


# pytest-postgresql fixtures (only if PostgreSQL is available)
try:
  import shutil
  if shutil.which("pg_config") is None:
    raise FileNotFoundError("pg_config not found")

  from pytest_postgresql import factories

  postgresql_proc = factories.postgresql_proc()
  postgresql = factories.postgresql("postgresql_proc")

  TABLE_DDL = """
CREATE TABLE kifus (
  kid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  slug        VARCHAR(1024) NOT NULL,
  side        VARCHAR(20) NOT NULL DEFAULT 'none',
  result      VARCHAR(20) NOT NULL DEFAULT 'none',
  memo        TEXT NOT NULL DEFAULT '',
  kif         TEXT NOT NULL DEFAULT '',
  shared      BOOLEAN NOT NULL DEFAULT FALSE,
  share_code  VARCHAR(36),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tags (
  tid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  name        VARCHAR(127) NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE kifu_tags (
  kid         VARCHAR(12) NOT NULL,
  tid         VARCHAR(12) NOT NULL,
  PRIMARY KEY (kid, tid)
);

CREATE UNIQUE INDEX idx_kifus_user_slug
  ON kifus (username, slug);

CREATE INDEX idx_kifus_user_updated
  ON kifus (username, updated_at DESC);

CREATE UNIQUE INDEX idx_kifus_share_code
  ON kifus (share_code) WHERE share_code IS NOT NULL;

CREATE UNIQUE INDEX idx_tags_user_name
  ON tags (username, name);

CREATE INDEX idx_kifu_tags_tid
  ON kifu_tags (tid);
"""

  @pytest.fixture
  def db_connection(postgresql):
    from psycopg.rows import dict_row
    postgresql.row_factory = dict_row

    cur = postgresql.cursor()
    cur.execute(TABLE_DDL)
    postgresql.commit()
    cur.close()

    import repositories.db as db_mod
    db_mod._conn = postgresql

    yield postgresql

  HAS_POSTGRESQL = True
except (ImportError, Exception):
  HAS_POSTGRESQL = False

requires_postgresql = pytest.mark.skipif(
  not HAS_POSTGRESQL,
  reason="PostgreSQL not available"
)
