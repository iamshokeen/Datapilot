"""
DataPilot — One-Shot Project Setup Script
Run this once from inside your datapilot/ folder.
It creates every file and folder automatically.

Usage:
    python datapilot_setup.py
"""

import os
import sys

def write(path, content):
    """Create a file and all parent directories."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {path}")

def touch(path):
    """Create an empty __init__.py file."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("")
    print(f"  ✅ {path}")

print("\n🚀 DataPilot Setup — Creating project files...\n")

# ============================================================
# ROOT FILES
# ============================================================

write("docker-compose.yml", '''\
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${DATAPILOT_DB_USER:-datapilot}
      POSTGRES_PASSWORD: ${DATAPILOT_DB_PASSWORD:-datapilot}
      POSTGRES_DB: ${DATAPILOT_DB_NAME:-datapilot}
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATAPILOT_DB_USER:-datapilot}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
''')

write(".env.example", '''\
# ============================================================
# DataPilot — Environment Variables
# Copy this file to .env and fill in your values
# NEVER commit .env to git
# ============================================================

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o

DATAPILOT_DB_USER=datapilot
DATAPILOT_DB_PASSWORD=datapilot
DATAPILOT_DB_NAME=datapilot
DATAPILOT_DB_HOST=localhost
DATAPILOT_DB_PORT=5433

REDIS_URL=redis://localhost:6379/0

APP_ENV=development
SECRET_KEY=change-me-in-production
API_KEY_HEADER=X-API-Key

RATE_LIMIT_PER_MINUTE=30
SQL_QUERY_TIMEOUT_SECONDS=30
SQL_MAX_ROWS_RETURNED=1000

EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
''')

write(".gitignore", '''\
.env
.env.*
!.env.example
__pycache__/
*.py[cod]
.venv/
venv/
node_modules/
frontend/dist/
mlruns/
*.pem
*.key
.pytest_cache/
htmlcov/
.coverage
''')

# ============================================================
# BACKEND FILES
# ============================================================

write("backend/Dockerfile", '''\
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''')

write("backend/requirements.txt", '''\
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
pydantic==2.8.2
pydantic-settings==2.4.0
python-dotenv==1.0.1
sqlalchemy==2.0.35
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.3
pgvector==0.3.3
redis==5.0.8
openai==1.45.0
anthropic==0.34.2
langchain==0.3.1
langchain-openai==0.2.1
langchain-anthropic==0.2.1
langgraph==0.2.22
tiktoken==0.7.0
pandas==2.2.3
numpy==1.26.4
httpx==0.27.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
structlog==24.4.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
ruff==0.6.8
mypy==1.11.2
click==8.1.7
''')

write("backend/pytest.ini", '''\
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
''')

write("backend/init_db.sql", '''\
-- DataPilot Internal Database Initialization
-- Run ONCE after starting the postgres container

CREATE EXTENSION IF NOT EXISTS vector;

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

CREATE INDEX IF NOT EXISTS idx_schema_embeddings_vector
    ON schema_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

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
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_history_connection
    ON query_history (connection_id, created_at DESC);
''')

# ---- app/__init__.py ----
touch("backend/app/__init__.py")

# ---- app/config.py ----
write("backend/app/config.py", '''\
"""DataPilot — Application Configuration"""
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_env: Literal["development", "production"] = "development"
    secret_key: str = "change-me-in-production"
    api_key_header: str = "X-API-Key"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_model: str = "gpt-4o"

    datapilot_db_user: str = "datapilot"
    datapilot_db_password: str = "datapilot"
    datapilot_db_name: str = "datapilot"
    datapilot_db_host: str = "localhost"
    datapilot_db_port: int = 5433

    @property
    def datapilot_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.datapilot_db_user}:{self.datapilot_db_password}"
            f"@{self.datapilot_db_host}:{self.datapilot_db_port}/{self.datapilot_db_name}"
        )

    @property
    def datapilot_db_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.datapilot_db_user}:{self.datapilot_db_password}"
            f"@{self.datapilot_db_host}:{self.datapilot_db_port}/{self.datapilot_db_name}"
        )

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 30
    sql_query_timeout_seconds: int = 30
    sql_max_rows_returned: int = 1000
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
''')

# ---- app/main.py ----
write("backend/app/main.py", '''\
"""DataPilot — FastAPI Application Entry Point"""
import logging
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import ask, connect, health
from app.config import settings

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="DataPilot API",
    description="AI-powered BI Agent — ask questions about any PostgreSQL database in plain English",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(connect.router, prefix="/connect", tags=["Connection"])
app.include_router(ask.router, prefix="/ask", tags=["Query"])

@app.on_event("startup")
async def startup():
    structlog.get_logger().info("DataPilot API started", env=settings.app_env)
''')

