"""Storage backends for DevAssist."""

import json
import os
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from devassist.db.models import Brief


class Storage(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_brief(self, brief: Brief) -> str:
        """Save a brief and return its ID."""
        ...
    
    @abstractmethod
    def get_brief(self, brief_id: str) -> Brief | None:
        """Get a brief by ID."""
        ...
    
    @abstractmethod
    def get_latest_brief(self, user_id: str) -> Brief | None:
        """Get the most recent brief for a user."""
        ...
    
    @abstractmethod
    def list_briefs(self, user_id: str, limit: int = 10) -> list[Brief]:
        """List recent briefs for a user."""
        ...


class SQLiteStorage(Storage):
    """SQLite storage backend (good for local/dev)."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.path.expanduser("~/.devassist/briefs.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS briefs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    summary TEXT,
                    items TEXT,
                    sources_used TEXT,
                    raw_response TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_briefs_user_created 
                ON briefs(user_id, created_at DESC)
            """)
    
    def save_brief(self, brief: Brief) -> str:
        brief_id = brief.id or str(uuid.uuid4())
        brief.id = brief_id
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO briefs 
                (id, user_id, created_at, summary, items, sources_used, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                brief_id,
                brief.user_id,
                brief.created_at.isoformat(),
                brief.summary,
                json.dumps([item.to_dict() for item in brief.items]),
                json.dumps(brief.sources_used),
                brief.raw_response,
            ))
        
        return brief_id
    
    def get_brief(self, brief_id: str) -> Brief | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM briefs WHERE id = ?", (brief_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_brief(row)
    
    def get_latest_brief(self, user_id: str) -> Brief | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM briefs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_brief(row)
    
    def list_briefs(self, user_id: str, limit: int = 10) -> list[Brief]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM briefs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            
            return [self._row_to_brief(row) for row in rows]
    
    def _row_to_brief(self, row: sqlite3.Row) -> Brief:
        return Brief.from_dict({
            "id": row["id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "summary": row["summary"],
            "items": json.loads(row["items"] or "[]"),
            "sources_used": json.loads(row["sources_used"] or "[]"),
            "raw_response": row["raw_response"],
        })


class PostgresStorage(Storage):
    """PostgreSQL storage backend (good for production/OpenShift)."""
    
    def __init__(self, connection_string: str | None = None):
        self.connection_string = connection_string or os.environ.get(
            "DATABASE_URL",
            "postgresql://localhost/devassist"
        )
        self._pool = None
    
    def _get_connection(self) -> Any:
        """Get a database connection."""
        try:
            import psycopg2
            return psycopg2.connect(self.connection_string)
        except ImportError:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary")
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS briefs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        summary TEXT,
                        items JSONB,
                        sources_used JSONB,
                        raw_response TEXT
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_briefs_user_created 
                    ON briefs(user_id, created_at DESC)
                """)
            conn.commit()
    
    def save_brief(self, brief: Brief) -> str:
        brief_id = brief.id or str(uuid.uuid4())
        brief.id = brief_id
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO briefs 
                    (id, user_id, created_at, summary, items, sources_used, raw_response)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        items = EXCLUDED.items,
                        sources_used = EXCLUDED.sources_used,
                        raw_response = EXCLUDED.raw_response
                """, (
                    brief_id,
                    brief.user_id,
                    brief.created_at,
                    brief.summary,
                    json.dumps([item.to_dict() for item in brief.items]),
                    json.dumps(brief.sources_used),
                    brief.raw_response,
                ))
            conn.commit()
        
        return brief_id
    
    def get_brief(self, brief_id: str) -> Brief | None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM briefs WHERE id = %s", (brief_id,))
                row = cur.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_brief(row, cur.description)
    
    def get_latest_brief(self, user_id: str) -> Brief | None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM briefs WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                row = cur.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_brief(row, cur.description)
    
    def list_briefs(self, user_id: str, limit: int = 10) -> list[Brief]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM briefs WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (user_id, limit)
                )
                rows = cur.fetchall()
                
                return [self._row_to_brief(row, cur.description) for row in rows]
    
    def _row_to_brief(self, row: tuple, description: Any) -> Brief:
        cols = [col.name for col in description]
        data = dict(zip(cols, row))
        
        return Brief.from_dict({
            "id": str(data["id"]),
            "user_id": data["user_id"],
            "created_at": data["created_at"].isoformat() if data["created_at"] else None,
            "summary": data["summary"],
            "items": data["items"] or [],
            "sources_used": data["sources_used"] or [],
            "raw_response": data["raw_response"],
        })


def get_storage() -> Storage:
    """Get the configured storage backend."""
    backend = os.environ.get("DEVASSIST_STORAGE", "sqlite")
    
    if backend == "postgres":
        storage = PostgresStorage()
        storage._init_db()
        return storage
    else:
        return SQLiteStorage()
