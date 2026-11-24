from __future__ import annotations

import shlex
import time
from pathlib import Path

from . import console
from .config import DeployConfig
from .system import run
from .templates_util import write_rendered


def _start_exec(cfg: DeployConfig) -> str:
    """Build ExecStart line. Prefer absolute node when command starts with node."""
    cmd = cfg.start_command.strip()
    if cmd.startswith("node "):
        script = cmd[5:].strip()
        return f"{cfg.node_bin} {script}"
    if cmd in {"npm start", "npm run start"}:
        npm = str(Path(cfg.node_bin).parent / "npm")
        if not Path(npm).exists():
            npm = "npm"
        return f"{npm} start"
    # Generic: run via bash -lc so npm/pnpm/yarn work
    return f"/bin/bash -lc {shlex.quote(cmd)}"


def install_systemd(cfg: DeployConfig) -> None:
    if cfg.serve_mode != "node":
        console.log("Mode static — pas de service systemd applicatif")
        # Disable previous service if any
        return

    console.log(f"Installation du service systemd {cfg.service_name}…")
    unit = Path(f"/etc/systemd/system/{cfg.service_name}.service")
    write_rendered(
        "app.service.tpl",
        unit,
        {
            "APP_NAME": cfg.app_name,
            "APP_USER": cfg.app_user,
            "APP_GROUP": cfg.app_group,
            "APP_DIR": str(cfg.app_dir),
            "ENV_FILE": str(cfg.env_system),
            "START_EXEC": _start_exec(cfg),
        },
    )
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", cfg.service_name])
    run(["systemctl", "restart", cfg.service_name])
    time.sleep(1)
    run(["systemctl", "--no-pager", "--full", "status", cfg.service_name], check=False)