# ---- api __init__ files ----
touch("backend/app/api/__init__.py")
touch("backend/app/api/routes/__init__.py")

# ---- health route ----
write("backend/app/api/routes/health.py", '''\
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", environment=settings.app_env)
''')

# ---- connect route ----
write("backend/app/api/routes/connect.py", '''\
"""DataPilot — /connect Endpoints"""
import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.core.embedding import SchemaEmbeddingPipeline
from app.core.schema_introspector import SchemaIntrospector
from app.models.schemas import ConnectRequest, ConnectResponse, ConnectionStatusResponse, ErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _get_engine():
    return create_async_engine(settings.datapilot_db_url, echo=False)


@router.post("", response_model=ConnectResponse, responses={400: {"model": ErrorResponse}})
async def connect_database(request: ConnectRequest):
    connection_string = request.to_connection_string()
    introspector = SchemaIntrospector(
        connection_string=connection_string,
        schemas_to_include=request.schemas,
        sample_rows_per_table=3,
    )

    loop = asyncio.get_event_loop()
    success, message = await loop.run_in_executor(_executor, introspector.test_connection)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Database connection failed: {message}")

    try:
        schema_info = await loop.run_in_executor(_executor, introspector.introspect)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema introspection failed: {str(e)}")

    connection_id = str(uuid.uuid4())
    engine = _get_engine()

    async with AsyncSession(engine) as session:
        await session.execute(
            text("""
                INSERT INTO db_connections
                    (id, alias, host, port, database_name, username, connection_string_encrypted, schema_indexed, total_tables)
                VALUES (:id, :alias, :host, :port, :db, :user, :conn_str, false, :total)
            """),
            {"id": connection_id, "alias": request.alias, "host": request.host, "port": request.port,
             "db": request.database, "user": request.username, "conn_str": connection_string,
             "total": schema_info.total_tables},
        )
        await session.commit()

        pipeline = SchemaEmbeddingPipeline(db_session=session)
        indexed_count = await pipeline.index_schema(connection_id, schema_info)

        await session.execute(
            text("UPDATE db_connections SET schema_indexed = true WHERE id = :id"),
            {"id": connection_id},
        )
        await session.commit()

    return ConnectResponse(
        connection_id=connection_id,
        alias=request.alias,
        database_name=schema_info.database_name,
        total_tables=schema_info.total_tables,
        tables=schema_info.get_table_names(),
        message=f"Successfully connected and indexed {indexed_count} tables.",
    )


@router.get("/{connection_id}", response_model=ConnectionStatusResponse)
async def get_connection(connection_id: str):
    engine = _get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            text("SELECT * FROM db_connections WHERE id = :id"), {"id": connection_id}
        )
        row = result.mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    return ConnectionStatusResponse(
        connection_id=row["id"], alias=row["alias"], host=row["host"],
        database_name=row["database_name"], total_tables=row["total_tables"],
        schema_indexed=row["schema_indexed"], is_active=row["is_active"],
        created_at=row["created_at"],
    )
''')

