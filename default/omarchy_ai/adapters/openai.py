import json
import urllib.request
import urllib.error

from .base import LLMAdapter, ChatResponse, ToolCall


class OpenAIAdapter(LLMAdapter):
  def __init__(self, model: str, api_key: str, api_base: str = "https://api.openai.com/v1"):
    self.model = model
    self.api_key = api_key
    self.api_base = api_base.rstrip("/")

  def _request(self, data: dict) -> dict:
    url = f"{self.api_base}/chat/completions"
    req = urllib.request.Request(
      url,
      data=json.dumps(data).encode(),
      headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}",
      },
      method="POST",
    )
    try:
      with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
      body = e.read().decode()
      raise RuntimeError(f"API error {e.code}: {body}") from e
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
      "temperature": temperature,
      "max_tokens": max_tokens,
    }

    if tools:
      body["tools"] = tools

    result = self._request(body)

    choice = result.get("choices", [{}])[0]
    msg = choice.get("message", {})

    content = msg.get("content", "")
    raw_tool_calls = msg.get("tool_calls", [])

    tool_calls = []
    for tc in raw_tool_calls:
      func = tc.get("function", {})
      name = func.get("name", "")
      raw_args = func.get("arguments", "{}")
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
      finish_reason=choice.get("finish_reason"),
    )

  def is_available(self) -> bool:
    try:
      result = self._request({
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
      "provider": "openai-compat",
      "endpoint": self.api_base,
    }

  def get_name(self) -> str:
    return f"OpenAI/{self.model}"
