import uuid
import json
import httpx
import asyncio
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.config import (
    OLLAMA_URL,
    MODEL_NAME,
    STATIC_DIR,
    COMPACTION_THRESHOLD_TOKENS,
)
from src.db import (
    init_db,
    ensure_conversation,
    insert_message,
    get_active_messages,
    get_total_active_tokens,
    get_latest_checkpoint,
    get_user_profile,
    upsert_user_profile,
    insert_audit_log,
)
from src.token_budgeter import (
    compile_budgeted_prompt,
    estimate_tokens,
    get_chat_generation_options,
)
from src.retriever import retrieve_episodic_memories
from src.guardrails import (
    BASE_PERSONALITY_PROMPT,
    TECHNICAL_COPILOT_PROMPT,
    select_personality_prompt,
    parse_persona,
    inspect_crisis_intervention,
    is_within_quiet_hours,
    sanitize_response_length,
)
from src.compactor import compactor
from src.tools import default_tools
from src.agent_loop import agent_loop, AgentTaskResult

app = FastAPI(title="Sovereign AI Personal Companion", version="1.0.0")

class ChatRequest(BaseModel):
    conversation_id: str = "conv_default"
    message: str
    stream: bool = True

class ExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None

class AgentTaskRequest(BaseModel):
    task: str
    required_slots: Optional[List[str]] = None

class CheckinRequest(BaseModel):
    conversation_id: str = "conv_default"

class FeedbackRequest(BaseModel):
    conversation_id: str = "conv_default"
    message_id: str
    thumb: str  # "up" or "down"
    prompt: Optional[str] = None
    response: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    await init_db()
    profiles = await get_user_profile()
    if not profiles:
        await upsert_user_profile("ambition_startup", "ambition", "Build and launch sovereign AI startup", 1.0)
        await upsert_user_profile("habit_evening", "habit", "Tends to procrastinate on social media when tired after work", 0.9)

@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Sovereign AI Companion API active. Web frontend at static/index.html"}

@app.get("/health")
async def health_check():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "model": MODEL_NAME,
        "ollama_connected": ollama_ok,
    }

@app.get("/v1/checkpoint")
async def get_checkpoint():
    cp = await get_latest_checkpoint()
    return {"checkpoint": cp}

@app.get("/v1/memories")
async def list_memories():
    profile = await get_user_profile()
    return {"profile": profile}