# ---- ask route ----
write("backend/app/api/routes/ask.py", '''\
"""DataPilot — /ask Endpoint"""
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.core.embedding import SchemaEmbeddingPipeline
from app.core.llm import get_llm_client
from app.core.sql_generator import SQLGenerator
from app.models.schemas import AskRequest, AskResponse, ErrorResponse, SQLResult

router = APIRouter()
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _get_engine():
    return create_async_engine(settings.datapilot_db_url, echo=False)


def _execute_sql_sync(connection_string: str, sql: str, max_rows: int) -> SQLResult:
    start = time.time()
    conn = psycopg2.connect(connection_string)
    conn.set_session(readonly=True, autocommit=False)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = {settings.sql_query_timeout_seconds * 1000}")
            cur.execute(sql)
            raw_rows = cur.fetchmany(max_rows)
        elapsed_ms = (time.time() - start) * 1000
        rows = [{k: str(v) if v is not None else None for k, v in dict(r).items()} for r in raw_rows]
        return SQLResult(sql=sql, rows=rows, row_count=len(rows),
                         columns=list(rows[0].keys()) if rows else [],
                         execution_time_ms=round(elapsed_ms, 2))
    finally:
        conn.close()


@router.post("", response_model=AskResponse, responses={400: {"model": ErrorResponse}})
async def ask_question(request: AskRequest):
    import asyncio
    options = request.options
    max_rows = options.max_rows if options else 100
    session_id = request.session_id or str(uuid.uuid4())
    engine = _get_engine()
    total_start = time.time()

    async with AsyncSession(engine) as db_session:
        result = await db_session.execute(
            text("SELECT * FROM db_connections WHERE id = :id AND is_active = true"),
            {"id": request.connection_id},
        )
        conn_row = result.mappings().fetchone()
        if not conn_row:
            raise HTTPException(status_code=404,
                detail=f"Connection {request.connection_id} not found. Run POST /connect first.")
        if not conn_row["schema_indexed"]:
            raise HTTPException(status_code=400, detail="Schema not yet indexed. Please reconnect.")

        pipeline = SchemaEmbeddingPipeline(db_session=db_session)
        chunks = await pipeline.search_relevant_tables(
            connection_id=request.connection_id, question=request.question, top_k=5)
        if not chunks:
            raise HTTPException(status_code=400, detail="No schema found. Try reconnecting.")

        schema_context = "\\n\\n---\\n\\n".join(chunks)
        llm_client = get_llm_client()
        generator = SQLGenerator(llm_client=llm_client, max_rows=max_rows)
        gen_result = generator.generate(question=request.question, schema_context=schema_context)

        if not gen_result.can_answer or not gen_result.sql:
            await _log_query(db_session, request.connection_id, session_id, request.question,
                             None, False, "LLM could not generate SQL", gen_result.model)
            return AskResponse(
                question=request.question,
                answer="I couldn\'t generate a SQL query for this question. The schema might not contain the relevant data.",
                session_id=session_id, query_id=-1, llm_model=gen_result.model,
                total_time_ms=round((time.time() - total_start) * 1000, 2))

        loop = asyncio.get_event_loop()
        try:
            sql_result = await loop.run_in_executor(
                _executor, _execute_sql_sync,
                conn_row["connection_string_encrypted"], gen_result.sql, max_rows)
        except Exception as e:
            await _log_query(db_session, request.connection_id, session_id, request.question,
                             gen_result.sql, False, str(e), gen_result.model)
            raise HTTPException(status_code=422, detail=f"SQL execution failed: {str(e)}")

        total_ms = round((time.time() - total_start) * 1000, 2)
        answer = ("The query returned no results." if sql_result.row_count == 0
                  else f"Found {sql_result.row_count} result(s).")

        query_id = await _log_query(db_session, request.connection_id, session_id,
                                    request.question, gen_result.sql, True, None,
                                    gen_result.model, sql_result.row_count, sql_result.execution_time_ms)

        return AskResponse(question=request.question, answer=answer,
                           sql_result=sql_result, session_id=session_id,
                           query_id=query_id, llm_model=gen_result.model, total_time_ms=total_ms)


async def _log_query(session, connection_id, session_id, question, sql,
                     success, error, model, rows=None, exec_ms=None) -> int:
    result = await session.execute(
        text("""
            INSERT INTO query_history
                (connection_id, session_id, question, generated_sql, was_successful,
                 error_message, rows_returned, execution_time_ms, llm_model_used)
            VALUES (:conn_id, :sess_id, :question, :sql, :success, :error, :rows, :exec_ms, :model)
            RETURNING id
        """),
        {"conn_id": connection_id, "sess_id": session_id, "question": question,
         "sql": sql, "success": success, "error": error, "rows": rows,
         "exec_ms": exec_ms, "model": model},
    )
    await session.commit()
    row = result.fetchone()
    return row[0] if row else -1
''')

# ---- core __init__ ----
touch("backend/app/core/__init__.py")

