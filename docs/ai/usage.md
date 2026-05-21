# Usage Guide

## AI Chat

### Interactive Mode

Press `SUPER + ;` or run:

```bash
omarchy ai
```

This opens a floating terminal overlay (800x600, pinned above all windows). Type questions in natural language.

**Built-in commands:**
- `exit` / `quit` — close the chat
- `clear` — clear conversation history
- `help` — show help
- `context` — show current system context
- `model` — show current model info

### One-Shot Mode

Ask a single question without entering the interactive chat:

```bash
omarchy ai "what's my battery status"
omarchy ai "set brightness to 50%"
omarchy ai "install ripgrep"
```

### Example Questions

| You ask | What happens |
|---|---|
| "find the budget file" | AI searches indexed files by meaning |
| "what's my battery" | AI runs `omarchy-battery-status` |
| "change theme to Tokyo Night" | AI applies the theme |
| "brightness to 75%" | AI adjusts display brightness |
| "install jq and ripgrep" | AI installs packages (asks permission) |
| "lock my computer" | AI locks the screen (asks permission) |
| "take a screenshot" | AI runs the screenshot tool |
| "what apps are running" | context already includes running apps |
| "reboot" | AI reboots the system (asks for sudo) |

## Semantic File Search

### Command Line

```bash
# Search all indexed files
omarchy ai find "budget spreadsheet from last quarter"

# Search only personal notes
omarchy ai find --notes "smart home automation idea"

# JSON output for scripting
omarchy ai find --json "budget"
```

Results show file paths with relevance scores (0-100%).

### How Search Works

1. Files are indexed on install (or first search)
2. Text is extracted from TXT, MD, PDF, DOCX, XLSX, PPTX, code, and config files
3. Content is chunked (2000 chars with 200 char overlap)
4. Each chunk is embedded using mxbai-embed-large (1024-dim vectors) via Ollama
5. Queries are embedded the same way and compared using cosine similarity
6. Results above 10% similarity are returned, sorted by relevance

### Via AI Chat

The AI will automatically search files when you ask questions like:
- "find me the budget file"
- "search for notes about smart home"
- "what did I write about machine learning"
- "where's that report from last month"

## Managing Indexed Folders

```bash
# Add a folder to the index
omarchy ai index --add ~/Projects

# Remove a folder from the index config
omarchy ai index --remove ~/Downloads

# List indexed folders
omarchy ai index --list

# Show index status
omarchy ai index --status

# Clear and rebuild the index
omarchy ai index --clear
omarchy ai index
```

Default indexed directories: `~/Documents`, `~/Downloads`, `~/notes`, `~/Desktop`.

## Model Management

```bash
# Show current model
omarchy ai model

# List available/recommended models
omarchy ai model list

# Switch to a different model
omarchy ai model llama3.2:3b
omarchy ai model qwen2.5:7b
```

### Recommended Models

| Model | Size | RAM Required | Quality |
|---|---|---|---|
| gemma3:4b | ~2.6 GB | 4 GB | Good (default) |
| llama3.2:3b | ~2.0 GB | 4 GB | Good |
| qwen2.5:7b | ~4.5 GB | 8 GB | Better |
| qwen2.5:14b | ~9 GB | 16 GB | Best |
