# Architecture

The AI assistant is built in four layers:

```
┌─────────────────────────────────────────────────┐
│                  User Interface                  │
│  CLI (omarchy ai)   TUI (SUPER + ;)   Waybar    │
├─────────────────────────────────────────────────┤
│                 Orchestrator                     │
│  chat.py — main loop, message routing,          │
│  tool response cycle, permission checks         │
├─────────────────────────────────────────────────┤
│   LLM Adapters    │   Context Layer             │
│   ollama.py       │   collect_static()          │
│   openai.py       │   collect_dynamic()         │
│   anthropic.py    │   collect_hardware()        │
│                   │   format_system_prompt()    │
├─────────────────────────────────────────────────┤
│  Tool Engine     │  Permission System           │
│  build_tool_     │  4 tiers:                    │
│  definitions()   │  read-only (auto)            │
│  execute_tool()  │  safe (ask once)             │
│  250+ commands   │  sensitive (always ask)      │
│                  │  sudo (always ask + warning) │
├─────────────────────────────────────────────────┤
│              Index Engine (RAG)                  │
│  extract.py → chunk_text()                      │
│  embedder.py → embed_query() (Ollama API)       │
│  store.py → VectorStore (numpy + JSON)          │
│  indexer.py → walk_files() + parallel process   │
│  search.py → find() + query_notes()             │
└─────────────────────────────────────────────────┘
```

## Layer Details

### 1. LLM Adapters (`default/omarchy_ai/adapters/`)

Pluggable backends implementing a common interface (`LLMAdapter`):

| Adapter | File | Protocol |
|---|---|---|
| Ollama | `ollama.py` | HTTP to Ollama API (fully offline) |
| OpenAI | `openai.py` | OpenAI-compatible API |
| Anthropic | `anthropic.py` | Anthropic Messages API |

The `ChatResponse` dataclass normalizes responses from all backends into a common format with `content`, `tool_calls`, `usage`, and `finish_reason`.

### 2. Context Layer (`context.py`)

Collects system state into a JSON blob sent with every prompt:

- **Static**: OS version, hostname, user, theme name, accent color, dark mode
- **Hardware**: battery presence, touchpad, Vulkan, ASUS ROG, NVIDIA
- **Dynamic**: battery percentage/status, toggle states, running apps, active workspace

The `format_system_prompt()` function generates a pattern-based system prompt with explicit "WHEN TO USE" guidance, common workflow examples, permission rules, and the full tool listing.

### 3. Tool Engine (`tools.py`)

Two sources of tools:

- **Auto-discovered** (296 commands): `omarchy commands --json` lists all Omarchy CLI commands with their metadata (name, group, summary, args). Each becomes a tool with generic `{args: string}` parameters.

- **Builtin** (54 tools): Pre-defined tools with proper parameter schemas (`{query: string}`, `{level: string}`, `{packages: string}`, etc.) for the most common workflows. When a builtin and CLI tool share a name, the builtin version (with structured params) takes priority.

Critical tools (`omarchy_search_files`, `omarchy_query_notes`) are always placed first in the listing.

**Tool execution** routes through `execute_tool()`:
1. Python-native tools (`search_files`, `query_notes`) run directly via imports
2. All other tools run via subprocess to the corresponding `omarchy-*` CLI command
3. Builtin tools with structured params are converted to CLI arguments

### 4. Permission System (`permissions.py`)

Four tiers with escalating prompts:

| Tier | Behavior | Examples |
|---|---|---|
| `read-only` | Auto-approved | Battery status, theme list, file search |
| `safe` | Ask once per session | Brightness, toggles, screenshots |
| `sensitive` | Always ask | Package install/remove, system lock |
| `sudo` | Always ask + warning | Reboot, shutdown |

Audit logs are written to `~/.local/state/omarchy/ai-audit.log` when `log_audit = true`.

### 5. Index Engine (`default/omarchy_ai/index/`)

The RAG (Retrieval-Augmented Generation) pipeline:

```
File → extract_text() → chunk_text() → embedder.embed() → VectorStore.add() → save()
Query → embedder.embed_query() → VectorStore.search() → format_results()
```

| Component | File | Purpose |
|---|---|---|
| `extract.py` | Text extraction from TXT, MD, PDF, DOCX, XLSX, PPTX, code files | Chunking with 2000-char windows and 200-char overlap |
| `embedder.py` | Ollama `/api/embed` wrapper using mxbai-embed-large | Returns 1024-dim float32 vectors |
| `store.py` | Vector store using numpy `.npy` + JSON metadata | Cosine similarity search with 0.1 score threshold |
| `indexer.py` | Recursive file walker with parallel processing (4 workers) | Auto-indexes default directories, progress feedback |
| `search.py` | High-level `find()` and `query_notes()` functions | Auto-indexes on first use, format results for display |

**Design decisions:**
- Zero additional services — no ChromaDB, no Qdrant, no Docker
- Storage: numpy `.npy` files + JSON metadata — simple, fast, debuggable
- The only external dependency beyond stdlib is `numpy` (for vector operations)
- File system calls use `urllib.request` (stdlib) — no `requests` library needed
