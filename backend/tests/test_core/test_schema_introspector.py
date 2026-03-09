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
