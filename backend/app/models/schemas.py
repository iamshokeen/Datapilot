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
