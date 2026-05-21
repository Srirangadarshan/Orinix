import json
import urllib.request
import urllib.error
import numpy as np


class Embedder:
  def __init__(self, model: str = "mxbai-embed-large", host: str = "http://localhost:11434"):
    self.model = model
    self.host = host.rstrip("/")
    self._dim = None

  def embed(self, texts: list[str]) -> np.ndarray:
    if not texts:
      return np.empty((0, 0), dtype=np.float32)

    data = {
      "model": self.model,
      "input": texts,
    }

    url = f"{self.host}/api/embed"
    req = urllib.request.Request(
      url,
      data=json.dumps(data).encode(),
      headers={"Content-Type": "application/json"},
      method="POST",
    )

    try:
      with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    except Exception as e:
      raise RuntimeError(f"Embedding failed: {e}")

    embeddings = result.get("embeddings", [])
    if not embeddings:
      raise RuntimeError("No embeddings returned")

    arr = np.array(embeddings, dtype=np.float32)
    self._dim = arr.shape[1]
    return arr

  def embed_query(self, text: str) -> np.ndarray:
    return self.embed([text])[0]

  @property
  def dim(self) -> int:
    if self._dim is None:
      self.embed([""])
    return self._dim or 0

  def model_available(self) -> bool:
    try:
      req = urllib.request.Request(f"{self.host}/api/tags")
      with urllib.request.urlopen(req, timeout=5) as resp:
        tags = json.loads(resp.read())
      for model in tags.get("models", []):
        if self.model in model.get("name", ""):
          return True
      return False
    except Exception:
      return False
