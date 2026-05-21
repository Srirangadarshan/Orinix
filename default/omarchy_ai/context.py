import json
import subprocess
import os
import shlex

OMARCHY_PATH = os.environ.get("OMARCHY_PATH", os.path.expanduser("~/.local/share/omarchy"))
HOME = os.path.expanduser("~")


def _run_cmd(cmd: str) -> str | None:
  try:
    result = subprocess.run(
      shlex.split(cmd),
      capture_output=True,
      text=True,
      timeout=10,
    )
    if result.returncode == 0:
      return result.stdout.strip()
    return None
  except Exception:
    return None


def _run_in_path(cmd: str) -> str | None:
  env = os.environ.copy()
  env["PATH"] = f"{OMARCHY_PATH}/bin:{env.get('PATH', '')}"
  try:
    result = subprocess.run(
      shlex.split(cmd),
      capture_output=True,
      text=True,
      timeout=10,
      env=env,
    )
    if result.returncode == 0:
      return result.stdout.strip()
    return None
  except Exception:
    return None


def _file_or(path: str, fallback: str = "") -> str:
  try:
    with open(path) as f:
      return f.read().strip()
  except Exception:
    return fallback


def collect_static() -> dict:
  os_name = _file_or(f"{OMARCHY_PATH}/version", "unknown")
  hostname = _run_cmd("hostname") or "unknown"
  user = os.environ.get("USER", "unknown")

  theme_name = _file_or(f"{HOME}/.config/omarchy/current/theme.name", "unknown")
  theme_colors = {}
  try:
    colors_path = f"{HOME}/.config/omarchy/current/theme/colors.toml"
    with open(colors_path) as f:
      for line in f:
        if "=" in line and not line.strip().startswith("["):
          key, val = line.split("=", 1)
          theme_colors[key.strip()] = val.strip().strip('"').strip("'")
  except Exception:
    pass

  is_dark = not os.path.exists(f"{HOME}/.config/omarchy/current/theme/light.mode")

  return {
    "schema_version": "1.0",
    "os": {
      "name": "Omarchy",
      "version": os_name,
    },
    "hostname": hostname,
    "user": user,
    "theme": {
      "name": theme_name,
      "is_dark": is_dark,
      "accent": theme_colors.get("accent", ""),
      "background": theme_colors.get("background", ""),
      "foreground": theme_colors.get("foreground", ""),
    },
  }


def collect_dynamic() -> dict:
  battery = {}
  battery_pct = _run_in_path("omarchy-battery-remaining")
  if battery_pct:
    battery["percentage"] = battery_pct

  battery_status = _run_in_path("omarchy-battery-status")
  if battery_status:
    battery["status"] = battery_status

  toggles = {}
  toggle_state = _run_in_path("omarchy-toggle-enabled")
  known_toggles = ["idle", "nightlight", "screensaver", "suspend", "touchpad", "touchscreen", "waybar"]
  for t in known_toggles:
    state_file = f"{HOME}/.local/state/omarchy/toggles/{t}"
    toggles[t] = os.path.exists(state_file)

  running_apps = []
  clients = _run_cmd("hyprctl clients -j")
  if clients:
    try:
      for c in json.loads(clients):
        if c.get("class"):
          running_apps.append(c["class"])
    except Exception:
      pass

  workspace = _run_cmd("hyprctl activeworkspace -j")
  active_workspace = None
  if workspace:
    try:
      active_workspace = json.loads(workspace).get("id")
    except Exception:
      pass

  return {
    "battery": battery or None,
    "toggles": toggles,
    "running_apps": running_apps[:20],
    "active_workspace": active_workspace,
  }


def collect_hardware() -> dict:
  return {
    "has_battery": _run_in_path("omarchy-battery-present") is not None,
    "has_touchpad": _run_in_path("omarchy-hw-touchpad") is not None,
    "has_vulkan": _run_in_path("omarchy-hw-vulkan") is not None,
    "has_asus_rog": _run_in_path("omarchy-hw-asus-rog") is not None,
    "has_nvidia": _run_in_path("omarchy-hw-nvidia") is not None,
  }


def collect_all() -> dict:
  ctx = collect_static()
  ctx["hardware"] = collect_hardware()
  ctx["dynamic"] = collect_dynamic()
  return ctx


def format_system_prompt(context: dict, tool_definitions: list[dict]) -> str:
  tools_summary = []
  for t in tool_definitions:
    func = t.get("function", t)
    tools_summary.append(f"  - {func.get('name', '')}: {func.get('description', '')}")

  ctx_json = json.dumps(context, indent=2)

  return f"""You are Omarchy AI, a terminal assistant for the Omarchy Linux distribution.
Be concise, accurate, and helpful. Keep responses under 3 sentences when possible.

SYSTEM STATE:
{ctx_json}

AVAILABLE TOOLS:
{chr(10).join(tools_summary) if tools_summary else "  (no tools available)"}

WHEN TO USE EACH TOOL:
- omarchy_search_files: User says "find", "search for", "locate" a file or document. Pass the search phrase as "query".
- omarchy_query_notes: User asks "what did I write about", "check my notes on", "remind me about". Only for personal notes.
- omarchy_battery_* / battery_*: User asks about battery, power, charge status.
- omarchy_weather_*: User asks about weather.
- omarchy_theme_*: User asks about or wants to change the visual theme.
- omarchy_brightness_*: User wants to change screen or keyboard brightness.
- omarchy_toggle_*: User wants to enable/disable idle, nightlight, touchpad, waybar, etc.
- omarchy_capture_*: User wants to take a screenshot or screen recording.
- omarchy_pkg_*: User wants to install or remove software packages.
- omarchy_system_lock: User wants to lock the screen.
- omarchy_system_reboot / omarchy_system_shutdown: User wants to restart or shut down.
- omarchy_notification_send: User asks to send a notification or reminder.
- omarchy_font_*: User wants to change the system font.
- omarchy_launch_* / omarchy-or-focus: User wants to open an application.
- omarchy_audio_*: User wants to mute/unmute mic or switch audio output.
- omarchy_wifi_*: User asks about Wi-Fi power saving.
- omarchy_powerprofiles_*: User wants to change power mode.
- All other tools follow the same pattern: tool name describes what it does.

COMMON WORKFLOWS:
- "find the budget file" → omarchy_search_files(query="budget")
- "what's my battery" → omarchy_battery_remaining or omarchy_battery_status
- "change theme to Tokyo Night" → omarchy_theme_set(args="Tokyo Night")
- "brightness to 50%" → omarchy_brightness_display(args="50%")
- "install ripgrep" → omarchy_pkg_add(args="ripgrep")
- "lock my computer" → omarchy_system_lock
- "take a screenshot" → omarchy_capture_screenshot

PERMISSIONS:
- Tools tagged [read-only] run automatically without asking.
- Tools tagged [safe] ask once per chat session, then auto-run.
- Tools tagged [sensitive] ask every time before running.
- Tools tagged [sudo] ask every time and require admin privileges.

RULES:
1. NEVER invent tools or commands. Only use the tools listed above.
2. Before using a sensitive or sudo tool, briefly explain what you will do.
3. If a tool call fails, report the error and suggest alternatives.
4. When the user's request is unclear, ask a clarifying question before acting.
5. After finding files with omarchy_search_files, ask the user if they want to open any of them."""
