from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

from . import console
from .build import build_app
from .config import DeployConfig
from .nginx_setup import install_nginx_http
from .node_runtime import ensure_node
from .packages import install_base_packages
from .ssl_setup import obtain_ssl
from .system import HostOS, open_firewall, require_root
from .systemd_setup import install_systemd


def write_runtime_env(cfg: DeployConfig) -> None:
    console.log(f"Écriture de {cfg.env_system}")
    cfg.env_system.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(cfg.env_vars.items())]
    cfg.env_system.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cfg.env_system.chmod(0o600)

    if not cfg.config_local.exists():
        local = {
            "APP_NAME": cfg.app_name,
            "DOMAIN": cfg.domain,
            "WWW_DOMAIN": cfg.www_domain,
            "EMAIL": cfg.email,
            "PORT": str(cfg.port),
            "FRAMEWORK": cfg.framework,
            "SERVE_MODE": cfg.serve_mode,
            "APP_DIR": str(cfg.app_dir),
            "BUILD_COMMAND": cfg.build_command,
            "START_COMMAND": cfg.start_command,
            "STATIC_ROOT": cfg.static_root,
            "ENABLE_SSL": "true" if cfg.enable_ssl else "false",
            "ADMIN_PASSWORD": cfg.admin_password,
            "TOKEN_SECRET": cfg.token_secret,
        }
        cfg.config_local.write_text(
            "\n".join(f"{k}={v}" for k, v in local.items()) + "\n",
            encoding="utf-8",
        )
        cfg.config_local.chmod(0o600)


def healthcheck(cfg: DeployConfig) -> None:
    console.log("Vérification…")
    if cfg.serve_mode == "node":
        url = f"http://127.0.0.1:{cfg.port}/"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
                code = resp.getcode()
        except (urllib.error.URLError, TimeoutError):
            code = "ERR"
        if code in {200, 304}:
            console.log(f"App OK sur :{cfg.port} (HTTP {code})")
        else:
            console.warn(
                f"HTTP {code} sur :{cfg.port} — journalctl -u {cfg.service_name} -n 50"
            )
    else:
        index = cfg.static_path / "index.html"
        if index.exists():
            console.log(f"Fichiers statiques OK ({cfg.static_path})")
        else:
            console.warn(f"index.html manquant dans {cfg.static_path}")


def print_summary(cfg: DeployConfig) -> None:
    print()
    console.log("===== Déploiement terminé =====")
    scheme = "https" if cfg.enable_ssl else "http"
    print(f"  App         : {cfg.app_name} ({cfg.framework} / {cfg.serve_mode})")
    print(f"  URL         : {scheme}://{cfg.domain}")
    if cfg.serve_mode == "node":
        print(f"  Service     : systemctl status {cfg.service_name}")
        print(f"  Logs        : journalctl -u {cfg.service_name} -f")
    print(f"  Env         : {cfg.env_system}")
    print()
    console.warn(f"DNS A/AAAA de {cfg.domain} → IP de ce serveur (ports 80/443).")


def deploy(cfg: DeployConfig) -> None:
    """Deploy the project on the current Linux host (requires root)."""
    require_root()
    cfg.validate()
    host = HostOS()
    total = 8

    console.step(1, total, "Paquets système (nginx, certbot…)")
    install_base_packages(host)

    console.step(2, total, "Node.js")
    cfg.node_bin = ensure_node(cfg, host)

    console.step(3, total, "Pare-feu 80/443")
    open_firewall()

    console.step(4, total, "Variables d'environnement")
    write_runtime_env(cfg)

    console.step(5, total, f"Build applicatif ({cfg.build_command[:60]}…)")
    build_app(cfg)

    console.step(6, total, "Service systemd + nginx HTTP")
    install_systemd(cfg)
    install_nginx_http(cfg)

    console.step(7, total, "Certificat SSL Let's Encrypt")
    obtain_ssl(cfg)

    console.step(8, total, "Vérification finale")
    healthcheck(cfg)
    print_summary(cfg)
