# Sovereign AI Personal Companion: System Design Document

*   **Author:** Zerak Jamil
*   **Status:** Approved
*   **Date:** 2026-11-20

--------------------------------------------------------------------------------

## Overview

This document specifies the technical design for a self-hosted, sovereign AI Personal Companion operating on the edge server `ayewar`. The system functions as a durable life archivist, gentle accountability partner, and conversational confidant. 

Unlike commercial cloud-hosted chatbots that treat conversations as disposable ephemeral sessions, this companion preserves relationship continuity across years without ongoing API subscription costs or telemetry leaks. The core technical mechanism separates the generative language model from durable memory management. An edge runtime (Ollama with Qwen2.5-3B Q4_K_M) generates responses within an NVIDIA GeForce GTX 1650 Mobile (4 GB VRAM) hardware envelope, while a dedicated Python/FastAPI harness governs token budgeting, episodic SQLite retrieval, and background context compaction.

## The Problem

1. **Privacy Insecurity in Personal Journals:** Users seeking an emotionally intelligent companion or accountability partner must either trust sensitive life reflections to multi-tenant cloud providers or forfeit conversational continuity.
2. **Context Window vs. Long-Term Memory Contradiction:** Commercial models advertise 128K+ token windows, but processing large raw histories locally exceeds consumer GPU VRAM and incurs quadratic attention compute latency. Storing years of verbatim dialogue in active context is computationally infeasible on a 4 GB GPU.
3. **Passive Reactive Chatbot Fatigue:** Standard conversational agents remain purely reactive; they wait passively for prompts, have zero agency to follow up on abandoned goals, and fail to differentiate between restorative rest and destructive avoidance.

## Goals

*   **G1 (Hardware & Compute Envelope):** Maintain 100% local GPU execution on an NVIDIA GeForce GTX 1650 (4 GB VRAM) with steady-state VRAM usage $\le 2.6 \text{ GB}$ (leaving $\ge 1.4 \text{ GB}$ headroom) and generation throughput $\ge 45 \text{ tokens/second}$.
*   **G2 (Bounded Token Budget):** Enforce a strict 4,096-token attention window per turn, dynamically allocated across System Persona (384), User Profile (256), Episodic Memory (512), Active History (2,144), and Generation Buffer (800).
*   **G3 (Asynchronous Context Compaction):** Automatically trigger background summarization when active context hits 75% utilization (3,072 tokens) without blocking or delaying user chat streaming.
*   **G4 (Durable Episodic Memory & Zero-VRAM Hybrid Retrieval):** Store permanent conversational history, user commitments, and session checkpoints in SQLite WAL mode on `/srv/storage`. Combine SQLite FTS5 BM25 keyword matching with CPU-side ONNX embeddings (`all-MiniLM-L6-v2`) to eliminate GPU VRAM contention.
*   **G5 (System Hardening & Data Sovereignty):** Anchor all models, logs, and database files in `/srv/storage/` to protect the 89%-full root `/` partition. Zero external cloud dependencies.

## Non-Goals

*   **NG1 (Cloud Fallback / Multi-Tenant Scaling):** No failover to proprietary APIs (OpenAI, Anthropic). The system is single-user, edge-exclusive, and operates fully offline or behind Tailscale.
*   **NG2 (7B+ Model Deployment):** No deployment of 7B or 14B models requiring CPU offloading across PCIe 3.0, which degrades token generation to unusable speeds (<3 tok/s).
*   **NG3 (Voice & Multimodal I/O in Initial Scope):** Speech-to-text (Whisper) and text-to-speech are deferred to subsequent phases. Phase 1 focuses exclusively on text streaming and memory synchronization.
*   **NG4 (Automated Task Execution / Tool Action Execution):** The companion does not execute shell scripts, browser automation, or financial actions on the user's behalf; it is a conversational accountability sounding board.
*   **NG5 (Nightly Dream Cycle Consolidation in Phase 1):** Full graph synthesis, associative dream consolidation, and cross-session semantic restructuring are deferred to Phase 4. Phase 1 focuses on deterministic FIFO compaction, FTS5 keyword retrieval, CPU ONNX semantic scoring, and structured session checkpoints.

