-- Migration: 001_init_callbacks.sql
-- Description: Initialize callbacks and dead-letter queue tables for Honeypot session reporting.

-- [UP]
CREATE TABLE IF NOT EXISTS callbacks (
    id bigserial PRIMARY KEY,
    report_id text UNIQUE NOT NULL,
    session_id text NOT NULL,
    scam_detected boolean NOT NULL,
    scam_type text,
    confidence_level double precision,
    total_messages integer,
    engagement_sec integer,
    channel text,
    finalized_at timestamptz DEFAULT now(),
    payload jsonb NOT NULL
);

-- Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_callbacks_session ON callbacks (session_id);
CREATE INDEX IF NOT EXISTS idx_callbacks_scam_type ON callbacks (scam_type);
CREATE INDEX IF NOT EXISTS idx_callbacks_finalized_at ON callbacks (finalized_at);

-- GIN Index for deep searching across the entire payload
CREATE INDEX IF NOT EXISTS idx_callbacks_payload_gin ON callbacks USING GIN (payload jsonb_path_ops);

-- GIN Index for fast lookup specifically on extracted phone numbers
CREATE INDEX IF NOT EXISTS idx_callbacks_iocs_phone_gin ON callbacks USING GIN ((payload->'extractedIntelligence'->'phoneNumbers'));

-- Dead Letter Queue for failed callback attempts
CREATE TABLE IF NOT EXISTS callbacks_dlq (
    id bigserial PRIMARY KEY,
    session_id text NOT NULL,
    report_id text,
    dead_at timestamptz DEFAULT now(),
    ledger jsonb,
    final_report jsonb
);

-- [DOWN]
-- DROP TABLE IF EXISTS callbacks_dlq;
-- DROP INDEX IF EXISTS idx_callbacks_iocs_phone_gin;
-- DROP INDEX IF EXISTS idx_callbacks_payload_gin;
-- DROP INDEX IF EXISTS idx_callbacks_finalized_at;
-- DROP INDEX IF EXISTS idx_callbacks_scam_type;
-- DROP INDEX IF EXISTS idx_callbacks_session;
-- DROP TABLE IF EXISTS callbacks;