# ---- schema_introspector ----
write("backend/app/core/schema_introspector.py", '''\
"""DataPilot — PostgreSQL Schema Introspector"""
import logging
from dataclasses import dataclass, field
from typing import Any
import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    default_value: str | None
    is_primary_key: bool
    max_length: int | None = None


@dataclass
class ForeignKeyInfo:
    column: str
    referenced_table: str
    referenced_column: str
    constraint_name: str


@dataclass
class IndexInfo:
    name: str
    columns: list[str]
    is_unique: bool


@dataclass
class TableInfo:
    schema: str
    name: str
    full_name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    row_count: int = 0
    sample_rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def primary_keys(self) -> list[str]:
        return [col.name for col in self.columns if col.is_primary_key]

    def to_text_summary(self) -> str:
        lines = [f"Table: {self.full_name}", "Columns:"]
        for col in self.columns:
            pk = " [PK]" if col.is_primary_key else ""
            null = "" if col.is_nullable else " NOT NULL"
            lines.append(f"  - {col.name}: {col.data_type}{pk}{null}")
        if self.foreign_keys:
            lines.append("Relationships:")
            for fk in self.foreign_keys:
                lines.append(f"  - {self.full_name}.{fk.column} -> {fk.referenced_table}.{fk.referenced_column}")
        if self.sample_rows:
            lines.append(f"Sample data ({len(self.sample_rows)} rows):")
            for row in self.sample_rows[:3]:
                lines.append(f"  {row}")
        return "\\n".join(lines)


@dataclass
class SchemaInfo:
    database_name: str
    host: str
    tables: dict[str, TableInfo] = field(default_factory=dict)
    total_tables: int = 0

    def get_table_names(self) -> list[str]:
        return list(self.tables.keys())

    def to_compact_summary(self) -> str:
        lines = [f"Database: {self.database_name}", f"Total tables: {self.total_tables}", ""]
        for table in self.tables.values():
            col_list = ", ".join(
                f"{c.name}({c.data_type})" + (" [PK]" if c.is_primary_key else "")
                for c in table.columns
            )
            lines.append(f"{table.full_name}: {col_list}")
        return "\\n".join(lines)


class SchemaIntrospector:
    def __init__(self, connection_string: str, schemas_to_include: list[str] | None = None,
                 sample_rows_per_table: int = 3, skip_tables: list[str] | None = None):
        self.connection_string = connection_string
        self.schemas_to_include = schemas_to_include or ["public"]
        self.sample_rows_per_table = sample_rows_per_table
        self.skip_tables = set(skip_tables or [])

    def introspect(self) -> SchemaInfo:
        logger.info("Starting schema introspection")
        with self._connect() as conn:
            db_name = self._get_database_name(conn)
            host = self._get_host(conn)
            schema_info = SchemaInfo(database_name=db_name, host=host)
            table_names = self._get_table_names(conn)
            logger.info(f"Found {len(table_names)} tables")
            for schema, table in table_names:
                full_name = f"{schema}.{table}"
                if table in self.skip_tables or full_name in self.skip_tables:
                    continue
                t = TableInfo(schema=schema, name=table, full_name=full_name)
                t.columns = self._get_columns(conn, schema, table)
                t.foreign_keys = self._get_foreign_keys(conn, schema, table)
                t.indexes = self._get_indexes(conn, schema, table)
                t.row_count = self._get_row_count(conn, schema, table)
                if self.sample_rows_per_table > 0:
                    t.sample_rows = self._get_sample_rows(conn, schema, table, self.sample_rows_per_table)
                schema_info.tables[full_name] = t
                logger.debug(f"Introspected: {full_name} ({len(t.columns)} cols, {t.row_count} rows)")
            schema_info.total_tables = len(schema_info.tables)
        logger.info(f"Introspection complete: {schema_info.total_tables} tables")
        return schema_info

    def test_connection(self) -> tuple[bool, str]:
        try:
            with self._connect() as conn:
                db_name = self._get_database_name(conn)
            return True, f"Connected successfully to database \'{db_name}\'"
        except psycopg2.OperationalError as e:
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def _connect(self) -> PgConnection:
        conn = psycopg2.connect(self.connection_string)
        conn.set_session(readonly=True, autocommit=True)
        return conn

    def _get_database_name(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            return cur.fetchone()[0]

    def _get_host(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT inet_server_addr()")
            result = cur.fetchone()[0]
            return str(result) if result else "localhost"

    def _get_table_names(self, conn):
        placeholders = ",".join(["%s"] * len(self.schemas_to_include))
        query = f"""
            SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_type = \'BASE TABLE\' AND table_schema IN ({placeholders})
            ORDER BY table_schema, table_name
        """
        with conn.cursor() as cur:
            cur.execute(query, self.schemas_to_include)
            return cur.fetchall()

    def _get_columns(self, conn, schema, table):
        query = """
            SELECT c.column_name, c.data_type, c.is_nullable = \'YES\' AS is_nullable,
                c.column_default, c.character_maximum_length,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                    AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = \'PRIMARY KEY\' AND tc.table_schema = %s AND tc.table_name = %s
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, (schema, table, schema, table))
            rows = cur.fetchall()
        return [ColumnInfo(name=r["column_name"], data_type=r["data_type"],
                           is_nullable=r["is_nullable"], default_value=r["column_default"],
                           is_primary_key=r["is_primary_key"], max_length=r["character_maximum_length"])
                for r in rows]

    def _get_foreign_keys(self, conn, schema, table):
        query = """
            SELECT kcu.column_name, ccu.table_schema || \'.\' || ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = \'FOREIGN KEY\' AND tc.table_schema = %s AND tc.table_name = %s
        """
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, (schema, table))
            rows = cur.fetchall()
        return [ForeignKeyInfo(column=r["column_name"], referenced_table=r["referenced_table"],
                               referenced_column=r["referenced_column"], constraint_name=r["constraint_name"])
                for r in rows]

    def _get_indexes(self, conn, schema, table):
        query = """
            SELECT i.relname AS index_name, ix.indisunique AS is_unique,
                array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) AS columns
            FROM pg_catalog.pg_class t
            JOIN pg_catalog.pg_index ix ON t.oid = ix.indrelid
            JOIN pg_catalog.pg_class i ON i.oid = ix.indexrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE n.nspname = %s AND t.relname = %s AND t.relkind = \'r\'
            GROUP BY i.relname, ix.indisunique ORDER BY i.relname
        """
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, (schema, table))
            rows = cur.fetchall()
        return [IndexInfo(name=r["index_name"], columns=list(r["columns"]), is_unique=r["is_unique"])
                for r in rows]

    def _get_row_count(self, conn, schema, table):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT reltuples::bigint FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s
            """, (schema, table))
            result = cur.fetchone()
            if result and result[0] >= 0:
                return int(result[0])
            cur.execute(f\'SELECT COUNT(*) FROM "{schema}"."{table}"\')
            return cur.fetchone()[0]

    def _get_sample_rows(self, conn, schema, table, n):
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f\'SELECT * FROM "{schema}"."{table}" TABLESAMPLE BERNOULLI(1) LIMIT %s\', (n,))
                rows = cur.fetchall()
            if not rows:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(f\'SELECT * FROM "{schema}"."{table}" LIMIT %s\', (n,))
                    rows = cur.fetchall()
            return [{k: str(v) if v is not None else None for k, v in dict(row).items()} for row in rows]
        except Exception as e:
            logger.warning(f"Could not fetch sample rows for {schema}.{table}: {e}")
            return []
''')