## Open Questions

*   **OQ1 (Client Protocol Choice - Resolved):** Dual-transport architecture: FastAPI exposes authenticated Server-Sent Events (SSE) for the desktop/Tailscale web app (`100.65.241.69:8000`), while a lightweight Telegram Bot webhook / polling daemon and optional self-hosted `ntfy` topic deliver proactive background push check-in prompts directly to mobile devices without requiring a persistent open browser tab.
*   **OQ2 (Compaction Model Specialization):** Whether to use the resident Qwen2.5-3B for background compaction tasks or a fast 0.5B/1.5B secondary worker to minimize GPU compute contention during active user typing. Phase 1 employs Qwen2.5-3B governed by an in-memory priority scheduler with a 30-second conversational inactivity debounce.

## Critical User Journeys (CUJs)

### CUJ 1: Proactive Evening Check-in & Rest vs. Avoidance Guidance

*   **Given**: The user stated an ambition to finish a pitch deck by Friday. The time is 8:30 PM (evaluated against `USER_TIMEZONE`, outside quiet hours 23:00–08:00). Active context is at 1,800 tokens.
*   **When**: The check-in scheduler fires a proactive prompt dispatched via Telegram bot push (or `ntfy`), asking how their evening is going, and the user replies: *"Just scrolling through TikTok."*
*   **Then**: 
    1. The token budgeter compiles the active prompt with the User Goal Card (`Launch AI startup`), Episodic Memory, and the Personality Prompt (`Be warm, witty, never judgmental`), setting `options: {"num_ctx": 4096, "num_predict": 150}`.
    2. The companion generates a concise 2-sentence response recognizing their goal without shame: *"You've been working toward starting your own company. Is this a quick break, or are you putting something off?"*
    3. The interaction updates the user state in SQLite asynchronously without stalling generation.

### CUJ 2: Context Saturation & Out-of-Band Compaction with Pre-emptive Cancellation

*   **Given**: An extended discussion reaches 3,100 tokens, crossing the 75% threshold (3,072 tokens).
*   **When**: The user submits their next message.
*   **Then**:
    1. The API immediately streams the assistant's reply via SSE at $\ge 50 \text{ tok/s}$ with `options: {"num_ctx": 4096, "num_predict": 150}`. User requests hold an exclusive, pre-emptive generation lock.
    2. Upon stream completion, an in-memory priority scheduler in `compactor.py` schedules background compaction guarded by a 30-second conversational inactivity debounce.
    3. If the user sends another message during the 30-second debounce, the timer resets.
    4. If the user sends a message *while* compaction is actively executing against Ollama, `compactor.py` **pre-emptively cancels the in-flight compaction task** (`asyncio.Task.cancel()`), immediately closing the HTTP connection. Ollama terminates generation instantly, freeing the GPU for the incoming user request with zero wait.
    5. Once conversational idle is confirmed, the background worker isolates the oldest 1,000 tokens of non-quarantined dialogue, invokes Ollama with `options: {"num_ctx": 4096, "num_predict": 400}` to distill structured facts and commitments into `summaries` and `user_profile`, updates FTS5 and embeddings, and truncates the active working window down to 1,500 tokens.
    6. The user experiences zero latency penalty on subsequent turns.

### CUJ 3: Server Reboot & Session Recovery Checkpoint

*   **Given**: The user concludes a late-night session stating: *"I'm exhausted, heading to bed. Will continue writing the pitch deck tomorrow."*
*   **When**: The host server (`ayewar`) reboots overnight for routine maintenance.
*   **Then**:
    1. Systemd restarts `ollama.service` and the FastAPI companion service. Ollama preloads Qwen2.5-3B into VRAM (`OLLAMA_KEEP_ALIVE=-1`).
    2. When the user connects the following morning, the companion queries `checkpoints` from SQLite, finds the unfinished task and emotional state (`Tired`), and initiates: *"Good morning! Feeling rested? Ready to jump back into the pitch deck you were drafting last night?"*

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

The system comprises three decoupled architectural layers operating locally on `ayewar`: the **Inference Runtime**, the **AI Orchestration Harness**, and the **Client Interface Gateway**.

