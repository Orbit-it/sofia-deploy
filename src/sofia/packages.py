from __future__ import annotations

import shutil
from pathlib import Path

from . import console
from .system import HostOS, pkg_install, pkg_update, run
from .templates_util import template_text

OPTIONS_SSL = """ssl_session_cache shared:le_nginx_SSL:10m;
ssl_session_timeout 1440m;
ssl_session_tickets off;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
"""


def ensure_letsencrypt_ssl_snippets() -> None:
    le = Path("/etc/letsencrypt")
    le.mkdir(parents=True, exist_ok=True)
    options = le / "options-ssl-nginx.conf"
    if not options.exists():
        try:
            options.write_text(template_text("options-ssl-nginx.conf"), encoding="utf-8")
        except Exception:  # noqa: BLE001
            options.write_text(OPTIONS_SSL, encoding="utf-8")
        console.log("Créé /etc/letsencrypt/options-ssl-nginx.conf")
    dh = le / "ssl-dhparams.pem"
    if not dh.exists():
        console.log("Génération de ssl-dhparams.pem (1–2 min)…")
        run(["openssl", "dhparam", "-out", str(dh), "2048"])


def install_base_packages(host: HostOS) -> None:
    console.log("Installation des paquets système…")
    pkg_update(host)

    if host.pkg == "apt":
        pkg_install(
            host,
            "curl",
            "ca-certificates",
            "gnupg",
            "openssl",
            "git",
            "nginx",
            "certbot",
            "python3-certbot-nginx",
        )
        ensure_letsencrypt_ssl_snippets()
        return

    if not shutil.which("curl"):
        pkg_install(host, "curl", check=False)
    pkg_install(host, "ca-certificates", "openssl", "git", "tar", "gzip", check=False)

    if not shutil.which("nginx"):
        if shutil.which("amazon-linux-extras"):
            run(["amazon-linux-extras", "enable", "nginx1"], check=False)
        if not pkg_install(host, "nginx", check=False):
            console.die("Échec installation nginx")

    if not shutil.which("certbot"):
        if not pkg_install(host, "certbot", "python3-certbot-nginx", check=False):
            console.warn("certbot introuvable — tentative pip…")
            if pkg_install(host, "python3-pip", check=False):
                run(["pip3", "install", "--upgrade", "certbot", "certbot-nginx"], check=False)
            else:
                console.warn("certbot non installé — SSL pourra échouer")

    ensure_letsencrypt_ssl_snippets()
