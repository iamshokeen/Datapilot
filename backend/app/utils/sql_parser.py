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
        if not normalized.lstrip().startswith(("SELECT", "WITH")):
            return f"SQL must start with SELECT, got: {normalized[:50]}"
        words = set(re.findall(r"\b([A-Z_]+)\b", normalized))
        blocked = words & BLOCKED_KEYWORDS
        if blocked:
            return f"SQL contains blocked keywords: {blocked}"
        stripped = normalized.strip().rstrip(";")
        if ";" in stripped:
            return "SQL contains multiple statements"
        return None

    def extract_table_names(self, sql: str) -> list[str]:
        pattern = r"(?:FROM|JOIN)\s+(?:\w+\.)?\w+"
        matches = re.findall(pattern, sql, re.IGNORECASE)
        tables = []
        for match in matches:
            parts = match.strip().split()
            if len(parts) >= 2:
                table = parts[-1].replace('"', '').split('.')[-1]
                tables.append(table)
        return list(set(tables))

    def _normalize(self, sql: str) -> str:
        sql = re.sub(r"--[^\n]*", " ", sql)
        sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
        return sql.upper()
