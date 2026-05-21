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
    raw = json.loads(result.stdout)
    commands = raw if isinstance(raw, list) else raw.get("commands", [])
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

  builtin = _builtin_tools()
  builtin_names = {bt.get("function", bt).get("name") for bt in builtin}
  # Replace CLI tools with builtin versions when they share a name
  tools = [t for t in tools if t.get("function", t).get("name") not in builtin_names]
  for bt in builtin:
    tools.append(bt)

  critical = {"omarchy_search_files", "omarchy_query_notes"}
  critical_tools = [t for t in tools if t.get("function", t).get("name") in critical]
  rest = [t for t in tools if t.get("function", t).get("name") not in critical]
  # Builtins with structured params before CLI tools with generic args
  rest_builtins = [t for t in rest if t.get("function", t).get("name") in builtin_names]
  rest_cli = [t for t in rest if t.get("function", t).get("name") not in builtin_names]
  return (critical_tools + rest_builtins + rest_cli)[:250]


def _builtin_tools() -> list[dict]:
  return [
    # === CRITICAL PYTHON TOOLS (not available as CLI commands) ===
    _tool("omarchy_search_files",
      "Search indexed files by natural language. When user says 'find' or 'search for' a file, use this. Returns file paths with relevance scores.",
      "read-only", query="Natural language search query"),
    _tool("omarchy_query_notes",
      "Search personal notes by meaning. When user says 'what did I write about' or 'check my notes', use this. Returns matching text excerpts.",
      "read-only", query="Natural language question about your notes"),

    # === SYSTEM INFO ===
    _tool("omarchy_hw_info",
      "Detect and report hardware: CPU, GPU, battery, touchpad, Vulkan support, ASUS ROG, NVIDIA.",
      "read-only"),
    _tool("omarchy_hw_battery_present",
      "Check if the system has a battery.",
      "read-only"),
    _tool("omarchy_hw_touchpad",
      "Check if the system has a touchpad.",
      "read-only"),
    _tool("omarchy_hw_vulkan",
      "Check if Vulkan graphics is available.",
      "read-only"),
    _tool("omarchy_hw_nvidia",
      "Check if an NVIDIA GPU is present.",
      "read-only"),

    # === POWER & BATTERY ===
    _tool("omarchy_battery_remaining",
      "Get current battery percentage (integer 0-100).",
      "read-only"),
    _tool("omarchy_battery_status",
      "Get detailed battery status including charge rate and time remaining.",
      "read-only"),
    _tool("omarchy_battery_capacity",
      "Get battery full capacity in watt-hours.",
      "read-only"),
    _tool("omarchy_ac_present",
      "Check if AC power is connected.",
      "read-only"),
    _tool("omarchy_powerprofile_set",
      "Set power profile. Valid values: performance, balanced, power-saver.",
      "safe", profile="performance|balanced|power-saver"),
    _tool("omarchy_powerprofile_list",
      "List all available power profiles on the system.",
      "read-only"),

    # === AUDIO ===
    _tool("omarchy_audio_input_mute",
      "Toggle microphone mute on/off. Drives hardware mic-mute LED on supported laptops.",
      "safe"),
    _tool("omarchy_audio_output_switch",
      "Switch between audio output devices while preserving mute state.",
      "safe"),

    # === DISPLAY & BRIGHTNESS ===
    _tool("omarchy_brightness_display",
      "Adjust display brightness. Examples: +5%, 5%-, 50%, on, off.",
      "safe", level="Brightness level like +5%, 50%, or on/off"),
    _tool("omarchy_brightness_keyboard",
      "Adjust keyboard backlight brightness.",
      "safe", level="Brightness level (up/down or percentage)"),

    # === CAPTURE ===
    _tool("omarchy_screenshot",
      "Take a screenshot. Options: region (select area), fullscreen, window. Save to file or copy to clipboard.",
      "safe", mode="region|fullscreen|window", action="save|copy"),
    _tool("omarchy_screenrecording",
      "Start or stop screen recording.",
      "safe", action="start|stop"),

    # === TOGGLES ===
    _tool("omarchy_toggle_idle",
      "Toggle automatic idle locking on or off.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_nightlight",
      "Toggle blue-light filter (nightlight) on or off.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_touchpad",
      "Toggle touchpad on or off.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_waybar",
      "Toggle the Waybar status bar visibility.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_screensaver",
      "Toggle screensaver availability.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_suspend",
      "Toggle system suspend availability.",
      "safe", state="on|off"),
    _tool("omarchy_toggle_notification_silencing",
      "Toggle notification do-not-disturb mode.",
      "safe", state="on|off"),

    # === THEME ===
    _tool("omarchy_theme_current",
      "Show the name of the currently active theme.",
      "read-only"),
    _tool("omarchy_theme_list",
      "List all available themes that can be applied.",
      "read-only"),
    _tool("omarchy_theme_set",
      "Apply an Omarchy theme by name. Use omarchy_theme_list first if unsure.",
      "safe", theme_name="Name of the theme to apply"),
    _tool("omarchy_theme_bg_next",
      "Cycle to the next background wallpaper for the current theme.",
      "safe"),
    _tool("omarchy_theme_refresh",
      "Re-apply the current theme templates without switching.",
      "safe"),

    # === FONT ===
    _tool("omarchy_font_current",
      "Show the current system monospace font.",
      "read-only"),
    _tool("omarchy_font_list",
      "List all available monospace fonts.",
      "read-only"),
    _tool("omarchy_font_set",
      "Change the system monospace font. Use omarchy_font_list first to see options.",
      "safe", font_name="Font name to set"),

    # === WEATHER ===
    _tool("omarchy_weather_status",
      "Get current weather: temperature, conditions, wind.",
      "read-only"),
    _tool("omarchy_weather_icon",
      "Get a weather condition icon adjusted for sunrise/sunset.",
      "read-only"),

    # === NOTIFICATIONS ===
    _tool("omarchy_notification_send",
      "Send a desktop notification with a headline and optional body text.",
      "safe", headline="Notification title", body="Notification body text (optional)"),

    # === PACKAGE MANAGEMENT ===
    _tool("omarchy_pkg_add",
      "Install one or more Arch Linux packages. Example: omarchy_pkg_add(args='jq ripgrep')",
      "sensitive", packages="Package names to install, space-separated"),
    _tool("omarchy_pkg_remove",
      "Remove one or more installed packages.",
      "sensitive", packages="Package names to remove, space-separated"),
    _tool("omarchy_pkg_update",
      "Update all system packages with pacman.",
      "sensitive"),

    # === SYSTEM CONTROLS ===
    _tool("omarchy_system_lock",
      "Lock the screen immediately. Turns off display.",
      "sensitive"),
    _tool("omarchy_system_logout",
      "Log out after closing application windows.",
      "sensitive"),
    _tool("omarchy_system_reboot",
      "Reboot the computer after closing application windows. Requires sudo.",
      "sudo"),
    _tool("omarchy_system_shutdown",
      "Shut down the computer after closing application windows. Requires sudo.",
      "sudo"),
    _tool("omarchy_system_wake",
      "Wake displays and restore brightness after idle/sleep.",
      "safe"),

    # === UPDATE ===
    _tool("omarchy_update_perform",
      "Run the full Omarchy update pipeline: git pull, system packages, AUR packages, firmware.",
      "sensitive"),

    # === NETWORK ===
    _tool("omarchy_wifi_powersave",
      "Set Wi-Fi power saving mode on or off.",
      "safe", state="on|off"),

    # === STYLE ===
    _tool("omarchy_style_corners",
      "Set window and UI corner style: sharp or round. Affects Hyprland, notifications, menus.",
      "safe", style="sharp|round"),
    _tool("omarchy_style_waybar_position",
      "Set Waybar panel position: top or bottom.",
      "safe", position="top|bottom"),

    # === LAUNCH ===
    _tool("omarchy_launch_browser",
      "Open the default web browser. Optionally with a URL.",
      "safe", url="URL to open (optional)"),
    _tool("omarchy_launch_terminal",
      "Open a terminal window.",
      "safe"),
    _tool("omarchy_launch_files",
      "Open the file manager (Nautilus).",
      "safe"),
    _tool("omarchy_launch_wifi",
      "Open the Wi-Fi network manager TUI.",
      "safe"),
    _tool("omarchy_launch_bluetooth",
      "Open the Bluetooth manager TUI.",
      "safe"),
  ]


def _tool(name: str, description: str, category: str, **params) -> dict:
  props = {}
  required = []
  for param_name, param_desc in params.items():
    props[param_name] = {"type": "string", "description": param_desc}
    required.append(param_name)

  return {
    "type": "function",
    "function": {
      "name": name,
      "description": f"[{category}] {description}",
      "parameters": {
        "type": "object",
        "properties": props or {"_": {"type": "string", "description": "No arguments needed"}},
        "required": required,
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
  else:
    param_values = [v for k, v in arguments.items() if k != "_"]
    if param_values:
      full_cmd = f"{safe_name} {shlex.join(param_values)}"

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
