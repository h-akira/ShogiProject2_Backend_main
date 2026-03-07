#!/usr/bin/env python3
"""Database migration script for Aurora DSQL.

Executes SQL files from the sql/ directory in alphabetical order.
Each statement (delimited by '-- STATEMENT') runs in a separate transaction
to comply with Aurora DSQL's one-DDL-per-transaction constraint.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import aurora_dsql_psycopg as dsql


def parse_sql_file(filepath: str) -> list[str]:
  """Parse a SQL file into individual statements, split by '-- STATEMENT'."""
  with open(filepath) as f:
    content = f.read()
  return [s.strip() for s in content.split("-- STATEMENT") if s.strip()]


def run_migrations(endpoint: str, region: str, sql_dir: str) -> None:
  """Connect to Aurora DSQL and execute all SQL migration files."""
  conn = dsql.connect(host=endpoint, dbname="postgres", region=region)

  sql_files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))
  if not sql_files:
    print(f"No SQL files found in {sql_dir}")
    conn.close()
    return

  for filepath in sql_files:
    filename = os.path.basename(filepath)
    print(f"Processing {filename}...")
    statements = parse_sql_file(filepath)

    for i, stmt in enumerate(statements, 1):
      try:
        with conn.cursor() as cur:
          cur.execute(stmt)
        conn.commit()
        print(f"  Statement {i}/{len(statements)} executed successfully")
      except Exception as e:
        conn.rollback()
        print(f"  Statement {i}/{len(statements)} FAILED: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

  conn.close()
  print("All migrations completed successfully")


def main() -> None:
  parser = argparse.ArgumentParser(description="Run database migrations")
  parser.add_argument("--endpoint", required=True, help="DSQL cluster endpoint")
  parser.add_argument("--region", default="ap-northeast-1", help="AWS region")
  parser.add_argument("--sql-dir", default="./sql", help="SQL files directory")
  args = parser.parse_args()

  run_migrations(args.endpoint, args.region, args.sql_dir)


if __name__ == "__main__":
  main()
