import os
import tomllib

from .embedder import Embedder
from .store import VectorStore, INDEX_DIR
from .indexer import index_directory, default_config, INCLUDE_EXTENSIONS


CONFIG_PATH = os.path.expanduser("~/.config/omarchy/ai/config.toml")


def _load_index_config() -> dict:
  cfg = default_config()
  if os.path.exists(CONFIG_PATH):
    try:
      with open(CONFIG_PATH, "rb") as f:
        user = tomllib.load(f)
      user_index = user.get("index", {})
      if "directories" in user_index:
        cfg["directories"] = user_index["directories"]
      if "notes_dir" in user_index:
        cfg["notes_dir"] = user_index["notes_dir"]
      if "embedding_model" in user_index:
        cfg["embedding_model"] = user_index["embedding_model"]
      if "max_file_size" in user_index:
        cfg["max_file_size"] = user_index["max_file_size"]
      if "include_extensions" in user_index:
        cfg["include_extensions"] = user_index["include_extensions"]
    except Exception:
      pass
  if "notes_dir" not in cfg:
    cfg["notes_dir"] = "~/notes"
  return cfg


def _get_store(config: dict) -> VectorStore:
  store = VectorStore()
  if store.count() == 0:
    dirs = config.get("directories", [])
    for d in dirs:
      try:
        index_directory(d, config)
      except Exception:
        pass
    store.load()
  return store


def find(query: str, top_k: int = 10) -> list[tuple[str, float, str, int]]:
  config = _load_index_config()
  embedder = Embedder(model=config.get("embedding_model", "mxbai-embed-large"))
  store = _get_store(config)

  query_vec = embedder.embed_query(query)
  return store.search(query_vec, top_k)


def query_notes(query: str, top_k: int = 5) -> list[tuple[str, float, str, int]]:
  config = _load_index_config()
  notes_dir = config.get("notes_dir", "~/notes")
  expanded = os.path.expanduser(notes_dir)

  if not os.path.isdir(expanded):
    return []

  embedder = Embedder(model=config.get("embedding_model", "mxbai-embed-large"))
  store = _get_store(config)

  query_vec = embedder.embed_query(query)
  all_results = store.search(query_vec, top_k * 3)

  notes_results = []
  for path, score, text, idx in all_results:
    if path.startswith(expanded):
      notes_results.append((path, score, text, idx))
    if len(notes_results) >= top_k:
      break

  return notes_results


def format_search_results(results: list[tuple[str, float, str, int]]) -> str:
  if not results:
    return "No matching files found."

  lines = []
  seen = set()
  for path, score, _text, _idx in results:
    if path not in seen:
      seen.add(path)
      lines.append(f"{path} ({score:.0%})")
  return "\n".join(lines)


def format_note_results(results: list[tuple[str, float, str, int]]) -> str:
  if not results:
    return "No matching notes found."

  lines = []
  for path, score, text, _idx in results:
    short = path.rsplit("/", 1)[-1]
    lines.append(f"[{short} ({score:.0%})]")
    excerpt = text[:500].strip()
    lines.append(excerpt)
    if len(text) > 500:
      lines.append("...")
    lines.append("")
  return "\n".join(lines).strip()


def index_exists() -> bool:
  store = VectorStore()
  return store.count() > 0
