"""
Retro terminal rendering helpers. Pure stdlib (ANSI codes) — no extra
dependencies required. If you later want a fancier split-pane layout,
swap this out for `rich` or `textual`.
"""

import sys
import time

COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "white": "\033[97m",
    "red": "\033[91m",
    "dim": "\033[2m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


def color(text: str, name: str) -> str:
    return f"{COLORS.get(name, '')}{text}{RESET}"


def typewriter(text: str, color_name: str = "white", delay: float = 0.012):
    sys.stdout.write(COLORS.get(color_name, ""))
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET + "\n")


def speaker_line(name: str, color_name: str):
    label = f"[{name}]"
    print(f"\n{BOLD}{COLORS.get(color_name, '')}{label}{RESET}")


def moderator_line(text: str):
    print(f"\n{COLORS['dim']}--- {text} ---{RESET}")


def thinking_indicator(name: str):
    sys.stdout.write(f"{COLORS['dim']}{name} is composing a response...{RESET}\r")
    sys.stdout.flush()


def clear_line():
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def banner(topic: str):
    line = "=" * 60
    print(f"\n{BOLD}{line}\n  DEBATE TOPIC: {topic}\n{line}{RESET}\n")