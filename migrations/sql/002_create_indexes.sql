-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifus_user_updated
  ON kifus (username, updated_at);

-- STATEMENT
CREATE UNIQUE INDEX ASYNC IF NOT EXISTS idx_kifus_user_slug
  ON kifus (username, slug);

-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifus_share_code
  ON kifus (share_code);

-- STATEMENT
CREATE UNIQUE INDEX ASYNC IF NOT EXISTS idx_tags_user_name
  ON tags (username, name);

-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifu_tags_tid
  ON kifu_tags (tid);