```
+-----------------------------------------------------------------------------------+
|                            Client Layer (Phone / Desktop)                         |
|      Tailscale Node (100.65.241.69) / Mobile Webview / Telegram Bot Webhook        |
+-----------------------------------------------------------------------------------+
                                        | (HTTP / SSE Stream)
                                        v
+-----------------------------------------------------------------------------------+
|                FastAPI Orchestration Harness (/srv/storage/ai-companion)          |
|                                                                                   |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  | Token Budgeter     |  | Context Retriever    |  | Response Guardrail        |  |
|  | (4K Envelope/75%)  |  | (FTS5 + CPU ONNX)    |  | (1-3 Sentences, Empathy)  |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  | Out-of-Band        |  | Check-in Scheduler   |  | Memory Manager            |  |
|  | Compactor Worker   |  | (Background Timer)   |  | (SQLite WAL Store)        |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
+-----------------------------------------------------------------------------------+
             | (Ollama REST API :11434)                 | (Local SQLite IPC)
             v                                          v
+--------------------------------------+   +----------------------------------------+
|   Ollama Runtime (systemd service)   |   |        SQLite Database Storage         |
|  Qwen2.5-3B Q4_K_M (37/37 Layers GPU)|   |     /srv/storage/ai-companion/data/    |
|  GTX 1650 Mobile (2,138 MiB VRAM)    |   |     companion.db (WAL Mode)            |
|  OLLAMA_KEEP_ALIVE = -1              |   |     FTS5 Full-Text & Embedding Index   |
+--------------------------------------+   +----------------------------------------+
```

### 1. Layer Specifications

#### 1.1. Edge Inference Runtime (`Ollama` + `Qwen2.5-3B Q4_K_M`)
* **Execution Boundary:** Native host systemd service (`ollama.service`) configured with drop-in overrides:
  * `OLLAMA_MODELS=/srv/storage/ollama/models` (anchors weights to NVMe, preserving root `/` headroom).
  * `OLLAMA_HOST=127.0.0.1:11434` (bound exclusively to loopback to isolate raw inference from the local area network).
  * `OLLAMA_KEEP_ALIVE=-1` (prevents model eviction during idle periods, guaranteeing instant $\le 180 \text{ ms}$ TTFT).
  * `OLLAMA_NUM_PARALLEL=1` (serializes GPU execution to strictly protect the 4 GB VRAM ceiling).
* **Context & Prediction Bounds:** All conversational API calls to Ollama (`/api/generate` and `/api/chat`) explicitly include `"options": {"num_ctx": 4096, "num_predict": 150}` in the JSON payload, preventing verbosity runaway and enforcing concise 1–3 sentence responses at the inference engine level. Compaction distillation calls pass `"options": {"num_ctx": 4096, "num_predict": 400}`.
* **Compute Allocation:** Full 37-layer GPU offload to the NVIDIA GeForce GTX 1650 Mobile.
  * Measured model buffer: 1,834.8 MiB.
  * Measured KV cache buffer (4,096 tokens): 144.0 MiB in FP16.
  * Measured peak VRAM: 2,138 MiB (52% utilization).
  * Measured generation speed: 50.4 to 52.1 tokens/sec.

#### 1.2. AI Orchestration Harness (Python 3.12 / FastAPI)
The harness operates as a standalone service in `/srv/storage/ai-companion/`:
* **`token_budgeter.py` (Deterministic Envelope Enforcement):**
  Allocates the fixed 4,096-token context budget:
  * System Persona & Behavioral Rules: `384 tokens` (Fixed)
  * User Core Preferences & Life Ambitions: `256 tokens` (Fixed)
  * Retrieved Episodic Memories (Top-3): `512 tokens` (Dynamic)
  * Working Conversation Window: `2,144 tokens` (Dynamic FIFO buffer)
  * Model Generation Allowance: `800 tokens` (Reserved output headroom)
  * *Threshold Invariant:* When total context reaches 3,072 tokens (75%), an asynchronous compaction event is enqueued. Always injects `"options": {"num_ctx": 4096, "num_predict": 150}` into conversational Ollama request payloads.
