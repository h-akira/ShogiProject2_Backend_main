import os

DSQL_CLUSTER_ENDPOINT: str = os.environ["DSQL_CLUSTER_ENDPOINT"]
KIFU_MAX: int = int(os.environ.get("KIFU_MAX", "2000"))
TAG_MAX: int = int(os.environ.get("TAG_MAX", "50"))
USER_POOL_ID: str = os.environ["USER_POOL_ID"]
CLIENT_ID: str = os.environ["CLIENT_ID"]