# ---- embedding.py ----
write("backend/app/core/embedding.py", '''\
"""DataPilot — Schema Embedding Pipeline"""
import logging
from dataclasses import dataclass
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.schema_introspector import SchemaInfo

logger = logging.getLogger(__name__)


@dataclass
class SchemaChunk:
    connection_id: str
    table_full_name: str
    content: str
    embedding: list[float] | None = None


class EmbeddingClient:
    def __init__(self):
        self._client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model, input=texts, dimensions=self.dimensions)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class SchemaEmbeddingPipeline:
    def __init__(self, db_session: AsyncSession, embedding_client: EmbeddingClient | None = None):
        self.db = db_session
        self.embedder = embedding_client or EmbeddingClient()

    async def index_schema(self, connection_id: str, schema_info: SchemaInfo) -> int:
        chunks = [
            SchemaChunk(connection_id=connection_id, table_full_name=t.full_name, content=t.to_text_summary())
            for t in schema_info.tables.values()
        ]
        if not chunks:
            return 0
        embeddings = self.embedder.embed([c.content for c in chunks])
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        await self._upsert_embeddings(chunks)
        return len(chunks)

    async def search_relevant_tables(self, connection_id: str, question: str, top_k: int = 5) -> list[str]:
        query_embedding = self.embedder.embed_one(question)
        result = await self.db.execute(
            text("""
                SELECT content, 1 - (embedding <=> :query_vec::vector) AS similarity
                FROM schema_embeddings WHERE connection_id = :connection_id
                ORDER BY embedding <=> :query_vec::vector LIMIT :top_k
            """),
            {"query_vec": str(query_embedding), "connection_id": connection_id, "top_k": top_k},
        )
        return [row[0] for row in result.fetchall()]

    async def _upsert_embeddings(self, chunks: list[SchemaChunk]) -> None:
        for chunk in chunks:
            await self.db.execute(
                text("""
                    INSERT INTO schema_embeddings (connection_id, table_full_name, content, embedding)
                    VALUES (:connection_id, :table_full_name, :content, :embedding::vector)
                    ON CONFLICT (connection_id, table_full_name)
                    DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding, updated_at = NOW()
                """),
                {"connection_id": chunk.connection_id, "table_full_name": chunk.table_full_name,
                 "content": chunk.content, "embedding": str(chunk.embedding)},
            )
        await self.db.commit()
''')