@app.post("/v1/execute")
async def execute_command_endpoint(req: ExecuteRequest):
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    result = default_tools.execute_terminal_command(command, cwd=req.cwd)
    await insert_audit_log(
        command=result["command"],
        blast_radius=result["blast_radius"],
        exit_code=result["exit_code"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        duration_ms=result["duration_ms"],
        is_safe=result["is_safe"]
    )
    return result

@app.get("/v1/system/vitals")
async def system_vitals_endpoint():
    return default_tools.get_system_vitals()

@app.post("/v1/agent/task", response_model=AgentTaskResult)
async def run_agent_task_endpoint(req: AgentTaskRequest):
    task_desc = req.task.strip()
    if not task_desc:
        raise HTTPException(status_code=400, detail="Task description cannot be empty")
    return await agent_loop.execute_task(task_desc, required_slots=req.required_slots)

@app.post("/v1/chat")
async def chat_endpoint(req: ChatRequest):
    conversation_id = req.conversation_id
    user_text = req.message.strip()
    
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    await compactor.acquire_user_turn()
    await ensure_conversation(conversation_id)

    is_crisis, crisis_referral = inspect_crisis_intervention(user_text)
    if is_crisis:
        msg_id_u = f"msg_{uuid.uuid4().hex[:12]}"
        msg_id_a = f"msg_{uuid.uuid4().hex[:12]}"
        await insert_message(msg_id_u, conversation_id, "user", user_text, estimate_tokens(user_text), is_quarantined=1)
        await insert_message(msg_id_a, conversation_id, "system_crisis", crisis_referral, estimate_tokens(crisis_referral), is_quarantined=1)

        async def crisis_stream():
            yield f"data: {json.dumps({'token': crisis_referral})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(crisis_stream(), media_type="text/event-stream")

    memories = await retrieve_episodic_memories(user_text, top_k=3)
    profile_rows = await get_user_profile()
    profile_cards = [f"{r['category']}: {r['value']}" for r in profile_rows]
    
    history_rows = await get_active_messages(conversation_id, limit=20)
    dialogue_history = [{"role": r["role"], "content": r["content"]} for r in history_rows if r["role"] in ("user", "assistant")]

    active_persona = None
    for r in profile_rows:
        if r["key"] == "custom_persona":
            try:
                active_persona = json.loads(r["value"])
            except Exception:
                pass

    detected_persona = parse_persona(user_text)
    if detected_persona:
        if detected_persona.get("reset"):
            active_persona = None
            await upsert_user_profile("custom_persona", "persona", json.dumps({"name": "Aria", "gender": "female"}), 1.0)
        else:
            active_persona = detected_persona
            await upsert_user_profile("custom_persona", "persona", json.dumps(detected_persona), 1.0)

    personality_prompt, is_technical = select_personality_prompt(user_text, active_persona=active_persona)

    compiled_messages, active_tokens, compaction_needed = compile_budgeted_prompt(
        personality_prompt,
        profile_cards,
        memories,
        dialogue_history,
        user_text
    )

    user_tokens = estimate_tokens(user_text)
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    await insert_message(user_msg_id, conversation_id, "user", user_text, user_tokens, is_quarantined=0)

    ollama_payload = {
        "model": MODEL_NAME,
        "messages": compiled_messages,
        "stream": True,
        "options": get_chat_generation_options(is_technical=is_technical)
    }

    async def token_generator():
        assistant_chunks: List[str] = []
        question_count = 0
        stream_finished = False

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=ollama_payload) as resp:
                    if resp.status_code != 200:
                        yield f"data: {json.dumps({'error': f'Ollama error {resp.status_code}'})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if stream_finished:
                            break
                        if line:
                            try:
                                chunk_json = json.loads(line)
                                msg_chunk = chunk_json.get("message", {}).get("content", "")
                                if msg_chunk:
                                    if "?" in msg_chunk and not is_technical:
                                        if question_count >= 1:
                                            stream_finished = True
                                            break
                                        question_count += 1

                                    assistant_chunks.append(msg_chunk)
                                    yield f"data: {json.dumps({'token': msg_chunk, 'total_tokens': active_tokens})}\n\n"

                                    if not is_technical:
                                        acc = "".join(assistant_chunks)
                                        sents = [s for s in re.split(r'(?<=[.!?])\s+', acc) if s.strip() and re.search(r'\w', s)]
                                        if len(sents) >= 3 and acc.rstrip().endswith((".", "!", "?")):
                                            stream_finished = True
                                            break

                                if chunk_json.get("done", False):
                                    break
                            except Exception:
                                continue
        finally:
            full_assistant_reply = sanitize_response_length("".join(assistant_chunks), is_technical=is_technical)
            assist_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            if full_assistant_reply:
                assist_tokens = estimate_tokens(full_assistant_reply)
                await insert_message(assist_msg_id, conversation_id, "assistant", full_assistant_reply, assist_tokens, is_quarantined=0)

            yield f"data: {json.dumps({'done': True, 'message_id': assist_msg_id, 'token': '', 'total_tokens': active_tokens})}\n\n"
            yield "data: [DONE]\n\n"

            if compaction_needed:
                compactor.schedule_compaction(conversation_id)

    return StreamingResponse(token_generator(), media_type="text/event-stream")

@app.post("/v1/checkin")
async def trigger_proactive_checkin(req: CheckinRequest):
    conversation_id = req.conversation_id
    if is_within_quiet_hours():
        return {
            "status": "suppressed_quiet_hours",
            "message": "Check-in suppressed during quiet hours (23:00 - 08:00)"
        }

    checkpoint = await get_latest_checkpoint()
    if checkpoint:
        checkin_prompt = f"Good evening! Feeling refreshed? Want to pick back up on {checkpoint.get('project_topic')}?"
    else:
        checkin_prompt = "Hey! How's your evening going? Taking a breather or winding down?"

    return {
        "status": "dispatched",
        "checkin_message": checkin_prompt
    }

@app.post("/v1/feedback")
async def record_feedback(req: FeedbackRequest):
    db_path = "/srv/storage/ai-companion/training/local_rl.db"
    soup_bin = "/srv/storage/ai-companion/training/.venv/bin/soup"
    prompt_text = req.prompt or ""
    resp_text = req.response or ""

    if not prompt_text or not resp_text:
        active_msgs = await get_active_messages(req.conversation_id, limit=10)
        for i, m in enumerate(active_msgs):
            if m.get("id") == req.message_id or (not req.message_id and m.get("role") == "assistant"):
                resp_text = m.get("content", "")
                if i > 0 and active_msgs[i-1].get("role") == "user":
                    prompt_text = active_msgs[i-1].get("content", "")
                break

    if prompt_text and resp_text:
        try:
            proc = await asyncio.create_subprocess_exec(
                soup_bin,
                "local-rl", "record",
                "--db", db_path,
                "--prompt", prompt_text,
                "--response", resp_text,
                "--thumb", req.thumb,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
        except Exception:
            pass

    return {
        "status": "recorded",
        "thumb": req.thumb,
        "message_id": req.message_id
    }
