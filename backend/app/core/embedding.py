"""DataPilot — Schema Embedding Pipeline"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.schema_introspector import SchemaInfo

logger = logging.getLogger(__name__)


def _get_openai_key() -> str:
    """Get OpenAI key from settings, env var, or .env file directly."""
    # 1. Try pydantic settings first
    if settings.openai_api_key:
        return settings.openai_api_key

    # 2. Try environment variable directly
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key

    # 3. Walk up from this file to find .env and parse it manually
    search_dirs = [
        Path(__file__).parent,                    # app/core/
        Path(__file__).parent.parent,             # app/
        Path(__file__).parent.parent.parent,      # backend/
        Path(__file__).parent.parent.parent.parent,  # datapilot/
    ]
    for d in search_dirs:
        env_file = d / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        logger.info(f"Loaded OPENAI_API_KEY from {env_file}")
                        return key

    logger.warning("OPENAI_API_KEY not found — embeddings will fail")
    return ""


@dataclass
class SchemaChunk:
    connection_id: str
    table_full_name: str
    content: str
    embedding: list[float] | None = None


class EmbeddingClient:
    def __init__(self):
        api_key = _get_openai_key()
        self._client = OpenAI(api_key=api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    @staticmethod
    def _truncate(text: str, max_chars: int = 6000) -> str:
        """Truncate to avoid exceeding embedding model token limit (~8192 tokens).
        6000 chars ≈ 1500-2000 tokens, safely under the 8192 token limit."""
        return text[:max_chars] if len(text) > max_chars else text

    def embed(self, texts: list[str]) -> list[list[float]]:
        texts = [self._truncate(t) for t in texts]
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self.model, input=texts, dimensions=self.dimensions
        )
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class SchemaEmbeddingPipeline:
    def __init__(self, db_session: AsyncSession, embedding_client: EmbeddingClient | None = None):
        self.db = db_session
        self.embedder = embedding_client or EmbeddingClient()

    async def index_schema(self, connection_id: str, schema_info: SchemaInfo) -> int:
        chunks = [
            SchemaChunk(
                connection_id=connection_id,
                table_full_name=t.full_name,
                content=t.to_text_summary(),
            )
            for t in schema_info.tables.values()
        ]
        if not chunks:
            return 0
        embeddings = self.embedder.embed([c.content for c in chunks])
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        await self._upsert_embeddings(chunks)
        return len(chunks)

    async def search_relevant_tables(
        self, connection_id: str, question: str, top_k: int = 5
    ) -> list[str]:
        query_embedding = self.embedder.embed_one(question)
        result = await self.db.execute(
            text("""
                SELECT content, 1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                FROM schema_embeddings WHERE connection_id = :connection_id
                ORDER BY embedding <=> CAST(:query_vec AS vector) LIMIT :top_k
            """),
            {
                "query_vec": str(query_embedding),
                "connection_id": connection_id,
                "top_k": top_k,
            },
        )
        return [row[0] for row in result.fetchall()]

    async def _upsert_embeddings(self, chunks: list[SchemaChunk]) -> None:
        for chunk in chunks:
            await self.db.execute(
                text("""
                    INSERT INTO schema_embeddings (connection_id, table_full_name, content, embedding)
                    VALUES (:connection_id, :table_full_name, :content, CAST(:embedding AS vector))
                    ON CONFLICT (connection_id, table_full_name)
                    DO UPDATE SET content = EXCLUDED.content,
                                  embedding = EXCLUDED.embedding,
                                  updated_at = NOW()
                """),
                {
                    "connection_id": chunk.connection_id,
                    "table_full_name": chunk.table_full_name,
                    "content": chunk.content,
                    "embedding": str(chunk.embedding),
                },
            )
        await self.db.commit()