# ---- llm.py ----
write("backend/app/core/llm.py", '''\
"""DataPilot — LLM Client"""
import logging
from abc import ABC, abstractmethod
import anthropic
import httpx
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str,
                 temperature: float = 0.0, max_tokens: int = 2048) -> str: ...
    @property
    @abstractmethod
    def model_name(self) -> str: ...


class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o"):
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
        response = self._client.chat.completions.create(
            model=self._model, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_message}])
        return response.choices[0].message.content or ""

    @property
    def model_name(self): return self._model


class AnthropicClient(LLMClient):
    def __init__(self, model: str = "claude-sonnet-4-5"):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
        response = self._client.messages.create(
            model=self._model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt, messages=[{"role": "user", "content": user_message}])
        return response.content[0].text

    @property
    def model_name(self): return self._model


class OllamaClient(LLMClient):
    def __init__(self, model: str = "llama3.1"):
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
        response = httpx.post(f"{self._base_url}/api/chat", timeout=120.0, json={
            "model": self._model, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_message}]})
        response.raise_for_status()
        return response.json()["message"]["content"]

    @property
    def model_name(self): return f"ollama/{self._model}"


def get_llm_client() -> LLMClient:
    provider, model = settings.llm_provider, settings.llm_model
    if provider == "openai": return OpenAIClient(model=model)
    if provider == "anthropic": return AnthropicClient(model=model)
    if provider == "ollama": return OllamaClient(model=model)
    raise ValueError(f"Unknown provider: {provider}")
''')

# ---- sql_generator.py ----
write("backend/app/core/sql_generator.py", '''\
"""DataPilot — Text-to-SQL Generator"""
import logging
import re
from app.core.llm import LLMClient
from app.utils.sql_parser import SQLParser

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are DataPilot, an expert PostgreSQL query generator.

Your job: Convert the user\'s natural language question into a single, correct, executable PostgreSQL SELECT query.

Rules:
1. Output ONLY the SQL query — no explanation, no markdown fences, no preamble
2. ONLY generate SELECT queries — never INSERT, UPDATE, DELETE, DROP, or any DDL
3. Always qualify column names with table aliases to avoid ambiguity
4. Add LIMIT {max_rows} unless the question asks for a count or aggregation
5. Use proper PostgreSQL syntax
6. If the question cannot be answered with the given schema, output exactly: CANNOT_ANSWER

Schema context:
{schema_context}
"""


class SQLGenerationResult:
    def __init__(self, sql, can_answer, raw_output, model, validation_error=None):
        self.sql = sql
        self.can_answer = can_answer
        self.raw_output = raw_output
        self.model = model
        self.validation_error = validation_error


class SQLGenerator:
    def __init__(self, llm_client: LLMClient, max_rows: int = 100):
        self.llm = llm_client
        self.max_rows = max_rows
        self.parser = SQLParser()

    def generate(self, question: str, schema_context: str) -> SQLGenerationResult:
        system_prompt = SYSTEM_PROMPT.format(schema_context=schema_context, max_rows=self.max_rows)
        raw_output = self.llm.complete(system_prompt=system_prompt, user_message=question, temperature=0.0)
        return self._parse_output(raw_output, question)

    def _parse_output(self, raw_output: str, question: str) -> SQLGenerationResult:
        sql = raw_output.strip()
        sql = re.sub(r"^```(?:sql)?\\n?", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\\n?```$", "", sql).strip()
        if sql.upper().startswith("CANNOT_ANSWER"):
            return SQLGenerationResult(sql=None, can_answer=False, raw_output=raw_output, model=self.llm.model_name)
        error = self.parser.validate_select_only(sql)
        if error:
            return SQLGenerationResult(sql=None, can_answer=False, raw_output=raw_output,
                                       model=self.llm.model_name, validation_error=error)
        return SQLGenerationResult(sql=sql, can_answer=True, raw_output=raw_output, model=self.llm.model_name)
''')

# ---- models ----
touch("backend/app/models/__init__.py")

write("backend/app/models/schemas.py", '''\
"""DataPilot — Pydantic API Schemas"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ConnectRequest(BaseModel):
    alias: str = Field(..., min_length=1, max_length=100)
    host: str
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    schemas: list[str] = Field(default=["public"])

    def to_connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class ConnectResponse(BaseModel):
    connection_id: str
    alias: str
    database_name: str
    total_tables: int
    tables: list[str]
    message: str


class ConnectionStatusResponse(BaseModel):
    connection_id: str
    alias: str
    host: str
    database_name: str
    total_tables: int
    schema_indexed: bool
    is_active: bool
    created_at: datetime


class AskOptions(BaseModel):
    max_rows: int = Field(default=100, ge=1, le=1000)
    include_sql: bool = True
    include_chart: bool = True
    include_insights: bool = True


class AskRequest(BaseModel):
    connection_id: str
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    options: AskOptions | None = None


class SQLResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    columns: list[str]
    execution_time_ms: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sql_result: SQLResult | None = None
    session_id: str
    query_id: int
    llm_model: str
    total_time_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    environment: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
''')

