# Configuration

The AI assistant is configured via `~/.config/omarchy/ai/config.toml`.

Open it with:

```bash
omarchy ai config
```

## Full Configuration Reference

```toml
# LLM Backend Selection
[llm]
backend = "ollama"           # ollama (default) | openai | anthropic

# Ollama Backend Settings
[llm.ollama]
model = "gemma3:4b"          # Model name in Ollama
host = "http://localhost:11434"  # Ollama API endpoint

# OpenAI Backend Settings
[llm.openai]
model = "gpt-4o"             # OpenAI model name
api_key = ""                 # Your OpenAI API key
api_base = "https://api.openai.com/v1"

# Anthropic Backend Settings
[llm.anthropic]
model = "claude-sonnet-4-20250514"  # Anthropic model name
api_key = ""                 # Your Anthropic API key

# File Index Settings
[index]
embedding_model = "mxbai-embed-large"  # Model used for embeddings
directories = ["~/Documents", "~/Downloads", "~/notes", "~/Desktop"]
notes_dir = "~/notes"        # Directory for note-specific queries
max_file_size = 10485760     # Max file size to index (10 MB)
include_extensions = [       # File types to index
  ".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx",
  ".py", ".sh", ".js", ".ts", ".rs", ".go", ".rb", ".php",
  ".c", ".h", ".cpp", ".hpp", ".java",
  ".json", ".toml", ".yaml", ".yml", ".conf", ".ini", ".csv", ".log",
  ".html", ".css", ".xml",
]

# Safety Settings
[safety]
permission_mode = "ask"      # ask | allow-all | deny-all
log_audit = true             # Log all tool executions to ~/.local/state/omarchy/ai-audit.log
```

## Switching Backends

To switch from Ollama to OpenAI:

```toml
[llm]
backend = "openai"

[llm.ollama]
model = "gemma3:4b"

[llm.openai]
model = "gpt-4o"
api_key = "sk-your-key-here"
```

The Ollama section is ignored when using OpenAI, and vice versa. No restart needed — changes take effect on next chat session.

## Permission Modes

| Mode | Behavior |
|---|---|
| `ask` (default) | Prompts user before sensitive/sudo actions, auto-approves read-only, asks once per session for safe actions |
| `allow-all` | Auto-approves all tool calls (not recommended) |
| `deny-all` | Rejects all tool calls, AI can read context and answer questions but cannot run commands |