* **`retriever.py` (Zero-VRAM Hybrid Retrieval & NumPy Vector Scoring):**
  * Primary search: SQLite `FTS5` BM25 keyword matching over historical messages. Non-quarantined integrity is strictly guaranteed upstream by trigger `messages_ai` (`WHEN new.is_quarantined = 0`), preventing crisis turns from ever entering the virtual index.
  * Semantic enrichment: CPU-quantized `all-MiniLM-L6-v2` executed via `onnxruntime` on the host Intel i7-9750H CPU using local model files stored in `/srv/storage/ai-companion/models/` and `HF_HOME=/srv/storage/ai-companion/cache`.
  * In-process vector scoring: Loads 384-dimensional float32 vector BLOBs from `message_embeddings` and computes cosine similarity directly in NumPy in ~1.2 ms, avoiding brittle external SQLite C-extensions (`sqlite-vec`) in `aiosqlite`. Consumes ~45 MB system RAM with zero GPU VRAM impact.
* **`compactor.py` (Debounced Priority Scheduler & Pre-emptive Cancellation):**
  * Governed by an in-memory priority scheduler: active user conversational requests hold an exclusive, pre-emptive generation lock.
  * When context crosses the 75% threshold, background compaction is scheduled with a **30-second conversational inactivity debounce timer**.
  * **Pre-emptive Cancellation:** If a user sends a prompt *while* compaction is actively executing against Ollama, `compactor.py` immediately cancels the active `asyncio.Task` and closes the HTTP connection (`httpx`). Ollama aborts token generation instantly, freeing the GPU for the incoming user turn without latency penalty. Compaction is deferred to the next idle window.
  * Once 30 seconds of user inactivity elapses, the worker isolates older non-quarantined turns (oldest 1,000 tokens), calls Ollama with `"options": {"num_ctx": 4096, "num_predict": 400}` to distill structured facts and commitments, records results into `summaries` and `user_profile`, updates `messages_fts` and `message_embeddings`, and advances the active conversation boundary.
* **`guardrails.py` (Tone, Crisis Quarantine & Timezone-Aware Pacing):**
  * Enforces Personality System Prompt invariants: warm, witty, curious, 1–3 short sentences, never preachy or judgmental, zero corporate filler phrases.
  * **Crisis Intervention & Context Quarantine:** Scans for statements indicative of severe psychological distress or self-harm; immediately bypasses generative roleplay to return neutral, supportive emergency referral resources (e.g., 988 Suicide & Crisis Lifeline contact info) without simulating therapy. Crisis turns are persisted with `is_quarantined = 1` in SQLite and are strictly excluded from FTS5 indexing, vector embeddings, and compaction summaries so past crises are never regurgitated in casual prompts.
  * **Timezone-Aware Pacing & Quiet Hours:** Suppresses all proactive check-in notifications between 23:00 and 08:00 evaluated in the user's configured local timezone (`USER_TIMEZONE`, default `Asia/Riyadh`) via Python's standard `zoneinfo`.
  * **Backoff Strategy:** Implements exponential backoff on unacknowledged check-ins (1 hour $\to$ 4 hours $\to$ pause until user re-initiates).

### 2. Database Schema (`companion.db`)

The SQLite database is initialized with `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`, `PRAGMA busy_timeout = 5000;`, `PRAGMA foreign_keys = ON;`, and `PRAGMA recursive_triggers = ON;`. Enabling `recursive_triggers` guarantees that cascading foreign key deletions on `conversations` fire the `messages_ad` trigger, cleanly purging orphaned records from `messages_fts`.

```sql
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
```

