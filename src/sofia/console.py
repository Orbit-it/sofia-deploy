from __future__ import annotations

import getpass
import sys


class Colors:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    NC = "\033[0m"


def _c(color: str, msg: str) -> str:
    if not sys.stdout.isatty():
        return msg
    return f"{color}{msg}{Colors.NC}"


def log(msg: str) -> None:
    print(_c(Colors.GREEN, "[sofia] ") + msg)


def warn(msg: str) -> None:
    print(_c(Colors.YELLOW, "[sofia] ") + msg)


def error(msg: str) -> None:
    print(_c(Colors.RED, "[sofia] ") + msg, file=sys.stderr)


def die(msg: str) -> None:
    error(msg)
    raise SystemExit(1)


def title(msg: str) -> None:
    print()
    print(_c(Colors.BOLD + Colors.CYAN, msg))
    print(_c(Colors.CYAN, "=" * max(len(msg), 8)))


def ask(prompt: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    label = f"{prompt}{suffix}: "
    while True:
        value = getpass.getpass(label) if secret else input(label).strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("  → valeur obligatoire.")


def ask_bool(prompt: str, default: bool = True) -> bool:
    hint = "O/n" if default else "o/N"
    while True:
        value = input(f"{prompt} [{hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"o", "oui", "y", "yes", "1", "true"}:
            return True
        if value in {"n", "non", "no", "0", "false"}:
            return False
        print("  → répondre par o/n.")


def ask_choice(prompt: str, choices: list[str], default: str) -> str:
    labels = "/".join(f"[{c}]" if c == default else c for c in choices)
    while True:
        value = input(f"{prompt} ({labels}): ").strip().lower()
        if not value:
            return default
        if value in choices:
            return value
        print(f"  → choisir parmi : {', '.join(choices)}")
