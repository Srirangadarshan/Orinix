import json
import os
import numpy as np


INDEX_DIR = os.path.expanduser("~/.local/share/omarchy/ai/index")


class VectorStore:
  def __init__(self, index_dir: str = INDEX_DIR):
    self.index_dir = index_dir
    self.embeddings_path = os.path.join(index_dir, "embeddings.npy")
    self.metadata_path = os.path.join(index_dir, "metadata.json")
    self._embeddings: np.ndarray | None = None
    self._metadata: list[dict] | None = None
    self._dirty = False

  def load(self):
    if self._embeddings is not None:
      return
    try:
      self._embeddings = np.load(self.embeddings_path)
    except Exception:
      self._embeddings = np.empty((0, 0), dtype=np.float32)
    try:
      with open(self.metadata_path) as f:
        self._metadata = json.load(f)
    except Exception:
      self._metadata = []

  def save(self):
    os.makedirs(self.index_dir, exist_ok=True)
    if self._embeddings is not None and len(self._embeddings) > 0:
      np.save(self.embeddings_path, self._embeddings)
    else:
      if os.path.exists(self.embeddings_path):
        os.remove(self.embeddings_path)
    if self._metadata:
      with open(self.metadata_path, "w") as f:
        json.dump(self._metadata, f, indent=2)
    elif os.path.exists(self.metadata_path):
      os.remove(self.metadata_path)
    self._dirty = False

  def add(self, new_embeddings: np.ndarray, new_metadata: list[dict]):
    self.load()
    if self._embeddings is None or self._embeddings.size == 0:
      self._embeddings = new_embeddings.astype(np.float32)
      self._metadata = new_metadata
    else:
      self._embeddings = np.vstack([self._embeddings, new_embeddings.astype(np.float32)])
      self._metadata.extend(new_metadata)
    self._dirty = True

  def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float, str, int]]:
    self.load()
    if self._embeddings is None or len(self._embeddings) == 0:
      return []

    query = query_vector.astype(np.float32).reshape(1, -1)
    norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
    query_norm = np.linalg.norm(query)
    if norms.min() == 0 or query_norm == 0:
      return []
    sim = (self._embeddings @ query.T) / (norms * query_norm)
    sim = sim.flatten()

    top_indices = np.argsort(sim)[-top_k:][::-1]
    results = []
    for idx in top_indices:
      score = float(sim[idx])
      if score < 0.1:
        continue
      meta = self._metadata[idx]
      results.append((
        meta.get("path", ""),
        score,
        meta.get("text", ""),
        meta.get("chunk_index", 0),
      ))

    return results

  def count(self) -> int:
    self.load()
    return len(self._metadata) if self._metadata else 0

  def status(self) -> dict:
    self.load()
    file_count = len(set(m.get("path", "") for m in (self._metadata or [])))
    return {
      "chunks": self.count(),
      "files": file_count,
      "path": self.index_dir,
    }

  def clear(self):
    self._embeddings = np.empty((0, 0), dtype=np.float32)
    self._metadata = []
    self._dirty = True
    self.save()
