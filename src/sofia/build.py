from __future__ import annotations

import os
import stat
from pathlib import Path

from . import console
from .config import DeployConfig
from .system import run


def _chown_tree(path: Path, user: str, group: str) -> None:
    try:
        import grp
        import pwd

        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid
    except KeyError:
        return
    for root, dirs, files in os.walk(path):
        try:
            os.chown(root, uid, gid)
        except FileNotFoundError:
            continue
        for name in dirs + files:
            try:
                os.chown(os.path.join(root, name), uid, gid)
            except FileNotFoundError:
                continue


def build_app(cfg: DeployConfig) -> None:
    app = cfg.app_dir
    assert app is not None
    console.log(f"Build dans {app}…")
    _chown_tree(app, cfg.app_user, cfg.app_group)

    if cfg.skip_build:
        console.warn("skip_build — build ignoré")
    else:
        user = cfg.app_user if cfg.app_user != "root" else None
        run(
            ["bash", "-lc", f"cd {shlex_path(app)} && {cfg.build_command}"],
            user=user,
        )

    if cfg.serve_mode == "static":
        index = cfg.static_path / "index.html"
        if not index.exists():
            console.die(
                f"Build incomplet : {index} manquant. "
                "Vérifiez static_root / build_command."
            )
        console.log(f"Static root OK : {cfg.static_path}")


def shlex_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")