### 3. Data Flow & Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Client / Tailscale)
    participant API as FastAPI Gateway
    participant Budget as Token Budgeter
    participant DB as SQLite (aiosqlite WAL)
    participant Ollama as Ollama (Qwen2.5-3B)
    participant Compactor as Priority Scheduler / Compactor

    User->>API: POST /v1/chat (message, stream=true)
    Note over API,Compactor: Acquire user lock; cancel in-flight compaction Task if running; reset debounce
    API->>DB: Async Query FTS5 BM25 + ONNX NumPy Cosine Sim (inherently pre-filtered by triggers)
    DB-->>API: Return Top-3 relevant memory nodes (max 512 tokens)
    API->>Budget: Compile prompt (System + Profile + Memories + Recent turns)
    
    alt Active Window >= 3,072 Tokens (75% Capacity)
        Budget->>Compactor: Schedule compaction (30s inactivity debounce)
    end
    
    Budget->>Ollama: POST /api/generate (stream=true, keep_alive=-1, options: {num_ctx: 4096, num_predict: 150})
    loop Stream Tokens
        Ollama-->>API: Token chunks (52 tokens/s)
        API-->>User: SSE Token Stream
    end
    
    API->>DB: Async record user message & assistant response
    Note over API,Compactor: Release user lock; start 30s conversational idle countdown
    
    opt After 30s Inactivity with Compaction Pending
        Compactor->>DB: Async fetch oldest 1,000 tokens of non-quarantined dialogue
        Compactor->>Ollama: POST /api/generate (distillation prompt, options: {num_ctx: 4096, num_predict: 400})
        Ollama-->>Compactor: Structured facts & commitments JSON
        Compactor->>DB: Async commit summaries, checkpoints, & message_embeddings
        Note over Compactor,DB: Advance active conversation window boundary
    end
