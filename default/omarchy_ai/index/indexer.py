import os
import sys
import time
import concurrent.futures

from .extract import extract_text, chunk_text
from .embedder import Embedder
from .store import VectorStore, INDEX_DIR


DEFAULT_DIRS = ["~/Documents", "~/Downloads", "~/notes", "~/Desktop"]
INCLUDE_EXTENSIONS = {
  ".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx",
  ".py", ".sh", ".js", ".ts", ".rs", ".go", ".rb", ".php",
  ".c", ".h", ".cpp", ".hpp", ".java",
  ".json", ".toml", ".yaml", ".yml", ".conf", ".ini", ".csv", ".log",
  ".html", ".css", ".xml",
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_WORKERS = 4


def default_config() -> dict:
  return {
    "directories": DEFAULT_DIRS,
    "max_file_size": MAX_SIZE,
    "include_extensions": list(INCLUDE_EXTENSIONS),
    "embedding_model": "mxbai-embed-large",
  }


def walk_files(directory: str, config: dict) -> list[str]:
  include = set(config.get("include_extensions", INCLUDE_EXTENSIONS))
  max_size = config.get("max_file_size", MAX_SIZE)
  files = []
  try:
    for root, dirs, names in os.walk(os.path.expanduser(directory)):
      _skip_hidden(dirs)
      for name in names:
        ext = os.path.splitext(name)[1].lower()
        if ext not in include:
          continue
        path = os.path.join(root, name)
        try:
          if os.path.getsize(path) <= max_size:
            files.append(path)
        except OSError:
          continue
  except Exception:
    pass
  return files


def _skip_hidden(dirs: list[str]):
  i = 0
  while i < len(dirs):
    if dirs[i].startswith("."):
      del dirs[i]
    else:
      i += 1


def process_file(filepath: str, max_size: int) -> list[dict]:
  text = extract_text(filepath, max_size)
  if not text:
    return []
  chunks = chunk_text(text)
  results = []
  for i, chunk in enumerate(chunks):
    results.append({
      "path": filepath,
      "chunk_index": i,
      "text": chunk,
      "mod_time": os.path.getmtime(filepath),
      "ext": os.path.splitext(filepath)[1].lower(),
    })
  return results


def index_directory(directory: str, config: dict | None = None, verbose: bool = False) -> int:
  if config is None:
    config = default_config()

  expanded = os.path.expanduser(directory)
  if not os.path.isdir(expanded):
    if verbose:
      print(f"  \033[33m{expanded}: not found, skipping\033[0m")
    return 0

  files = walk_files(directory, config)
  if not files:
    if verbose:
      print(f"  \033[33m{expanded}: no supported files found\033[0m")
    return 0

  embedder = Embedder(model=config.get("embedding_model", "mxbai-embed-large"))
  store = VectorStore()

  total = len(files)
  processed = 0
  chunks_total = 0

  if verbose:
    print(f"  \033[36mIndexing {total} files in {expanded}...\033[0m")

  with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    future_map = {pool.submit(process_file, f, config.get("max_file_size", MAX_SIZE)): f for f in files}
    for future in concurrent.futures.as_completed(future_map):
      processed += 1
      if verbose and processed % 50 == 0:
        _progress(processed, total)

  all_chunks = []
  for future in concurrent.futures.as_completed(list(future_map.keys())):
    try:
      chunks = future.result()
      all_chunks.extend(chunks)
    except Exception:
      pass

  if not all_chunks:
    if verbose:
      print(f"  \033[33mNo text could be extracted from {expanded}\033[0m")
    return 0

  texts = [c["text"] for c in all_chunks]
  try:
    embeddings = embedder.embed(texts)
  except Exception as e:
    if verbose:
      print(f"  \033[31mEmbedding failed: {e}\033[0m")
    return 0

  metadata = []
  for chunk, emb in zip(all_chunks, embeddings):
    metadata.append({
      "path": chunk["path"],
      "chunk_index": chunk["chunk_index"],
      "text": chunk["text"],
      "mod_time": chunk["mod_time"],
      "ext": chunk["ext"],
    })

  store.add(embeddings, metadata)
  store.save()

  if verbose:
    print(f"  \033[32mIndexed {len(all_chunks)} chunks from {total} files in {expanded}\033[0m")

  return len(all_chunks)


def _progress(current: int, total: int):
  pct = int(current / total * 100)
  bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
  print(f"  \033[90m[{bar}] {pct}%\033[0m", end="\r")


def index_all_defaults(config: dict | None = None, verbose: bool = False):
  if config is None:
    config = default_config()
  dirs = config.get("directories", DEFAULT_DIRS)
  total_chunks = 0
  for d in dirs:
    total_chunks += index_directory(d, config, verbose)
  if verbose:
    print(f"  \033[32mDone. {total_chunks} total chunks indexed.\033[0m")


if __name__ == "__main__":
  verbose = "-q" not in sys.argv
  dirs = [d for d in sys.argv[1:] if not d.startswith("-")]
  if dirs:
    cfg = default_config()
    for d in dirs:
      index_directory(d, cfg, verbose)
  else:
    index_all_defaults(verbose=True)
