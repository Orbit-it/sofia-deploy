from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path

from . import console
from .config import DeployConfig
from .system import HostOS, download, machine_arch, pkg_install, run


def _node_major() -> int | None:
    if not shutil.which("node"):
        return None
    out = run(["node", "-v"], capture=True, check=False)
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip().lstrip("v").split(".", 1)[0])
    except ValueError:
        return None


def node_ok() -> bool:
    major = _node_major()
    return major is not None and major >= 18


def install_node_from_tarball(cfg: DeployConfig) -> str:
    arch = machine_arch()
    ver = cfg.node_version
    name = f"node-v{ver}-linux-{arch}"
    url = f"https://nodejs.org/dist/v{ver}/{name}.tar.xz"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / "node.tar.xz"
        download(url, archive)
        with tarfile.open(archive, "r:xz") as tar:
            tar.extractall(tmp_path)
        target_root = Path("/usr/local/lib/nodejs")
        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.mkdir(parents=True)
        shutil.move(str(tmp_path / name), str(target_root / "node"))
    for binary in ("node", "npm", "npx"):
        src = Path("/usr/local/lib/nodejs/node/bin") / binary
        dest = Path("/usr/local/bin") / binary
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(src)
    return "/usr/local/bin/node"


def ensure_node(cfg: DeployConfig, host: HostOS) -> str:
    if node_ok():
        console.log(f"Node.js déjà installé : {run(['node', '-v'], capture=True).stdout.strip()}")
        return "/usr/local/bin/node" if Path("/usr/local/bin/node").exists() else shutil.which("node")  # type: ignore[return-value]

    if _node_major() is not None:
        console.warn(f"Node.js trop ancien — mise à jour vers {cfg.node_version}")

    console.log(f"Installation de Node.js {cfg.node_version}…")
    if host.pkg == "apt":
        setup = Path("/tmp/nodesource_setup.sh")
        try:
            download("https://deb.nodesource.com/setup_20.x", setup)
            run(["bash", str(setup)], check=False)
            pkg_install(host, "nodejs", check=False)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"NodeSource a échoué ({exc})")
        if not node_ok():
            return install_node_from_tarball(cfg)
    else:
        pkg_install(host, "nodejs", "npm", check=False)
        if not node_ok():
            console.warn("Fallback binaire officiel nodejs.org")
            return install_node_from_tarball(cfg)

    if not node_ok():
        console.die("Échec installation Node.js (>= 18 requis)")
    return "/usr/local/bin/node" if Path("/usr/local/bin/node").exists() else shutil.which("node")  # type: ignore[return-value]