```

--------------------------------------------------------------------------------

## Alternatives Considered

### Alternative A: Qwen2.5-7B with CPU Layer Offloading

*   **Description:** Running a 7B parameter model quantized to 4-bit (Q4_K_M) across hybrid GPU/CPU compute.
*   **Pros:** Marginal improvements in encyclopedic knowledge and syntactic complexity.
*   **Cons:** 7B Q4 requires ~4.5 GB VRAM. Exceeding the 4,096 MiB physical ceiling forces approximately 15 to 20 transformer layers into host system RAM. Transferring activation matrices back and forth across the PCIe 3.0 bus throttles generation throughput from 52 tokens/s down to 2.1–3.4 tokens/s.
*   **Reason for Rejection:** `Rejected by author: 15x–20x generation throughput collapse across PCIe 3.0 creates an unacceptable conversational lag, rendering real-time dialogue frustrating and unviable.`

### Alternative B: Commercial Cloud LLM API (OpenAI / Anthropic)

*   **Description:** Offloading companion reasoning and memory management to centralized frontier APIs.
*   **Pros:** Zero local GPU memory allocation, instant multi-device sync, and state-of-the-art general reasoning.
*   **Cons:** Transmits deeply personal thoughts, habit tracking, emotional reflections, and private life ambitions to third-party multi-tenant servers. Introduces ongoing per-token financial costs, rate limits, and failure during network outages.
*   **Reason for Rejection:** `Rejected by author: Violates the non-negotiable sovereign edge privacy guarantee and introduces recurring subscription costs.`

### Alternative C: Synchronous Compaction in Request-Response Hot Path

*   **Description:** Executing context summarization synchronously when active tokens cross the 75% threshold during an ongoing chat turn.
*   **Pros:** Simplifies concurrency control and eliminates potential SQLite database lock contention between background workers and the active API stream.
*   **Cons:** Summarizing 1,000+ tokens of dialogue requires 2.0 to 3.5 seconds of LLM execution. Running this in-band pauses the user's chat turn, creating a noticeable freeze every 8 to 12 turns.
*   **Reason for Rejection:** `Rejected by author: Freezes conversational streaming unpredictably. Replaced with out-of-band background compaction (asyncio.create_task) that executes after the turn completes.`

### Alternative D: GPU-Resident Vector Embedding Model

*   **Description:** Running a dedicated embedding model (e.g. `nomic-embed-text`) inside Ollama on the GTX 1650.
*   **Pros:** Simple unified Ollama API for both text generation and semantic embeddings.
*   **Cons:** An embedding model allocates an additional 400–600 MiB of VRAM. Combined with the 2,138 MiB base model and KV cache, this reduces VRAM safety headroom below 900 MiB, significantly increasing the risk of driver crashes during bursty token prefill.
*   **Reason for Rejection:** `Rejected by author: Unnecessarily consumes GPU VRAM. Replaced by running a CPU-quantized all-MiniLM-L6-v2 ONNX model on the host Intel i7-9750H, requiring only ~45 MB system RAM and ~3 ms latency with zero GPU VRAM impact.`

--------------------------------------------------------------------------------

## Non-Functional Requirements

### 1. Security & Data Privacy
* **Loopback & Isolated Binding:** Ollama is bound to loopback/local interface; the FastAPI gateway listens on local interfaces or Tailscale overlay (`100.65.241.69`).
* **Zero External Telemetry:** No analytical events, logs, or prompt telemetry leave the physical machine. All prompts and embeddings are processed locally.
* **Authentication:** API access protected by an optional bearer token header when exposed across the local network or Tailscale.

### 2. Performance & Resource Bounds
* **First Token Latency (TTFT):** $\le 200 \text{ ms}$ for warm model requests.
* **Streaming Throughput:** $\ge 45 \text{ tokens/second}$ sustained generation on the GTX 1650 Mobile GPU.
* **GPU Memory Footprint:** $\le 2,600 \text{ MiB}$ steady-state VRAM allocation, ensuring $\ge 1,400 \text{ MiB}$ physical safety margin.
* **CPU Consumption:** $\le 10\%$ CPU utilization during active generation; background compaction worker pinned to low-priority CPU scheduling (`nice=10`).
* **Root Partition Protection & Cache Routing:** All SQLite databases, vector files, temporary wheel compilations, and logs write strictly to `/srv/storage/ai-companion/` on NVMe. Hugging Face tokenizers, ONNX runtime models, and temporary buffers are strictly routed via environment variables `HF_HOME=/srv/storage/ai-companion/cache` and `TMPDIR=/srv/storage/tmp`. Writing to `~/.cache` or `/tmp` on root `/` is strictly prohibited.

### 3. Reliability & Recovery
* **Ollama Persistence:** `OLLAMA_KEEP_ALIVE=-1` guarantees model weights remain permanently in VRAM across chat turns.
* **Crash Resilience:** SQLite WAL mode with synchronous=NORMAL, `PRAGMA foreign_keys=ON;`, and `PRAGMA recursive_triggers=ON;` ensures zero database corruption if the server experiences a sudden power loss.
* **Automated WAL Checkpoints:** Daily automated backup via `VACUUM INTO '/srv/storage/backups/companion_backup_{date}.db'`.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create / Modify

#### 1. `/etc/systemd/system/ollama.service.d/override.conf` (Modify / Configure)
* **Type / Scope:** Systemd drop-in configuration for Ollama runtime.
* **Proposed Changes:** Set persistent environment overrides:
  ```ini
  [Service]
  Environment="OLLAMA_MODELS=/srv/storage/ollama/models"
  Environment="OLLAMA_HOST=127.0.0.1:11434"
  Environment="OLLAMA_KEEP_ALIVE=-1"
  Environment="OLLAMA_NUM_PARALLEL=1"
  ```

#### 2. `/srv/storage/ai-companion/requirements.txt` (Create)
* **Type / Scope:** Python dependency specification.
* **Proposed Changes:** Enumerate pinned minimal dependencies: `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `httpx>=0.27.0`, `pydantic>=2.8.0`, `aiosqlite>=0.20.0`, `onnxruntime>=1.18.0`, `tokenizers>=0.19.0`, `numpy>=1.26.0`. (Vector scoring is executed in-process via NumPy dot products, eliminating external SQLite C-extension compilation dependencies).

#### 3. `/srv/storage/ai-companion/src/config.py` (Create)
* **Type / Scope:** Runtime environment and configuration module.
* **Proposed Changes:** Define configuration constants with environment variable overrides: `OLLAMA_URL` (`http://127.0.0.1:11434`), `MODEL_NAME` (`qwen2.5:3b`), `MAX_CONTEXT_TOKENS` (`4096`), `COMPACTION_THRESHOLD_TOKENS` (`3072`), `NUM_PREDICT_CHAT` (`150`), `NUM_PREDICT_COMPACT` (`400`), `DATABASE_PATH` (`/srv/storage/ai-companion/data/companion.db`), `MODELS_DIR` (`/srv/storage/ai-companion/models`), `HF_HOME` (`/srv/storage/ai-companion/cache`), `TMPDIR` (`/srv/storage/tmp`), `USER_TIMEZONE` (`Asia/Riyadh`), `HOST` (`0.0.0.0`), `PORT` (`8000`), `QUIET_HOURS_START` (`23:00`), `QUIET_HOURS_END` (`08:00`). Explicitly configure `os.environ["HF_HOME"]` and `os.environ["TMPDIR"]` at module initialization.

