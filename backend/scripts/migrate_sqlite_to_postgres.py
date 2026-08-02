from __future__ import annotations
import argparse
import ast
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
from dotenv import load_dotenv
from sqlalchemy import text
BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
from app.models.database import Base, engine
from app.models import User, Conversation, Message, Document
from app.models.custom_agent import CustomAgent
TABLE_CONFIGS: Sequence[Dict[str, Any]] = (
    {
        "name": "users",
        "columns": [
            "id",
            "username",
            "email",
            "hashed_password",
            "is_active",
            "is_admin",
            "role",
            "created_at",
            "last_login",
        ],
        "bool_fields": {"is_active", "is_admin"},
        "json_fields": set(),
    },
    {
        "name": "conversations",
        "columns": ["id", "user_id", "title", "created_at", "updated_at"],
        "bool_fields": set(),
        "json_fields": set(),
    },
    {
        "name": "messages",
        "columns": [
            "id",
            "conversation_id",
            "content",
            "is_user",
            "created_at",
            "context_used",
            "model_name",
        ],
        "bool_fields": {"is_user"},
        "json_fields": set(),
    },
    {
        "name": "documents",
        "columns": [
            "id",
            "filename",
            "content",
            "file_type",
            "uploaded_by",
            "created_at",
            "is_processed",
        ],
        "bool_fields": {"is_processed"},
        "json_fields": set(),
    },
    {
        "name": "custom_agents",
        "columns": [
            "id",
            "name",
            "role",
            "expertise",
            "prompt",
            "tools",
            "is_public",
            "created_by",
        ],
        "bool_fields": {"is_public"},
        "json_fields": {"tools"},
    },
)
def _normalize_bool(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n"}:
            return False
    return bool(value)
def _normalize_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, int, float, bool)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            parsed = json.loads(stripped)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, (dict, list, int, float, bool, str)):
                return json.dumps(parsed, ensure_ascii=False)
        except (ValueError, SyntaxError):
            pass
        return json.dumps(stripped, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)
def _sqlite_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]
def _read_sqlite_rows(
    conn: sqlite3.Connection,
    table_name: str,
    wanted_columns: Sequence[str],
) -> List[Dict[str, Any]]:
    available = set(_sqlite_table_columns(conn, table_name))
    if not available:
        return []
    selectable = [col for col in wanted_columns if col in available]
    if not selectable:
        return []
    sql = f"SELECT {', '.join(selectable)} FROM {table_name}"
    rows = conn.execute(sql).fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        item = {key: row[key] for key in selectable}
        for missing_col in wanted_columns:
            item.setdefault(missing_col, None)
        result.append(item)
    return result
def _normalize_row(row: Dict[str, Any], bool_fields: set[str], json_fields: set[str]) -> Dict[str, Any]:
    normalized = dict(row)
    for field in bool_fields:
        normalized[field] = _normalize_bool(normalized.get(field))
    for field in json_fields:
        normalized[field] = _normalize_json(normalized.get(field))
    return normalized
def ensure_target_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS model_name VARCHAR"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_uploaded_by ON documents (uploaded_by)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_custom_agents_created_by ON custom_agents (created_by)"))
def _upsert_many(
    table_name: str,
    columns: Sequence[str],
    rows: List[Dict[str, Any]],
    json_fields: set[str],
) -> None:
    if not rows:
        return
    insert_cols = ", ".join(columns)
    bind_cols = ", ".join(
        f"CAST(:{col} AS JSON)" if col in json_fields else f":{col}"
        for col in columns
    )
    update_cols = [col for col in columns if col != "id"]
    update_stmt = ", ".join(f"{col}=EXCLUDED.{col}" for col in update_cols)
    sql = text(
        f"""
        INSERT INTO {table_name} ({insert_cols})
        VALUES ({bind_cols})
        ON CONFLICT (id) DO UPDATE SET
        {update_stmt}
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, rows)
def _reset_sequences(table_names: Iterable[str]) -> None:
    with engine.begin() as conn:
        for table_name in table_names:
            conn.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                        (SELECT COUNT(*) > 0 FROM {table_name})
                    )
                    """
                )
            )
def _target_count(table_name: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
def migrate(source_sqlite: Path, dry_run: bool = False, skip_schema: bool = False) -> None:
    if not source_sqlite.exists():
        raise FileNotFoundError(f"找不到 SQLite 檔案: {source_sqlite}")
    backend_name = engine.url.get_backend_name()
    if backend_name != "postgresql":
        raise RuntimeError(
            f"目前 DATABASE_URL 後端為 {backend_name}，請先切到 PostgreSQL 再遷移。"
        )
    print("=== DB Migration: SQLite -> PostgreSQL ===")
    print(f"Source SQLite : {source_sqlite}")
    print(f"Target DB URL : {engine.url.render_as_string(hide_password=True)}")
    print(f"Dry run       : {dry_run}")
    print()
    if not skip_schema:
        ensure_target_schema()
        print("✅ 已完成 target schema 檢查/補強")
    else:
        print("⏭️  略過 target schema 檢查/補強")
    sqlite_conn = sqlite3.connect(source_sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        for config in TABLE_CONFIGS:
            table_name = config["name"]
            columns = config["columns"]
            bool_fields = config["bool_fields"]
            json_fields = config["json_fields"]
            src_rows = _read_sqlite_rows(sqlite_conn, table_name, columns)
            normalized_rows = [
                _normalize_row(row, bool_fields=bool_fields, json_fields=json_fields)
                for row in src_rows
            ]
            if dry_run:
                print(f"[DRY-RUN] {table_name}: source={len(normalized_rows)} (未寫入)")
                continue
            _upsert_many(table_name, columns, normalized_rows, json_fields)
            tgt_count = _target_count(table_name)
            print(f"✅ {table_name}: migrated={len(normalized_rows)}, target_total={tgt_count}")
        if not dry_run:
            _reset_sequences(config["name"] for config in TABLE_CONFIGS)
            print("✅ sequences 已同步到最新 ID")
    finally:
        sqlite_conn.close()
    print("\n🎉 資料遷移完成")
def main() -> None:
    parser = argparse.ArgumentParser(description="將 SQLite 舊資料遷移到 PostgreSQL")
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_ROOT / "chatbot.db",
        help="來源 SQLite 檔案路徑（預設: backend/chatbot.db）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只讀取與檢查，不寫入 PostgreSQL",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="跳過 schema 補強（僅在你已確認 schema 完整時使用）",
    )
    args = parser.parse_args()
    migrate(source_sqlite=args.source, dry_run=args.dry_run, skip_schema=args.skip_schema)
if __name__ == "__main__":
    main()
