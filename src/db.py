import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any, Optional
from src.config import DATABASE_PATH

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
PRAGMA recursive_triggers = ON;

-- Conversations metadata
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    summary_id TEXT
);

-- Individual conversational turns
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'system_crisis')),
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    is_quarantined INTEGER DEFAULT 0, -- 1 = crisis intervention; excluded from memory/compaction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- Full-text search virtual table for episodic retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    message_id UNINDEXED,
    content,
    tokenize = 'porter unicode61'
);

-- Automatic FTS5 synchronization triggers (excluding quarantined crisis records)
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages WHEN new.is_quarantined = 0 BEGIN
    INSERT INTO messages_fts(message_id, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE message_id = old.id;
END;

-- Dense vector embeddings for CPU-side ONNX semantic retrieval (NumPy dot product)
CREATE TABLE IF NOT EXISTS message_embeddings (
    message_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL, -- 384-dimensional float32 vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- Persistent facts, user profile, and core life ambitions
CREATE TABLE IF NOT EXISTS user_profile (
    key TEXT PRIMARY KEY,
    category TEXT NOT NULL, -- 'ambition', 'habit', 'preference', 'boundary'
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    last_confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compacted historical memory nodes
CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    distilled_facts TEXT NOT NULL,
    commitments_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Session recovery checkpoints
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    project_topic TEXT NOT NULL,
    task_status TEXT NOT NULL,      -- 'in_progress', 'paused', 'unfinished'
    next_action TEXT NOT NULL,
    emotional_state TEXT NOT NULL,  -- 'tired', 'motivated', 'overwhelmed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
"""

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA recursive_triggers = ON;")
        await conn.execute("PRAGMA busy_timeout = 5000;")
        yield conn

async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()

async def ensure_conversation(conversation_id: str, title: str = "Personal Journal") -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO conversations (id, title, last_active_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET last_active_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, title)
        )
        await db.commit()

async def insert_message(
    msg_id: str,
    conversation_id: str,
    role: str,
    content: str,
    token_count: int,
    is_quarantined: int = 0
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, token_count, is_quarantined)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, conversation_id, role, content, token_count, is_quarantined)
        )
        await db.execute(
            "UPDATE conversations SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        await db.commit()

async def get_active_messages(conversation_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, role, content, token_count, is_quarantined, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_total_active_tokens(conversation_id: str) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(token_count), 0) FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

async def get_latest_checkpoint() -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, conversation_id, project_topic, task_status, next_action, emotional_state, created_at
            FROM checkpoints
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def save_checkpoint(
    cp_id: str,
    conversation_id: str,
    project_topic: str,
    task_status: str,
    next_action: str,
    emotional_state: str
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO checkpoints (id, conversation_id, project_topic, task_status, next_action, emotional_state)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cp_id, conversation_id, project_topic, task_status, next_action, emotional_state)
        )
        await db.commit()

async def get_user_profile() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT key, category, value, confidence FROM user_profile")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def upsert_user_profile(key: str, category: str, value: str, confidence: float = 1.0) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO user_profile (key, category, value, confidence, last_confirmed_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                category = excluded.category,
                value = excluded.value,
                confidence = excluded.confidence,
                last_confirmed_at = CURRENT_TIMESTAMP
            """,
            (key, category, value, confidence)
        )
        await db.commit()
