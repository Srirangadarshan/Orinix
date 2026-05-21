import json
import os
import sys
import traceback

from .adapters.ollama import OllamaAdapter
from .adapters.openai import OpenAIAdapter
from .adapters.anthropic import AnthropicAdapter
from .context import collect_all, format_system_prompt
from .tools import (
  build_tool_definitions,
  execute_tool,
  get_tool_category,
)
from .permissions import check_permission, log_action

CONFIG_PATH = os.path.expanduser("~/.config/omarchy/ai/config.toml")
HOME = os.path.expanduser("~")


def load_config() -> dict:
  config = {
    "llm": {
      "backend": "ollama",
    },
    "llm.ollama": {
      "model": "gemma3:4b",
      "host": "http://localhost:11434",
    },
    "llm.openai": {
      "model": "gpt-4o",
      "api_key": "",
      "api_base": "https://api.openai.com/v1",
    },
    "llm.anthropic": {
      "model": "claude-sonnet-4-20250514",
      "api_key": "",
    },
    "safety": {
      "permission_mode": "ask",
      "log_audit": True,
    },
  }

  if os.path.exists(CONFIG_PATH):
    try:
      import tomllib
      with open(CONFIG_PATH, "rb") as f:
        user_config = tomllib.load(f)
      _deep_merge(config, user_config)
    except Exception:
      pass

  return config


def _deep_merge(base: dict, override: dict):
  for key, value in override.items():
    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
      _deep_merge(base[key], value)
    else:
      base[key] = value


def create_adapter(config: dict):
  llm_config = config.get("llm", {})
  backend = llm_config.get("backend", "ollama")

  if backend == "ollama":
    ollama_cfg = config.get("llm.ollama", {})
    model = ollama_cfg.get("model", "gemma3:4b")
    host = ollama_cfg.get("host", "http://localhost:11434")
    return OllamaAdapter(model=model, host=host)

  elif backend == "openai":
    openai_cfg = config.get("llm.openai", {})
    model = openai_cfg.get("model", "gpt-4o")
    api_key = openai_cfg.get("api_key", "")
    api_base = openai_cfg.get("api_base", "https://api.openai.com/v1")
    return OpenAIAdapter(model=model, api_key=api_key, api_base=api_base)

  elif backend == "anthropic":
    anth_cfg = config.get("llm.anthropic", {})
    model = anth_cfg.get("model", "claude-sonnet-4-20250514")
    api_key = anth_cfg.get("api_key", "")
    return AnthropicAdapter(model=model, api_key=api_key)

  else:
    print(f"\033[31mUnknown backend: {backend}. Falling back to Ollama.\033[0m")
    return OllamaAdapter()


def load_theme_accent() -> str:
  try:
    colors_path = f"{HOME}/.config/omarchy/current/theme/colors.toml"
    with open(colors_path) as f:
      for line in f:
        if line.strip().startswith("accent"):
          val = line.split("=", 1)[1].strip().strip('"').strip("'")
          return val
  except Exception:
    pass
  return "\033[36m"


def print_banner(config: dict, adapter):
  print()
  print("\033[1m  ● Omarchy AI Assistant\033[0m")
  print(f"  \033[90mModel: {adapter.get_name() if hasattr(adapter, 'get_name') else 'unknown'}\033[0m")
  print(f"  \033[90mType 'exit' or 'quit' to close. Type 'help' for commands.\033[0m")
  print()


def print_help():
  print()
  print("  \033[1mCommands:\033[0m")
  print("  \033[36mexit\033[0m / \033[36mquit\033[0m    Close the AI assistant")
  print("  \033[36mclear\033[0m           Clear conversation history")
  print("  \033[36mhelp\033[0m            Show this help message")
  print("  \033[36mcontext\033[0m         Show the current system context")
  print("  \033[36mmodel\033[0m           Show current model info")
  print()


def run_chat(config: dict):
  adapter = create_adapter(config)
  accent = load_theme_accent()

  if not adapter.is_available():
    print(f"\033[31mCannot connect to {adapter.get_name()}.\033[0m")
    backend_name = config.get("llm", {}).get("backend", "ollama")
    if backend_name == "ollama":
      print(f"\033[33mMake sure Ollama is running: systemctl --user start ollama\033[0m")
      print(f"\033[33mOr install with: omarchy-ai-install\033[0m")
    else:
      print(f"\033[33mCheck your API key and endpoint in ~/.config/omarchy/ai/config.toml\033[0m")
    sys.exit(1)

  context = collect_all()
  tool_definitions = build_tool_definitions()
  system_prompt = format_system_prompt(context, tool_definitions)

  messages = []
  session_allowed: set[str] = set()
  use_tools = len(tool_definitions) > 0

  print_banner(config, adapter)

  while True:
    try:
      user_input = input(f"\033[1m> \033[0m").strip()
    except (EOFError, KeyboardInterrupt):
      print()
      break

    if not user_input:
      continue

    if user_input.lower() in ("exit", "quit"):
      break
    if user_input.lower() == "clear":
      messages.clear()
      print("  \033[90mConversation cleared.\033[0m")
      continue
    if user_input.lower() == "help":
      print_help()
      continue
    if user_input.lower() == "context":
      import pprint
      pprint.pprint(context)
      continue
    if user_input.lower() == "model":
      info = adapter.get_model_info()
      for k, v in info.items():
        print(f"  \033[36m{k}\033[0m: {v}")
      continue

    messages.append({"role": "user", "content": user_input})

    while True:
      try:
        response = adapter.chat(
          messages=messages,
          tools=tool_definitions if use_tools else None,
          system_prompt=system_prompt,
        )
      except Exception as e:
        print(f"\033[31mError: {e}\033[0m")
        messages.pop()
        break

      if response.content:
        print(f"\033[90m●\033[0m {response.content}")
        messages.append({"role": "assistant", "content": response.content})

      if response.tool_calls:
        for tc in response.tool_calls:
          category = get_tool_category(tc.name, tool_definitions)

          tool_desc = ""
          for t in tool_definitions:
            func = t.get("function", t)
            if func.get("name") == tc.name:
              tool_desc = func.get("description", "")
              break

          approved, reason = check_permission(tc.name, tc.arguments, category, tool_desc, session_allowed)

          if approved:
            success, result = execute_tool(tc.name, tc.arguments)
            status = "success" if success else "error"
            color = "\033[32m" if success else "\033[31m"
            print(f"  {color}● {tc.name}: {result[:200]}\033[0m")

            messages.append({
              "role": "tool",
              "content": result,
              "name": tc.name,
              "tool_name": tc.name,
            })

            if config.get("safety", {}).get("log_audit", True):
              log_action("execute", tc.name, tc.arguments, result, True)
          else:
            print(f"  \033[33m● {tc.name}: skipped (not approved)\033[0m")
            messages.append({
              "role": "tool",
              "content": "User declined to run this command",
              "name": tc.name,
              "tool_name": tc.name,
            })
            if config.get("safety", {}).get("log_audit", True):
              log_action("reject", tc.name, tc.arguments, "user declined", False)

        continue

      break

  print()
  print("  \033[90mGoodbye.\033[0m")
