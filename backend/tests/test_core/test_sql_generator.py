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
        result = make_generator("```sql\nSELECT * FROM users\n```").generate("q", "schema")
        assert "```" not in result.sql

    def test_cannot_answer(self):
        result = make_generator("CANNOT_ANSWER").generate("q", "schema")
        assert result.can_answer is False

    def test_mutation_rejected(self):
        result = make_generator("DELETE FROM users").generate("q", "schema")
        assert result.can_answer is False
