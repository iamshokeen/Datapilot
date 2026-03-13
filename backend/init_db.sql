-- DataPilot Internal Database Initialization
-- Run ONCE on a fresh database before starting the backend.

CREATE EXTENSION IF NOT EXISTS vector;

-- ── Connections ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS db_connections (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias                       VARCHAR(100)    NOT NULL,
    host                        VARCHAR(255)    NOT NULL,
    port                        INTEGER         NOT NULL DEFAULT 5432,
    database_name               VARCHAR(255)    NOT NULL,
    username                    VARCHAR(255)    NOT NULL,
    connection_string_encrypted TEXT            NOT NULL,
    is_active                   BOOLEAN         NOT NULL DEFAULT TRUE,
    schema_indexed              BOOLEAN         NOT NULL DEFAULT FALSE,
    total_tables                INTEGER         NOT NULL DEFAULT 0,
    created_at                  TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- ── Schema embeddings ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_embeddings (
    id                  SERIAL          PRIMARY KEY,
    connection_id       UUID            NOT NULL REFERENCES db_connections(id) ON DELETE CASCADE,
    table_full_name     VARCHAR(255)    NOT NULL,
    content             TEXT            NOT NULL,
    embedding           VECTOR(1536)    NOT NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_connection_table UNIQUE (connection_id, table_full_name)
);

-- ivfflat index — only effective once there are rows; safe to create upfront
CREATE INDEX IF NOT EXISTS idx_schema_embeddings_vector
    ON schema_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- ── Query history (ECHO cache + token tracking + feedback) ────────────────────
CREATE TABLE IF NOT EXISTS query_history (
    id                  SERIAL          PRIMARY KEY,
    connection_id       UUID            NOT NULL REFERENCES db_connections(id) ON DELETE CASCADE,
    session_id          VARCHAR(100),
    question            TEXT            NOT NULL,
    generated_sql       TEXT,
    was_successful      BOOLEAN,
    error_message       TEXT,
    rows_returned       INTEGER,
    execution_time_ms   FLOAT,
    llm_model_used      VARCHAR(100),
    response_payload    JSONB,
    -- ECHO
    question_embedding  VECTOR(1536),
    echo_tier           INTEGER         DEFAULT 3,
    verified            BOOLEAN,
    feedback            VARCHAR(10),
    correction_note     TEXT,
    -- Token / cost tracking
    input_tokens        INTEGER         DEFAULT 0,
    output_tokens       INTEGER         DEFAULT 0,
    cache_read_tokens   INTEGER         DEFAULT 0,
    cache_write_tokens  INTEGER         DEFAULT 0,
    cost_usd            FLOAT           DEFAULT 0.0,
    retry_count         INTEGER         DEFAULT 0,
    few_shot_used       BOOLEAN         DEFAULT FALSE,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_history_connection
    ON query_history (connection_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_query_history_embedding
    ON query_history
    USING ivfflat (question_embedding vector_cosine_ops)
    WITH (lists = 10)
    WHERE question_embedding IS NOT NULL;

-- ── Conversation turns (multi-turn context) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS conversation_turns (
    id              SERIAL          PRIMARY KEY,
    session_id      VARCHAR(100)    NOT NULL,
    connection_id   UUID            NOT NULL REFERENCES db_connections(id) ON DELETE CASCADE,
    turn_number     INTEGER         NOT NULL DEFAULT 0,
    question        TEXT            NOT NULL,
    narrative       TEXT,
    summary         TEXT,
    data            JSONB,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_turns_session
    ON conversation_turns (session_id, created_at DESC);
