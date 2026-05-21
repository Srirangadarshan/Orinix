# Installation & Removal

## Prerequisites

- Omarchy Linux
- At least 4 GB RAM (8 GB recommended)
- ~3 GB disk space for models
- Internet connection for the initial model download

## Automatic Install (Recommended)

The AI assistant is installed during the Omarchy install process. To install on an existing system:

```bash
omarchy ai install
```

This will:
1. Install Ollama via pacman
2. Install `python-numpy` for the vector store
3. Enable and start `ollama.service`
4. Copy the default config to `~/.config/omarchy/ai/config.toml`
5. Pull the Gemma 3 4B chat model (~2.6 GB)
6. Pull the mxbai-embed-large embedding model (~130 MB)
7. Index default directories (`~/Documents`, `~/Downloads`, `~/notes`, `~/Desktop`) in the background
8. Restart Waybar to show the AI status icon

## Manual Installation

```bash
# Install package
omarchy-pkg-add ollama

# Install Python dependency
omarchy-pkg-add python-numpy

# Copy default config
mkdir -p ~/.config/omarchy/ai
cp ~/.local/share/omarchy/config/omarchy/ai/config.toml ~/.config/omarchy/ai/

# Start Ollama
systemctl --user enable --now ollama.service

# Pull models
ollama pull gemma3:4b
ollama pull mxbai-embed-large

# Index files
mkdir -p ~/.local/share/omarchy/ai/index
python3 ~/.local/share/omarchy/bin/omarchy-ai-index
```

## Removal

```bash
omarchy ai remove
```

This will:
1. Stop and disable `ollama.service`
2. Remove the `ollama` package
3. Optionally delete downloaded models (~2.6 GB)
4. Delete `~/.config/omarchy/ai/`
5. Delete index data at `~/.local/share/omarchy/ai/index/`
6. Delete audit log at `~/.local/state/omarchy/ai-audit.log`
7. Restart Waybar

## Post-Install Verification

```bash
# Check Ollama is running
systemctl --user status ollama.service

# Check models are pulled
ollama list

# Check index status
omarchy ai index --status

# Test the AI
omarchy ai "hello, what can you do"
```