#### 4. `/srv/storage/ai-companion/src/db.py` (Create)
* **Type / Scope:** SQLite asynchronous connection manager and schema migration.
* **Proposed Changes:** Implement thread-safe connection pooling via `aiosqlite`. Configure `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, `PRAGMA busy_timeout=5000;`, `PRAGMA foreign_keys=ON;`, and `PRAGMA recursive_triggers=ON;`. Provide idempotent async initialization functions for `conversations`, `messages` (including `is_quarantined INTEGER DEFAULT 0`), `messages_fts`, `message_embeddings`, `user_profile`, `summaries`, `checkpoints`, and FTS5 triggers (`messages_ai` excluding quarantined rows, `messages_ad`).

#### 5. `/srv/storage/ai-companion/src/token_budgeter.py` (Create)
* **Type / Scope:** Deterministic token allocator and threshold inspector.
* **Proposed Changes:** Load the fast Qwen tokenizer (via Hugging Face `tokenizers`) from `/srv/storage/ai-companion/models/`. Implement methods to count tokens across system prompt, memory nodes, and dialogue turns. Enforce the budget slice: Persona (384), Profile (256), Episodic Memory (512), Active History (2,144), Response Headroom (800). Guarantee `"options": {"num_ctx": 4096, "num_predict": 150}` is attached to all outbound conversational Ollama payloads. Trigger compaction signal if active tokens exceed 3,072.

#### 6. `/srv/storage/ai-companion/src/retriever.py` (Create)
* **Type / Scope:** Hybrid keyword and semantic memory retrieval engine.
* **Proposed Changes:** Implement async BM25 search over `messages_fts` virtual table. Because the `messages_ai` trigger conditionally omits quarantined turns (`WHEN new.is_quarantined = 0`), the index is pre-filtered, guaranteeing that crisis records are never retrieved. Integrate CPU ONNX runtime execution for `all-MiniLM-L6-v2` embedding generation stored in `/srv/storage/ai-companion/models/`. Compute cosine similarity in-process using NumPy dot products over 384-dimensional float32 vector BLOBs stored in `message_embeddings`. Provide hybrid scoring function combining BM25 keyword rank and vector cosine similarity to return the top-3 relevant memory nodes within a 512-token budget.

#### 7. `/srv/storage/ai-companion/src/compactor.py` (Create)
* **Type / Scope:** Debounced priority scheduler with pre-emptive cancellation and context compaction worker.
* **Proposed Changes:** Implement an in-memory priority scheduler where user chat requests acquire an exclusive pre-emptive lock. Provide `async def schedule_compaction(conversation_id: str)` with a 30-second conversational inactivity debounce timer. **Pre-emptive Cancellation:** If a user request arrives while compaction is calling Ollama, immediately cancel the active `asyncio.Task` and close the `httpx` connection, prompting Ollama to abort generation instantly and freeing the GPU with zero user wait. Upon timer expiration during confirmed idle, fetch oldest 1,000 tokens of non-quarantined dialogue, invoke Ollama with `"options": {"num_ctx": 4096, "num_predict": 400}` to distill structured facts and commitments into `summaries` and `user_profile`, compute dense embeddings for `message_embeddings`, and advance the active window boundary in SQLite.

#### 8. `/srv/storage/ai-companion/src/guardrails.py` (Create)
* **Type / Scope:** Persona system prompt compiler, crisis interceptor, and timezone-aware pacing governor.
* **Proposed Changes:** Assemble base persona system prompt (*"warm, witty, curious, honest, emotionally intelligent, 1–3 short sentences, never preachy"*). Append active goals from `user_profile` and relevant facts from `retriever.py`. Implement crisis intervention pattern matching that halts generative roleplay on self-harm indicators, persists the interaction with `is_quarantined = 1`, and outputs supportive crisis hotline referrals. Implement timezone-aware quiet-hours guard (23:00–08:00 evaluated in `USER_TIMEZONE` via `zoneinfo`) and exponential backoff for unacknowledged check-in prompts.

#### 9. `/srv/storage/ai-companion/src/server.py` (Create)
* **Type / Scope:** FastAPI application gateway, SSE streaming router, and check-in dispatcher.
* **Proposed Changes:** Expose `POST /v1/chat` (streaming SSE endpoint forwarding tokens directly to the client with user priority lock, in-flight compaction cancellation, and `"options": {"num_ctx": 4096, "num_predict": 150}`), `GET /v1/memories` (returns stored episodic facts), `DELETE /v1/memories/{id}` (user-controlled memory pruning), `POST /v1/checkin` (proactive check-in trigger adhering to quiet hours), and client integration hooks (Telegram bot webhook / `ntfy` push dispatcher).

#### 10. `/etc/systemd/system/ai-companion.service` (Create)
* **Type / Scope:** Linux systemd service unit.
* **Proposed Changes:** Systemd unit definition ensuring automatic restart on boot:
  ```ini
  [Unit]
  Description=Sovereign AI Personal Companion Harness
  Wants=ollama.service
  After=network.target ollama.service

  [Service]
  Type=simple
  User=ayewar
  WorkingDirectory=/srv/storage/ai-companion
  Environment="PYTHONPATH=/srv/storage/ai-companion"
  Environment="HF_HOME=/srv/storage/ai-companion/cache"
  Environment="TMPDIR=/srv/storage/tmp"
  ExecStartPre=/bin/mkdir -p /srv/storage/tmp /srv/storage/ai-companion/cache /srv/storage/ai-companion/data /srv/storage/ai-companion/models
  ExecStart=/srv/storage/ai-companion/.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8000
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