write("backend/app/models/database.py", '''\
"""DataPilot — SQLAlchemy ORM Models"""
import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DBConnection(Base):
    __tablename__ = "db_connections"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=5432)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_string_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schema_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_tables: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SchemaEmbedding(Base):
    __tablename__ = "schema_embeddings"
    __table_args__ = (UniqueConstraint("connection_id", "table_full_name", name="uq_connection_table"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("db_connections.id", ondelete="CASCADE"))
    table_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QueryHistory(Base):
    __tablename__ = "query_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("db_connections.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    was_successful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rows_returned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
''')

# ---- utils ----
touch("backend/app/utils/__init__.py")

write("backend/app/utils/sql_parser.py", '''\
"""DataPilot — SQL Safety Validator"""
import re

BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE",
    "REPLACE", "MERGE", "GRANT", "REVOKE", "EXECUTE", "EXEC", "CALL",
    "COPY", "VACUUM", "LOCK",
}


class SQLParser:
    def validate_select_only(self, sql: str) -> str | None:
        if not sql or not sql.strip():
            return "SQL is empty"
        normalized = self._normalize(sql)
        if not normalized.lstrip().startswith("SELECT"):
            return f"SQL must start with SELECT, got: {normalized[:50]}"
        words = set(re.findall(r"\\b([A-Z_]+)\\b", normalized))
        blocked = words & BLOCKED_KEYWORDS
        if blocked:
            return f"SQL contains blocked keywords: {blocked}"
        stripped = normalized.strip().rstrip(";")
        if ";" in stripped:
            return "SQL contains multiple statements"
        return None

    def extract_table_names(self, sql: str) -> list[str]:
        pattern = r"(?:FROM|JOIN)\\s+(?:\\"?[\\w]+"?\\.)?\\"?([\\w]+)\\"?"
        return list(set(re.findall(pattern, sql, re.IGNORECASE)))

    def _normalize(self, sql: str) -> str:
        sql = re.sub(r"--[^\\n]*", " ", sql)
        sql = re.sub(r"/\\*.*?\\*/", " ", sql, flags=re.DOTALL)
        return sql.upper()
''')

# ---- tests ----
touch("backend/tests/__init__.py")
touch("backend/tests/test_core/__init__.py")

write("backend/tests/test_core/test_schema_introspector.py", '''\
"""Tests for SchemaIntrospector"""
from app.core.schema_introspector import ColumnInfo, ForeignKeyInfo, TableInfo, SchemaInfo
from app.utils.sql_parser import SQLParser


class TestTableInfoTextSummary:
    def test_basic_summary(self):
        table = TableInfo(schema="public", name="bookings", full_name="public.bookings")
        table.columns = [
            ColumnInfo("id", "integer", False, None, True),
            ColumnInfo("guest_name", "character varying", False, None, False),
        ]
        summary = table.to_text_summary()
        assert "Table: public.bookings" in summary
        assert "id: integer [PK]" in summary

    def test_foreign_keys_in_summary(self):
        table = TableInfo(schema="public", name="bookings", full_name="public.bookings")
        table.columns = [ColumnInfo("property_id", "integer", False, None, False)]
        table.foreign_keys = [ForeignKeyInfo("property_id", "public.properties", "id", "fk")]
        summary = table.to_text_summary()
        assert "public.properties" in summary


class TestSQLParser:
    def setup_method(self):
        self.parser = SQLParser()

    def test_valid_select(self):
        assert self.parser.validate_select_only("SELECT id FROM users LIMIT 10") is None

    def test_insert_blocked(self):
        assert self.parser.validate_select_only("INSERT INTO users VALUES (1)") is not None

    def test_drop_blocked(self):
        assert self.parser.validate_select_only("SELECT 1; DROP TABLE users") is not None

    def test_empty_blocked(self):
        assert self.parser.validate_select_only("") is not None

    def test_created_at_not_blocked(self):
        assert self.parser.validate_select_only("SELECT created_at FROM bookings") is None
''')

write("backend/tests/test_core/test_sql_generator.py", '''\
"""Tests for SQLGenerator"""
from unittest.mock import MagicMock
from app.core.sql_generator import SQLGenerator


def make_generator(llm_output: str) -> SQLGenerator:
    mock_llm = MagicMock()
    mock_llm.complete.return_value = llm_output
    mock_llm.model_name = "mock-model"
    return SQLGenerator(llm_client=mock_llm, max_rows=100)


class TestSQLGenerator:
    def test_clean_sql(self):
        result = make_generator("SELECT id FROM users LIMIT 100").generate("Show users", "schema")
        assert result.can_answer is True
        assert "SELECT" in result.sql

    def test_strips_markdown(self):
        result = make_generator("```sql\\nSELECT * FROM users\\n```").generate("q", "schema")
        assert "```" not in result.sql

    def test_cannot_answer(self):
        result = make_generator("CANNOT_ANSWER").generate("q", "schema")
        assert result.can_answer is False

    def test_mutation_rejected(self):
        result = make_generator("DELETE FROM users").generate("q", "schema")
        assert result.can_answer is False
''')

