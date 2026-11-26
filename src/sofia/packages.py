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
        # Copier le fichier fourni avec Sofia (évite openssl dhparam qui bloque 1–2 min)
        try:
            dh.write_text(template_text("ssl-dhparams.pem"), encoding="utf-8")
            console.log("Installé ssl-dhparams.pem (fourni avec Sofia)")
        except Exception:  # noqa: BLE001
            console.warn("Fallback : génération openssl dhparam (peut prendre 1–2 min, laisse tourner)…")
            run(["openssl", "dhparam", "-out", str(dh), "2048"])


def install_base_packages(host: HostOS) -> None:
    console.log("Installation des paquets système…")
    console.log("(dnf/apt peuvent sembler figés pendant le téléchargement — patiente)")
    pkg_update(host)

    if host.pkg == "apt":
        console.log("→ apt: nginx, certbot, outils…")
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
        console.log("Paquets système OK")
        return

    if not shutil.which("curl"):
        console.log("→ installation curl…")
        pkg_install(host, "curl", check=False)
    console.log("→ ca-certificates, openssl, git…")
    pkg_install(host, "ca-certificates", "openssl", "git", "tar", "gzip", check=False)

    if not shutil.which("nginx"):
        console.log("→ installation nginx…")
        if shutil.which("amazon-linux-extras"):
            run(["amazon-linux-extras", "enable", "nginx1"], check=False)
        if not pkg_install(host, "nginx", check=False):
            console.die("Échec installation nginx")
    else:
        console.log("nginx déjà présent")

    if not shutil.which("certbot"):
        console.log("→ installation certbot…")
        if not pkg_install(host, "certbot", "python3-certbot-nginx", check=False):
            console.warn("certbot introuvable — tentative pip (peut être long)…")
            if pkg_install(host, "python3-pip", check=False):
                run(["pip3", "install", "--upgrade", "certbot", "certbot-nginx"], check=False)
            else:
                console.warn("certbot non installé — SSL pourra échouer")
    else:
        console.log("certbot déjà présent")

    console.log("→ snippets SSL Let's Encrypt…")
    ensure_letsencrypt_ssl_snippets()
    console.log("Paquets système OK")
