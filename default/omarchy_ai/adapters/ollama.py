import json
import urllib.request
import urllib.error

from .base import LLMAdapter, ChatResponse, ToolCall


class OllamaAdapter(LLMAdapter):
  def __init__(self, model: str = "gemma3:4b", host: str = "http://localhost:11434"):
    self.model = model
    self.host = host.rstrip("/")

  def _request(self, endpoint: str, data: dict) -> dict:
    url = f"{self.host}{endpoint}"
    req = urllib.request.Request(
      url,
      data=json.dumps(data).encode(),
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    try:
      with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
      body = e.read().decode()
      raise RuntimeError(f"Ollama API error {e.code}: {body}") from e
    except urllib.error.URLError as e:
      raise RuntimeError(f"Cannot reach Ollama at {self.host}: {e.reason}") from e

  def chat(
    self,
    messages: list[dict],
    tools: list[dict] | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
  ) -> ChatResponse:
    body = {
      "model": self.model,
      "messages": messages,
      "stream": False,
      "options": {
        "temperature": temperature,
        "num_predict": max_tokens,
      },
    }

    if tools:
      body["tools"] = tools

    result = self._request("/api/chat", body)

    content = result.get("message", {}).get("content", "")
    raw_tool_calls = result.get("message", {}).get("tool_calls", [])

    tool_calls = []
    for tc in raw_tool_calls:
      func = tc.get("function", tc)
      name = func.get("name", "")
      raw_args = func.get("arguments", {})
      if isinstance(raw_args, str):
        raw_args = json.loads(raw_args)
      tool_calls.append(ToolCall(
        name=name,
        arguments=raw_args,
        id=tc.get("id", f"call_{name}"),
      ))

    return ChatResponse(
      content=content or None,
      tool_calls=tool_calls,
      usage=result.get("usage"),
      finish_reason=result.get("done_reason"),
    )

  def is_available(self) -> bool:
    try:
      req = urllib.request.Request(f"{self.host}/api/tags")
      with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status == 200
    except Exception:
      return False

  def get_model_info(self) -> dict:
    return {
      "name": self.model,
      "provider": "ollama",
      "endpoint": self.host,
    }

  def get_name(self) -> str:
    return f"Ollama/{self.model}"