# ---- CLI ----
write("backend/cli.py", '''\
"""DataPilot CLI — Test from the terminal"""
import json, sys
import click
import httpx

API_BASE = "http://localhost:8000"


@click.group()
def cli():
    """DataPilot CLI"""
    pass


@cli.command()
@click.option("--host", required=True)
@click.option("--port", default=5432)
@click.option("--db", required=True)
@click.option("--user", required=True)
@click.option("--password", required=True, prompt=True, hide_input=True)
@click.option("--alias", default="My Database")
@click.option("--schemas", default="public")
def connect(host, port, db, user, password, alias, schemas):
    """Connect and introspect a PostgreSQL database."""
    click.echo(f"\\n🔌 Connecting to {host}:{port}/{db}...")
    payload = {"host": host, "port": port, "database": db, "username": user,
               "password": password, "alias": alias, "schemas": schemas.split(",")}
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{API_BASE}/connect", json=payload)
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\\n✅ Connected!")
        click.echo(f"   Connection ID : {data[\'connection_id\']}")
        click.echo(f"   Tables found  : {data[\'total_tables\']}")
        click.echo(f"\\n💡 Save this ID: {data[\'connection_id\']}")
    else:
        click.echo(f"\\n❌ Failed: {response.json().get(\'detail\', response.text)}")
        sys.exit(1)


@cli.command()
@click.option("--connection-id", required=True)
@click.option("--max-rows", default=10)
@click.argument("question")
def ask(connection_id, max_rows, question):
    """Ask a question about your database."""
    click.echo(f"\\n🤔 {question}\\n")
    payload = {"connection_id": connection_id, "question": question,
               "options": {"max_rows": max_rows, "include_sql": True}}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{API_BASE}/ask", json=payload)
    if response.status_code == 200:
        data = response.json()
        click.echo(f"💬 {data[\'answer\']}")
        if data.get("sql_result"):
            click.echo(f"\\n📝 SQL: {data[\'sql_result\'][\'sql\']}")
            rows = data["sql_result"]["rows"]
            if rows:
                click.echo(f"\\n📊 Results:")
                for row in rows[:10]:
                    click.echo(f"   {row}")
    else:
        click.echo(f"\\n❌ {response.json().get(\'detail\', response.text)}")


@cli.command()
@click.option("--connection-id", required=True)
def repl(connection_id):
    """Interactive question mode."""
    click.echo(f"\\n🚀 DataPilot REPL | connection: {connection_id}")
    click.echo("   Type a question, or \\'quit\\' to exit.\\n")
    session_id = None
    while True:
        try:
            question = click.prompt("You")
        except (click.Abort, EOFError):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        payload = {"connection_id": connection_id, "question": question,
                   "session_id": session_id, "options": {"max_rows": 20}}
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{API_BASE}/ask", json=payload)
        if r.status_code == 200:
            data = r.json()
            session_id = data.get("session_id")
            click.echo(f"\\nDataPilot: {data[\'answer\']}")
            if data.get("sql_result"):
                click.echo(f"SQL: {data[\'sql_result\'][\'sql\']}")
            click.echo()
        else:
            click.echo(f"\\n❌ {r.json().get(\'detail\', r.text)}\\n")
    click.echo("Goodbye! 👋")


@cli.command()
def health():
    """Check if the API is running."""
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5.0)
        data = r.json()
        click.echo(f"✅ API is running | status={data[\'status\']} | env={data[\'environment\']}")
    except Exception as e:
        click.echo(f"❌ API not reachable: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
''')

print("\n" + "="*50)
print("✅ ALL FILES CREATED SUCCESSFULLY!")
print("="*50)
print("""
Next steps — run these commands one at a time:

1. Copy .env.example to .env and add your OpenAI key:
   Windows: copy .env.example .env
   Then open .env in Notepad and set OPENAI_API_KEY=sk-...

2. Start the database:
   docker-compose up postgres redis -d

3. Initialize DataPilot's internal tables:
   docker-compose exec postgres psql -U datapilot -d datapilot < backend/init_db.sql

4. Install Python packages:
   cd backend
   pip install -r requirements.txt

5. Start the API:
   uvicorn app.main:app --reload

6. Open in browser:
   http://localhost:8000/docs

That's it! 🚀
""")
