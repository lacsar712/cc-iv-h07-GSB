import os
import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:54402/pvivscan")


def connect():
    return psycopg.connect(DSN, row_factory=dict_row)


SCHEMA = """
CREATE TABLE IF NOT EXISTS iv_scans (
    id serial PRIMARY KEY,
    string_code text NOT NULL,
    voc_v double precision NOT NULL,
    isc_a double precision NOT NULL,
    fill_factor double precision NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    verdict text,
    reason text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    processed_at timestamptz
);

/* 修复历史上可能留下的“半开半关”记录：pending 不得带结论，done 缺结论则重新排队。 */
UPDATE iv_scans
SET verdict = NULL, reason = NULL, processed_at = NULL
WHERE status = 'pending';

UPDATE iv_scans
SET status = 'pending', verdict = NULL, reason = NULL, processed_at = NULL
WHERE status = 'done'
  AND (verdict IS NULL OR reason IS NULL OR processed_at IS NULL);

ALTER TABLE iv_scans DROP CONSTRAINT IF EXISTS iv_scans_state_ck;
ALTER TABLE iv_scans ADD CONSTRAINT iv_scans_state_ck CHECK (
  (
    status = 'pending'
    AND verdict IS NULL
    AND reason IS NULL
    AND processed_at IS NULL
  )
  OR (
    status = 'done'
    AND verdict IN ('合格', '衰减')
    AND reason IS NOT NULL
    AND processed_at IS NOT NULL
  )
);

CREATE OR REPLACE FUNCTION notify_iv_scan() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('iv_scan_new', NEW.id::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_iv_scan_notify ON iv_scans;
CREATE TRIGGER trg_iv_scan_notify
AFTER INSERT ON iv_scans
FOR EACH ROW EXECUTE FUNCTION notify_iv_scan();
"""
