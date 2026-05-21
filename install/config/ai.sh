# Install Ollama and pull default AI model

echo "Install Ollama for the AI assistant"

if omarchy-pkg-missing ollama; then
  omarchy-pkg-add ollama
fi

systemctl --user enable ollama.service 2>/dev/null || true

mkdir -p ~/.config/omarchy/ai
cp "$OMARCHY_PATH/config/omarchy/ai/config.toml" ~/.config/omarchy/ai/ 2>/dev/null || true

echo "Pulling default AI model (gemma3:4b) in the background..."
ollama pull gemma3:4b &

echo "Pulling embedding model for file search..."
ollama pull mxbai-embed-large

echo "Indexing files for AI search in the background..."
mkdir -p ~/.local/share/omarchy/ai/index
python3 "$OMARCHY_PATH/bin/omarchy-ai-index" &>/dev/null &
