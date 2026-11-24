from __future__ import annotations

import grp
import os
import pwd
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "app"


@dataclass
class DeployConfig:
    project_root: Path
    app_name: str = ""
    domain: str = ""
    www_domain: str = ""
    email: str = ""
    port: int = 3000
    framework: str = "node"  # angular | react | vite | node
    serve_mode: str = "node"  # node | static
    app_dir: Path | None = None
    build_command: str = "npm ci || npm install"
    start_command: str = "npm start"
    static_root: str = "dist"
    enable_ssl: bool = True
    skip_build: bool = False
    app_user: str = ""
    app_group: str = ""
    node_bin: str = ""
    node_version: str = "20.18.2"
    env_vars: dict[str, str] = field(default_factory=dict)
    # optional secrets commonly needed
    admin_password: str = ""
    token_secret: str = ""

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root).resolve()
        if self.app_dir is None:
            self.app_dir = self.project_root
        else:
            self.app_dir = Path(self.app_dir).resolve()
        if not self.app_name:
            self.app_name = _slug(self.project_root.name)
        else:
            self.app_name = _slug(self.app_name)
        if not self.www_domain and self.domain:
            self.www_domain = f"www.{self.domain.removeprefix('www.')}"
        if not self.token_secret:
            self.token_secret = secrets.token_hex(32)
        if not self.app_user:
            candidate = os.environ.get("SUDO_USER") or os.environ.get("USER") or "ec2-user"
            try:
                pwd.getpwnam(candidate)
                self.app_user = candidate
            except KeyError:
                self.app_user = "root"
        if not self.app_group:
            try:
                gid = pwd.getpwnam(self.app_user).pw_gid
                self.app_group = grp.getgrgid(gid).gr_name
            except KeyError:
                self.app_group = "root"
        # Inject common env
        self.env_vars.setdefault("NODE_ENV", "production")
        self.env_vars.setdefault("PORT", str(self.port))
        if self.admin_password:
            self.env_vars.setdefault("ADMIN_PASSWORD", self.admin_password)
        if self.token_secret:
            self.env_vars.setdefault("TOKEN_SECRET", self.token_secret)

    @property
    def service_name(self) -> str:
        return self.app_name

    @property
    def env_system(self) -> Path:
        return Path(f"/etc/sofia/{self.app_name}/env")

    @property
    def nginx_site(self) -> str:
        return self.app_name

    @property
    def static_path(self) -> Path:
        return (self.app_dir / self.static_root).resolve()

    @property
    def config_local(self) -> Path:
        return self.project_root / "sofia.env"

    def validate(self) -> None:
        if not self.domain:
            raise ValueError("domain obligatoire")
        if self.enable_ssl and not self.email:
            raise ValueError("email obligatoire si SSL activé")
        if not self.app_dir or not self.app_dir.is_dir():
            raise ValueError(f"app_dir introuvable : {self.app_dir}")
        if self.serve_mode not in {"node", "static"}:
            raise ValueError("serve_mode doit être 'node' ou 'static'")
        if self.serve_mode == "node" and not self.start_command:
            raise ValueError("start_command obligatoire en mode node")
