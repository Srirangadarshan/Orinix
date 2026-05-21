import os
import datetime

AUDIT_LOG = os.path.expanduser("~/.local/state/omarchy/ai-audit.log")


def log_action(action: str, tool: str, args: dict, result: str, approved: bool):
  os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
  timestamp = datetime.datetime.now().isoformat()
  status = "APPROVED" if approved else "REJECTED"
  with open(AUDIT_LOG, "a") as f:
    f.write(f"[{timestamp}] {status} | {tool} | args={args} | result={result}\n")


def prompt_user(tool_name: str, arguments: dict, category: str, tool_description: str) -> bool:
  args_str = ", ".join(f"{k}={v}" for k, v in arguments.items()) if arguments else "(no arguments)"

  print()
  print(f"\033[33m● AI wants to run:\033[0m")
  print(f"  \033[36m{tool_name}\033[0m {args_str}")
  print(f"  \033[90m({tool_description})\033[0m")

  if category == "sudo":
    print(f"  \033[31m⚠ This command requires sudo privileges\033[0m")

  while True:
    try:
      response = input(f"\033[33m  Run this? [y/N/a(llow for session)]: \033[0m").strip().lower()
    except (EOFError, KeyboardInterrupt):
      print()
      return False

    if response in ("y", "yes"):
      return True
    elif response in ("a", "allow", "all"):
      return True
    elif response in ("", "n", "no"):
      return False
    else:
      print("  Please answer y, n, or a.")


def check_permission(tool_name: str, arguments: dict, category: str, tool_description: str, session_allowed: set[str]) -> tuple[bool, str]:
  if category == "read-only":
    return True, "auto"

  if category == "safe" and tool_name in session_allowed:
    return True, "session"

  approved = prompt_user(tool_name, arguments, category, tool_description)

  if approved:
    session_allowed.add(tool_name)
    return True, "approved"
  else:
    return False, "rejected"
