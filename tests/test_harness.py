import pytest
import asyncio
from src.token_budgeter import (
    compile_budgeted_prompt,
    estimate_tokens,
    get_chat_generation_options,
    get_compaction_generation_options,
    BUDGET_SYSTEM_PERSONA,
    COMPACTION_THRESHOLD_TOKENS,
)
from src.guardrails import (
    inspect_crisis_intervention,
    sanitize_response_length,
)
from src.db import (
    init_db,
    ensure_conversation,
    insert_message,
    get_active_messages,
    get_db,
)

@pytest.mark.asyncio
async def test_sqlite_schema_and_triggers(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_companion.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db_path)
    
    await init_db()
    
    async with get_db() as db:
        # Verify WAL mode
        cursor = await db.execute("PRAGMA journal_mode;")
        row = await cursor.fetchone()
        assert row[0].lower() == "wal"
        
        # Verify recursive triggers
        cursor = await db.execute("PRAGMA recursive_triggers;")
        row = await cursor.fetchone()
        assert row[0] == 1
        
    # Test conversation insert and message triggers
    conv_id = "test_conv_1"
    await ensure_conversation(conv_id, "Test Run")
    
    # 1. Normal message should be inserted into messages_fts
    await insert_message("msg_1", conv_id, "user", "I want to start an AI company", 8, is_quarantined=0)
    
    async with get_db() as db:
        cursor = await db.execute("SELECT content FROM messages_fts WHERE message_id = 'msg_1'")
        row = await cursor.fetchone()
        assert row is not None
        assert "start an AI company" in row["content"]
        
    # 2. Quarantined crisis message should NOT enter messages_fts
    await insert_message("msg_crisis", conv_id, "system_crisis", "Call 988 lifeline", 6, is_quarantined=1)
    
    async with get_db() as db:
        cursor = await db.execute("SELECT content FROM messages_fts WHERE message_id = 'msg_crisis'")
        row = await cursor.fetchone()
        assert row is None # Quarantined!
        
    # 3. Test cascading delete triggers messages_ad to clean messages_fts
    async with get_db() as db:
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.commit()
        
        cursor = await db.execute("SELECT count(*) FROM messages_fts")
        row = await cursor.fetchone()
        assert row[0] == 0 # Pruned automatically via cascade & recursive trigger!

def test_token_budget_bounds():
    options = get_chat_generation_options()
    assert options["num_ctx"] == 4096
    assert options["num_predict"] == 150
    
    compact_opts = get_compaction_generation_options()
    assert compact_opts["num_ctx"] == 4096
    assert compact_opts["num_predict"] == 400

def test_crisis_intervention_safeguard():
    distress_msg = "I am suicidal and have no reason to live anymore"
    is_crisis, referral = inspect_crisis_intervention(distress_msg)
    assert is_crisis is True
    assert "988" in referral
    assert "Lifeline" in referral
    
    casual_msg = "Just scrolling through TikTok after a long day"
    is_crisis_2, _ = inspect_crisis_intervention(casual_msg)
    assert is_crisis_2 is False

def test_sentence_length_governor():
    verbose = "Sentence one is here. Sentence two follows this one. Sentence three provides detail. Sentence four is too long and should be trimmed."
    sanitized = sanitize_response_length(verbose)
    assert sanitized.count(".") <= 3
