import json
import subprocess
import shlex
import os

TOOL_CATEGORIES = {
  "read-only": "auto",
  "safe": "ask-once",
  "sensitive": "always-ask",
  "sudo": "always-ask",
}

OMARCHY_PATH = os.environ.get("OMARCHY_PATH", os.path.expanduser("~/.local/share/omarchy"))


def _run_omarchy_cmd(cmd: str) -> tuple[int, str, str]:
  env = os.environ.copy()
  env["PATH"] = f"{OMARCHY_PATH}/bin:{env.get('PATH', '')}"
  try:
    result = subprocess.run(
      shlex.split(cmd),
      capture_output=True,
      text=True,
      timeout=120,
      env=env,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()
  except subprocess.TimeoutExpired:
    return -1, "", "Command timed out after 120 seconds"
  except Exception as e:
    return -1, "", str(e)


def build_tool_definitions() -> list[dict]:
  env = os.environ.copy()
  env["PATH"] = f"{OMARCHY_PATH}/bin:{env.get('PATH', '')}"
  try:
    result = subprocess.run(
      shlex.split("omarchy commands --json"),
      capture_output=True,
      text=True,
      timeout=15,
      env=env,
    )
    if result.returncode != 0:
      return _builtin_tools()
    commands = json.loads(result.stdout)
  except Exception:
    return _builtin_tools()

  tools = []
  for cmd in commands:
    name = cmd.get("name", "")
    summary = cmd.get("summary", "")
    group = cmd.get("group", "")
    args = cmd.get("args", "")

    if not name:
      continue

    safe_name = name.replace("-", "_").replace(" ", "_")
    tool_name = f"omarchy_{safe_name}"
    description = f"[{group}] {summary}" if group else summary

    tools.append({
      "type": "function",
      "function": {
        "name": tool_name,
        "description": description,
        "parameters": {
          "type": "object",
          "properties": {
            "args": {
              "type": "string",
              "description": f"Command arguments: {args}" if args else "Command arguments",
            }
          },
          "required": [],
        },
      },
    })

  return tools[:80]


def _builtin_tools() -> list[dict]:
  return [
    _tool("omarchy_search_files", "Search indexed files by natural language query. Use this when the user wants to find a file but doesn't remember the name. Returns file paths with relevance scores.", "read-only", "query"),
    _tool("omarchy_query_notes", "Search personal notes and return relevant content. Use this when the user asks a question that might be answered by their notes or documents. Returns text chunks that can answer the question.", "read-only", "query"),
    _tool("omarchy_battery", "Get battery status and remaining percentage", "read-only"),
    _tool("omarchy_weather", "Get current weather information", "read-only"),
    _tool("omarchy_theme_list", "List available themes", "read-only"),
    _tool("omarchy_theme_current", "Show current theme name", "read-only"),
    _tool("omarchy_theme_set", "Change the system theme", "safe", "theme_name"),
    _tool("omarchy_theme_bg_next", "Cycle to next background wallpaper", "safe"),
    _tool("omarchy_toggle_idle", "Toggle idle locking on or off", "safe", "state"),
    _tool("omarchy_toggle_nightlight", "Toggle nightlight on or off", "safe", "state"),
    _tool("omarchy_toggle_touchpad", "Toggle touchpad on or off", "safe", "state"),
    _tool("omarchy_toggle_waybar", "Toggle waybar visibility on or off", "safe", "state"),
    _tool("omarchy_brightness_set", "Set display brightness level", "safe", "level"),
    _tool("omarchy_font_set", "Change the system font", "safe", "font_name"),
    _tool("omarchy_powerprofile_set", "Set power profile (performance/balanced/power-saver)", "safe", "profile"),
    _tool("omarchy_pkg_add", "Install packages via pacman", "sensitive", "packages"),
    _tool("omarchy_pkg_remove", "Remove packages via pacman", "sensitive", "packages"),
    _tool("omarchy_notification_send", "Send a desktop notification", "safe", "headline", "description"),
    _tool("omarchy_system_lock", "Lock the system", "sensitive"),
    _tool("omarchy_system_reboot", "Reboot the system", "sudo"),
    _tool("omarchy_system_shutdown", "Shut down the system", "sudo"),
  ]


def _tool(name: str, description: str, category: str, *args) -> dict:
  props = {}
  for arg in args:
    props[arg] = {"type": "string", "description": arg.replace("_", " ").title()}

  return {
    "type": "function",
    "function": {
      "name": name,
      "description": f"[{category}] {description}",
      "parameters": {
        "type": "object",
        "properties": props or {"_": {"type": "string", "description": "No arguments needed"}},
        "required": list(props.keys()) if props else [],
      },
    },
  }


def get_tool_category(tool_name: str, definitions: list[dict]) -> str:
  for t in definitions:
    func = t.get("function", t)
    if func.get("name") == tool_name:
      desc = func.get("description", "")
      if "[sudo]" in desc:
        return "sudo"
      if "[sensitive]" in desc:
        return "sensitive"
      if "[safe]" in desc:
        return "safe"
      if "[read-only]" in desc:
        return "read-only"
  return "sensitive"


def execute_tool(tool_name: str, arguments: dict) -> tuple[bool, str]:
  if tool_name == "omarchy_search_files":
    try:
      from omarchy_ai.index.search import find, format_search_results
      query = arguments.get("query", "")
      if not query:
        return False, "No query provided"
      results = find(query)
      return True, format_search_results(results)
    except Exception as e:
      return False, f"Search failed: {e}"

  if tool_name == "omarchy_query_notes":
    try:
      from omarchy_ai.index.search import query_notes, format_note_results
      query = arguments.get("query", "")
      if not query:
        return False, "No query provided"
      results = query_notes(query)
      return True, format_note_results(results)
    except Exception as e:
      return False, f"Notes search failed: {e}"

  safe_name = tool_name.replace("omarchy_", "omarchy-", 1).replace("_", "-")

  full_cmd = safe_name
  args = arguments.get("args", "")
  if args:
    full_cmd = f"{safe_name} {args}"

  env = os.environ.copy()
  env["PATH"] = f"{OMARCHY_PATH}/bin:{env.get('PATH', '')}"

  try:
    result = subprocess.run(
      shlex.split(full_cmd),
      capture_output=True,
      text=True,
      timeout=120,
      env=env,
    )
    if result.returncode == 0:
      output = result.stdout.strip()
      return True, output if output else "(completed successfully)"
    else:
      error = result.stderr.strip() or result.stdout.strip()
      return False, error or f"Command failed with exit code {result.returncode}"
  except subprocess.TimeoutExpired:
    return False, "Command timed out"
  except Exception as e:
    return False, str(e)
