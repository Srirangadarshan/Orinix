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

  return f"""You are Omarchy AI, an intelligent system assistant for the Omarchy Linux distribution.

You can help the user manage their system by answering questions and executing tools.
Always be concise, helpful, and accurate.

SYSTEM CONTEXT:
{ctx_json}

AVAILABLE TOOLS:
{chr(10).join(tools_summary) if tools_summary else "  (no tools available)"}

RULES:
1. Only use tools that are explicitly provided to you. Do not guess or invent commands.
2. When the user asks you to do something, explain what you're going to do before doing it.
3. If a tool is not available for what the user wants, explain that you cannot do it and suggest alternatives if possible.
4. Be concise in your responses - the user is working at a terminal.
5. If a tool call fails, explain the error to the user."""
