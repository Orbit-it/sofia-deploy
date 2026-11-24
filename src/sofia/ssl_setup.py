from __future__ import annotations

import shutil
from pathlib import Path

from . import console
from .config import DeployConfig
from .nginx_setup import install_nginx_ssl
from .system import run


def obtain_ssl(cfg: DeployConfig) -> None:
    if not cfg.enable_ssl:
        console.warn(f"SSL désactivé — HTTP seulement")
        return

    live = Path(f"/etc/letsencrypt/live/{cfg.domain}/fullchain.pem")
    if live.exists():
        console.log(f"Certificat déjà présent pour {cfg.domain}")
    else:
        if not shutil.which("certbot"):
            console.die("certbot introuvable")
        console.log(f"Let's Encrypt : {cfg.domain} + {cfg.www_domain}")
        webroot = run(
            [
                "certbot", "certonly", "--webroot", "-w", "/var/www/certbot",
                "-d", cfg.domain, "-d", cfg.www_domain,
                "--email", cfg.email, "--agree-tos", "--non-interactive", "--keep-until-expiring",
            ],
            check=False,
        )
        if webroot.returncode != 0:
            console.warn("Webroot échoué — tentative standalone…")
            run(["systemctl", "stop", "nginx"], check=False)
            try:
                run(
                    [
                        "certbot", "certonly", "--standalone",
                        "-d", cfg.domain, "-d", cfg.www_domain,
                        "--email", cfg.email, "--agree-tos", "--non-interactive",
                        "--preferred-challenges", "http",
                    ]
                )
            finally:
                run(["systemctl", "start", "nginx"], check=False)

    units = run(["systemctl", "list-unit-files"], capture=True, check=False)
    if units.returncode == 0 and "certbot.timer" in (units.stdout or ""):
        run(["systemctl", "enable", "--now", "certbot.timer"], check=False)
    else:
        cron = run(["crontab", "-l"], capture=True, check=False)
        existing = cron.stdout if cron.returncode == 0 else ""
        if "certbot renew" not in existing:
            run(
                "(crontab -l 2>/dev/null; echo \"0 3 * * * certbot renew --quiet --deploy-hook 'systemctl reload nginx'\") | crontab -",
                check=False,
            )

    if not live.exists():
        console.die("Certificat SSL introuvable. Vérifiez DNS + ports 80/443, puis relancez.")
    install_nginx_ssl(cfg)
