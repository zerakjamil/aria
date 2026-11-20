import asyncio
import uuid
import json
import httpx
from typing import Optional
from src.config import (
    OLLAMA_URL,
    MODEL_NAME,
    COMPACTION_DEBOUNCE_SECONDS,
)
from src.token_budgeter import get_compaction_generation_options
from src.db import get_db, insert_message, upsert_user_profile

class PriorityCompactor:
    def __init__(self):
        self._pending_task: Optional[asyncio.Task] = None
        self._inflight_compaction_task: Optional[asyncio.Task] = None
        self._user_lock = asyncio.Lock()
        self._active_http_client: Optional[httpx.AsyncClient] = None

    async def acquire_user_turn(self):
        """
        Acquired by the user chat handler.
        Pre-emptively cancels any pending or active in-flight compaction task
        to guarantee zero GPU queue contention on Ollama single-worker pipeline.
        """
        # 1. Cancel pending debounce timer
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
            self._pending_task = None
            
        # 2. Pre-emptively abort in-flight compaction HTTP request
        if self._inflight_compaction_task and not self._inflight_compaction_task.done():
            self._inflight_compaction_task.cancel()
            self._inflight_compaction_task = None
            
        if self._active_http_client:
            try:
                await self._active_http_client.aclose()
            except Exception:
                pass
            self._active_http_client = None

    def schedule_compaction(self, conversation_id: str):
        """
        Schedules compaction guarded by a 30-second conversational inactivity debounce.
        """
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
            
        self._pending_task = asyncio.create_task(self._debounced_compaction_worker(conversation_id))

    async def _debounced_compaction_worker(self, conversation_id: str):
        try:
            # Debounce idle wait
            await asyncio.sleep(COMPACTION_DEBOUNCE_SECONDS)
            # Launch active compaction
            self._inflight_compaction_task = asyncio.create_task(self._execute_compaction(conversation_id))
            await self._inflight_compaction_task
        except asyncio.CancelledError:
            pass # Reset cleanly when pre-empted by user
        finally:
            self._pending_task = None
            self._inflight_compaction_task = None

    async def _execute_compaction(self, conversation_id: str):
        async with get_db() as db:
            # Query oldest 1,000 tokens of non-quarantined dialogue
            cursor = await db.execute(
                """
                SELECT id, role, content, token_count
                FROM messages
                WHERE conversation_id = ? AND is_quarantined = 0
                ORDER BY created_at ASC
                LIMIT 10
                """,
                (conversation_id,)
            )
            turns = await cursor.fetchall()
            
        if len(turns) < 4:
            return # Insufficient turns to warrant compaction
            
        dialogue_text = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in turns)
        
        distillation_prompt = (
            "You are an analytical memory archivist. Summarize the following dialogue into structured JSON.\n"
            "Extract:\n"
            "1. 'distilled_facts': Key life facts, preferences, emotional milestones.\n"
            "2. 'commitments': Any tasks, promises, or goals mentioned.\n"
            "3. 'checkpoint': The current project or emotional state.\n\n"
            f"DIALOGUE:\n{dialogue_text}\n\n"
            "Format strictly as JSON with keys 'distilled_facts' (string), 'commitments' (list of strings), 'project_topic' (string), 'task_status' (string), 'next_action' (string), 'emotional_state' (string)."
        )
        
        payload = {
            "model": MODEL_NAME,
            "prompt": distillation_prompt,
            "stream": False,
            "format": "json",
            "options": get_compaction_generation_options()
        }
        
        self._active_http_client = httpx.AsyncClient(timeout=60.0)
        try:
            resp = await self._active_http_client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_json = data.get("response", "{}")
                parsed = json.loads(raw_json)
                
                summary_id = f"sum_{uuid.uuid4().hex[:12]}"
                distilled_facts = parsed.get("distilled_facts", "")
                commitments = json.dumps(parsed.get("commitments", []))
                
                async with get_db() as db:
                    # Commit to summaries
                    await db.execute(
                        """
                        INSERT INTO summaries (id, conversation_id, time_window_start, time_window_end, distilled_facts, commitments_json)
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
                        """,
                        (summary_id, conversation_id, distilled_facts, commitments)
                    )
                    
                    # Record checkpoint if project state identified
                    if parsed.get("project_topic"):
                        cp_id = f"cp_{uuid.uuid4().hex[:12]}"
                        await db.execute(
                            """
                            INSERT INTO checkpoints (id, conversation_id, project_topic, task_status, next_action, emotional_state)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cp_id,
                                conversation_id,
                                str(parsed.get("project_topic", "Personal")),
                                str(parsed.get("task_status", "in_progress")),
                                str(parsed.get("next_action", "")),
                                str(parsed.get("emotional_state", "neutral")),
                            )
                        )
                    await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass # Keep execution resilient
        finally:
            if self._active_http_client:
                await self._active_http_client.aclose()
                self._active_http_client = None

compactor = PriorityCompactor()
