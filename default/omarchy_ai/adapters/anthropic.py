import json
import urllib.request
import urllib.error

from .base import LLMAdapter, ChatResponse, ToolCall


class AnthropicAdapter(LLMAdapter):
  def __init__(self, model: str, api_key: str):
    self.model = model
    self.api_key = api_key
    self.api_base = "https://api.anthropic.com/v1"

  def _request(self, data: dict) -> dict:
    url = f"{self.api_base}/messages"
    req = urllib.request.Request(
      url,
      data=json.dumps(data).encode(),
      headers={
        "Content-Type": "application/json",
        "x-api-key": self.api_key,
        "anthropic-version": "2023-06-01",
      },
      method="POST",
    )
    try:
      with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
      body = e.read().decode()
      raise RuntimeError(f"Anthropic API error {e.code}: {body}") from e
    except urllib.error.URLError as e:
      raise RuntimeError(f"Cannot reach {self.api_base}: {e.reason}") from e

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
      "max_tokens": max_tokens,
      "temperature": temperature,
    }

    if system_prompt:
      body["system"] = system_prompt

    if tools:
      anthy_tools = []
      for t in tools:
        func = t.get("function", t)
        anthy_tools.append({
          "name": func.get("name", ""),
          "description": func.get("description", ""),
          "input_schema": func.get("parameters", {}),
        })
      body["tools"] = anthy_tools

    result = self._request(body)

    content = ""
    tool_calls = []
    for block in result.get("content", []):
      if block.get("type") == "text":
        content = (content + " " + block.get("text", "")).strip()
      elif block.get("type") == "tool_use":
        tool_calls.append(ToolCall(
          name=block.get("name", ""),
          arguments=block.get("input", {}),
          id=block.get("id", f"toolu_{block.get('name', 'unknown')}"),
        ))

    return ChatResponse(
      content=content or None,
      tool_calls=tool_calls,
      usage={
        "input_tokens": result.get("usage", {}).get("input_tokens"),
        "output_tokens": result.get("usage", {}).get("output_tokens"),
      },
      finish_reason=result.get("stop_reason"),
    )

  def is_available(self) -> bool:
    try:
      self._request({
        "model": self.model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
      })
      return True
    except Exception:
      return False

  def get_model_info(self) -> dict:
    return {
      "name": self.model,
      "provider": "anthropic",
      "endpoint": self.api_base,
    }

  def get_name(self) -> str:
    return f"Anthropic/{self.model}"
