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

    loop = asyncio.get_running_loop()
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
