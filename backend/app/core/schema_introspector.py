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
        return "\n".join(lines)


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
        return "\n".join(lines)


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
            return True, f"Connected successfully to database '{db_name}'"
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
            WHERE table_type = 'BASE TABLE' AND table_schema IN ({placeholders})
            ORDER BY table_schema, table_name
        """
        with conn.cursor() as cur:
            cur.execute(query, self.schemas_to_include)
            return cur.fetchall()

    def _get_columns(self, conn, schema, table):
        query = """
            SELECT c.column_name, c.data_type, c.is_nullable = 'YES' AS is_nullable,
                c.column_default, c.character_maximum_length,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                    AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = %s AND tc.table_name = %s
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
            SELECT kcu.column_name, ccu.table_schema || '.' || ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s AND tc.table_name = %s
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
            WHERE n.nspname = %s AND t.relname = %s AND t.relkind = 'r'
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
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            return cur.fetchone()[0]

    def _get_sample_rows(self, conn, schema, table, n):
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{schema}"."{table}" TABLESAMPLE BERNOULLI(1) LIMIT %s', (n,))
                rows = cur.fetchall()
            if not rows:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT %s', (n,))
                    rows = cur.fetchall()
            return [{k: str(v) if v is not None else None for k, v in dict(row).items()} for row in rows]
        except Exception as e:
            logger.warning(f"Could not fetch sample rows for {schema}.{table}: {e}")
            return []
