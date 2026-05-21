# Omarchy AI Assistant

A local, offline AI system assistant integrated into Omarchy Linux. It provides a natural-language chat interface and semantic file search powered by Ollama.

## Features

- **AI Chat** (`SUPER + ;`) — ask questions about your system, run commands, search files, all in natural language
- **Semantic File Search** — find files by meaning, not filename (`omarchy ai find "budget spreadsheet"`)
- **Personal RAG** — search your notes and documents for answers (`omarchy ai find --notes "smart home idea"`)
- **Tool Execution** — the AI can run 250+ Omarchy CLI commands with tiered permission prompts
- **Fully Offline** — runs locally via Ollama, no internet required after initial setup
- **Multi-Backend** — swap between Ollama (default), OpenAI, or Anthropic by editing config

## Quick Start

```bash
# Install
omarchy ai install

# Open interactive chat
omarchy ai

# One-shot question
omarchy ai "what's my battery status"

# Search files by meaning
omarchy ai find "budget report from last quarter"

# Search personal notes
omarchy ai find --notes "what did I write about smart home"
```

## Architecture

```
User Input → CLI / TUI → Orchestrator (chat.py)
                           ├── LLM Adapter (ollama/openai/anthropic)
                           ├── Context Layer (system state, hardware, toggles)
                           ├── Tool Engine (250+ Omarchy CLI commands)
                           ├── Permission System (4-tier approval)
                           └── Index Engine (semantic file search + RAG)
```

See [architecture.md](architecture.md) for details.

## Documentation

| Document | Description |
|---|---|
| [install.md](install.md) | Installation and removal |
| [usage.md](usage.md) | Chat, search, index, and model management |
| [configuration.md](configuration.md) | Config file reference |
| [architecture.md](architecture.md) | Technical architecture |