#### 11. `/srv/storage/ai-companion/tests/test_harness.py` (Create)
* **Type / Scope:** Automated test suite.
* **Proposed Changes:** Unit tests validating:
  * Token budgeter boundary calculations, 75% trigger detection, and `"options": {"num_ctx": 4096, "num_predict": 150}` payload validation.
  * SQLite schema creation, WAL mode verification, `PRAGMA recursive_triggers=ON;`, FTS5 sync triggers (`messages_ai`, `messages_ad`), and async `aiosqlite` execution.
  * Priority scheduler 30-second debounce and pre-emptive cancellation of active compaction tasks.
  * Crisis intervention filter halting generation, tagging `is_quarantined = 1`, and outputting resource referrals.
  * Quiet-hours check-in suppression between 23:00 and 08:00 in configured timezone.

---

## Verification Plan

### 1. Build & Dependency Verification
* Set up virtual environment in `/srv/storage/ai-companion/.venv/`.
* Run `export TMPDIR=/srv/storage/tmp && pip install -r requirements.txt`.
* Verify `onnxruntime` and `tokenizers` import and run on the host i7-9750H CPU without missing shared libraries.

### 2. Unit & Integration Tests
* Execute `pytest /srv/storage/ai-companion/tests/` to verify:
  * Database read/write concurrency in WAL mode without database locks.
  * Token allocation guarantees within 4,096 limit and 150 prediction ceiling.
  * FTS5 search precision over seeded test dialogue, verifying quarantined turns are excluded.
  * Cascade deletion of conversations purging `messages_fts` entries via recursive triggers.

### 3. Live Hardware & Latency Benchmarks
* Submit warm conversational request through `POST /v1/chat`.
* Verify time-to-first-token (TTFT) $\le 200 \text{ ms}$.
* Verify sustained streaming rate $\ge 45 \text{ tokens/second}$.
* Monitor `nvidia-smi` to confirm VRAM remains bounded at $\approx 2,138 \text{ MiB}$ (leaving $\ge 1.9 \text{ GB}$ headroom).
* Submit 15 consecutive messages to exceed 3,072 tokens and verify that background compaction triggers asynchronously without stalling the SSE token stream, and that user requests pre-emptively cancel in-flight compaction.

--------------------------------------------------------------------------------

*Drafted with EGM*