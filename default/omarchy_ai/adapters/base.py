from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
  name: str
  arguments: dict
  id: str


@dataclass
class ChatResponse:
  content: Optional[str]
  tool_calls: list[ToolCall] = field(default_factory=list)
  usage: Optional[dict] = None
  finish_reason: Optional[str] = None


class LLMAdapter(ABC):
  @abstractmethod
  def chat(
    self,
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
  ) -> ChatResponse:
    ...

  @abstractmethod
  def is_available(self) -> bool:
    ...

  @abstractmethod
  def get_model_info(self) -> dict:
    ...

  @abstractmethod
  def get_name(self) -> str:
    ...
