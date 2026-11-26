from __future__ import annotations

import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import console


class HostOS:
    def __init__(self) -> None:
        self.id = "unknown"
        self.version = ""
        self.pkg = "unknown"
        self._detect()

    def _detect(self) -> None:
        data: dict[str, str] = {}
        os_release = Path("/etc/os-release")
        if os_release.exists():
            for line in os_release.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    data[k] = v.strip().strip('"')
        self.id = data.get("ID", "unknown")
        self.version = data.get("VERSION_ID", "")
        if self.id in {"amzn", "amazon", "rhel", "centos", "rocky", "almalinux", "fedora"}:
            self.pkg = "dnf" if shutil.which("dnf") else "yum"
        elif self.id in {"ubuntu", "debian"}:
            self.pkg = "apt"
        else:
            console.die(
                f"OS non supporté ({self.id}). Supportés : Amazon Linux, RHEL/CentOS/Rocky, Ubuntu/Debian."
            )
        console.log(f"OS détecté : {self.id} {self.version} ({self.pkg})")


def require_root() -> None:
    if os.geteuid() != 0:
        console.die("Relancez avec sudo : sudo sofia")


def run(
    cmd: list[str] | str,
    *,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    user: str | None = None,
) -> subprocess.CompletedProcess:
    if isinstance(cmd, str):
        display = cmd
        if user and user != "root":
            args: list[str] | str = ["sudo", "-u", user, "-H", "bash", "-lc", cmd]
            shell = False
        else:
            args = cmd
            shell = True
    else:
        display = " ".join(cmd)
        if user and user != "root":
            args = ["sudo", "-u", user, "-H", *cmd]
            shell = False
        else:
            args = cmd
            shell = False
    console.log("$ " + display)
    return subprocess.run(
        args,
        shell=shell,
        check=check,
        text=True,
        capture_output=capture,
        env={**os.environ, **(env or {})},
    )


def pkg_update(host: HostOS) -> None:
    # Éviter `dnf makecache` complet (souvent long / silencieux sur Amazon Linux)
    if host.pkg == "apt":
        console.log("apt-get update…")
        run(["apt-get", "update", "-y"], check=False)
    elif host.pkg == "dnf":
        console.log("dnf check (rapide)…")
        run(["dnf", "-y", "check"], check=False)
    else:
        console.log("yum check…")
        run(["yum", "-y", "check"], check=False)


def pkg_install(host: HostOS, *packages: str, check: bool = True) -> bool:
    if not packages:
        return True
    try:
        if host.pkg == "apt":
            run(["apt-get", "install", "-y", *packages], env={"DEBIAN_FRONTEND": "noninteractive"}, check=check)
        elif host.pkg == "dnf":
            run(["dnf", "install", "-y", "--allowerasing", *packages], check=check)
        else:
            run(["yum", "install", "-y", *packages], check=check)
        return True
    except subprocess.CalledProcessError:
        if check:
            raise
        return False


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    console.log(f"Téléchargement {url}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310


def open_firewall() -> None:
    console.log("Ouverture des ports 80/443…")
    if shutil.which("firewall-cmd"):
        if run(["systemctl", "is-active", "--quiet", "firewalld"], check=False).returncode == 0:
            run(["firewall-cmd", "--permanent", "--add-service=http"], check=False)
            run(["firewall-cmd", "--permanent", "--add-service=https"], check=False)
            run(["firewall-cmd", "--reload"], check=False)
            return
    if shutil.which("ufw"):
        run(["ufw", "allow", "80/tcp"], check=False)
        run(["ufw", "allow", "443/tcp"], check=False)
        return
    console.warn("Pas de firewalld/ufw — vérifiez le security group AWS (80, 443).")


def machine_arch() -> str:
    m = platform.machine()
    if m in {"x86_64", "amd64"}:
        return "x64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    console.die(f"Architecture non supportée : {m}")
    raise AssertionError
