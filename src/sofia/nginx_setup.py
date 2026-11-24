from __future__ import annotations

from pathlib import Path

from . import console
from .config import DeployConfig
from .packages import ensure_letsencrypt_ssl_snippets
from .system import run
from .templates_util import write_rendered


def nginx_conf_path(cfg: DeployConfig) -> Path:
    if Path("/etc/nginx/conf.d").is_dir():
        return Path(f"/etc/nginx/conf.d/{cfg.nginx_site}.conf")
    if Path("/etc/nginx/sites-available").is_dir():
        return Path(f"/etc/nginx/sites-available/{cfg.nginx_site}")
    console.die("Répertoire de conf nginx introuvable")
    raise AssertionError


def enable_nginx_site(cfg: DeployConfig, conf: Path) -> None:
    sites_enabled = Path("/etc/nginx/sites-enabled")
    if Path("/etc/nginx/sites-available").is_dir() and sites_enabled.is_dir():
        link = sites_enabled / cfg.nginx_site
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(conf)
        default = sites_enabled / "default"
        if default.exists() or default.is_symlink():
            default.unlink()
    default_conf = Path("/etc/nginx/conf.d/default.conf")
    if default_conf.exists():
        default_conf.rename(default_conf.with_suffix(".conf.disabled"))


def _mapping(cfg: DeployConfig) -> dict[str, str]:
    return {
        "DOMAIN": cfg.domain,
        "WWW_DOMAIN": cfg.www_domain,
        "PORT": str(cfg.port),
        "STATIC_ROOT": str(cfg.static_path),
    }


def _http_template(cfg: DeployConfig) -> str:
    return "nginx-static-http.conf.tpl" if cfg.serve_mode == "static" else "nginx-proxy-http.conf.tpl"


def _ssl_template(cfg: DeployConfig) -> str:
    return "nginx-static-ssl.conf.tpl" if cfg.serve_mode == "static" else "nginx-proxy-ssl.conf.tpl"


def install_nginx_http(cfg: DeployConfig) -> None:
    Path("/var/www/certbot").mkdir(parents=True, exist_ok=True)
    conf = nginx_conf_path(cfg)
    write_rendered(_http_template(cfg), conf, _mapping(cfg))
    enable_nginx_site(cfg, conf)
    run(["nginx", "-t"])
    run(["systemctl", "enable", "nginx"])
    run(["systemctl", "restart", "nginx"])


def install_nginx_ssl(cfg: DeployConfig) -> None:
    ensure_letsencrypt_ssl_snippets()
    conf = nginx_conf_path(cfg)
    write_rendered(_ssl_template(cfg), conf, _mapping(cfg))
    enable_nginx_site(cfg, conf)
    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
