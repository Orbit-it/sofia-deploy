from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import console
from .config import DeployConfig
from .deploy import deploy
from .detect import FRAMEWORKS, SERVE_MODES, detect_project


def _load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def interactive_config(project_root: Path) -> DeployConfig:
    console.title("Sofia — déploiement interactif")
    print("À lancer sur le serveur cible (SSH + sudo).\n")

    root = Path(console.ask("Chemin du projet", str(project_root)))
    hints = detect_project(root)
    saved = _load_env(root / "sofia.env")

    console.log(
        f"Détecté : {hints.framework} · mode {hints.serve_mode} · dir {hints.app_dir}"
    )

    app_name = console.ask("Nom de l'app (service systemd)", saved.get("APP_NAME") or root.name)
    domain = console.ask("Domaine", saved.get("DOMAIN") or "example.com")
    www = console.ask("Domaine www", saved.get("WWW_DOMAIN") or f"www.{domain.removeprefix('www.')}")

    framework = console.ask_choice(
        "Framework",
        list(FRAMEWORKS),
        saved.get("FRAMEWORK") or hints.framework,
    )
    serve_mode = console.ask_choice(
        "Mode de service",
        list(SERVE_MODES),
        saved.get("SERVE_MODE") or hints.serve_mode,
    )

    app_dir = Path(console.ask("Dossier de l'app (package.json)", saved.get("APP_DIR") or str(hints.app_dir)))
    build_command = console.ask("Commande de build", saved.get("BUILD_COMMAND") or hints.build_command)

    start_command = saved.get("START_COMMAND") or hints.start_command
    static_root = saved.get("STATIC_ROOT") or hints.static_root
    port = int(saved.get("PORT") or "3000")

    if serve_mode == "node":
        start_command = console.ask("Commande de démarrage", start_command or "npm start")
        port = int(console.ask("Port interne", str(port)))
    else:
        static_root = console.ask("Dossier des fichiers statiques (relatif à l'app)", static_root or "dist")

    enable_ssl = console.ask_bool(
        "Activer HTTPS (Let's Encrypt) ?",
        saved.get("ENABLE_SSL", "true").lower() != "false",
    )
    email = saved.get("EMAIL", "")
    if enable_ssl:
        email = console.ask("Email Let's Encrypt", email or None)

    admin_password = saved.get("ADMIN_PASSWORD", "")
    if console.ask_bool("Définir ADMIN_PASSWORD (apps type BrainUp) ?", bool(admin_password)):
        if admin_password and console.ask_bool("Réutiliser le mot de passe enregistré ?", True):
            pass
        else:
            admin_password = console.ask("ADMIN_PASSWORD", secret=True)

    skip_build = not console.ask_bool("Lancer le build maintenant ?", True)
    app_user = console.ask(
        "Utilisateur système",
        os.environ.get("SUDO_USER") or os.environ.get("USER") or "ec2-user",
    )

    print()
    console.title("Récapitulatif")
    print(f"  app       : {app_name}")
    print(f"  framework : {framework} / {serve_mode}")
    print(f"  root      : {root}")
    print(f"  app_dir   : {app_dir}")
    print(f"  domain    : {domain}")
    print(f"  SSL       : {'oui' if enable_ssl else 'non'}")
    print(f"  build     : {build_command}")
    if serve_mode == "node":
        print(f"  start     : {start_command} (:{port})")
    else:
        print(f"  static    : {static_root}")
    print()
    if not console.ask_bool("Confirmer le déploiement ?", True):
        console.warn("Annulé.")
        raise SystemExit(0)

    return DeployConfig(
        project_root=root,
        app_name=app_name,
        domain=domain,
        www_domain=www,
        email=email,
        port=port,
        framework=framework,
        serve_mode=serve_mode,
        app_dir=app_dir,
        build_command=build_command,
        start_command=start_command,
        static_root=static_root,
        enable_ssl=enable_ssl,
        skip_build=skip_build,
        app_user=app_user,
        admin_password=admin_password,
        token_secret=saved.get("TOKEN_SECRET", ""),
    )


def config_from_env(project_root: Path, env: dict[str, str], *, skip_ssl: bool, skip_build: bool) -> DeployConfig:
    enable_ssl = env.get("ENABLE_SSL", "true").lower() != "false" and not skip_ssl
    if not env.get("DOMAIN"):
        console.die("DOMAIN manquant dans sofia.env")
    if enable_ssl and not env.get("EMAIL"):
        console.die("EMAIL manquant dans sofia.env")
    return DeployConfig(
        project_root=project_root,
        app_name=env.get("APP_NAME") or project_root.name,
        domain=env["DOMAIN"],
        www_domain=env.get("WWW_DOMAIN", ""),
        email=env.get("EMAIL", ""),
        port=int(env.get("PORT", "3000")),
        framework=env.get("FRAMEWORK", "node"),
        serve_mode=env.get("SERVE_MODE", "node"),
        app_dir=Path(env["APP_DIR"]) if env.get("APP_DIR") else None,
        build_command=env.get("BUILD_COMMAND", "npm ci || npm install"),
        start_command=env.get("START_COMMAND", "npm start"),
        static_root=env.get("STATIC_ROOT", "dist"),
        enable_ssl=enable_ssl,
        skip_build=skip_build,
        admin_password=env.get("ADMIN_PASSWORD", ""),
        token_secret=env.get("TOKEN_SECRET", ""),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sofia",
        description="Sofia — déploiement interactif Angular / React / Vite / Node.",
    )
    parser.add_argument("--repo", "--project", dest="project", type=Path, help="Chemin du projet")
    parser.add_argument("--config", type=Path, help="Fichier sofia.env")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--skip-ssl", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)

    project = (args.project or Path.cwd()).resolve()
    env_path = args.config or (project / "sofia.env")
    env = _load_env(env_path)

    if args.non_interactive:
        if not env:
            console.die(f"--non-interactive : config introuvable ({env_path})")
        cfg = config_from_env(project, env, skip_ssl=args.skip_ssl, skip_build=args.skip_build)
    else:
        cfg = interactive_config(project)
        if args.skip_ssl:
            cfg.enable_ssl = False
        if args.skip_build:
            cfg.skip_build = True

    try:
        deploy(cfg)
    except KeyboardInterrupt:
        console.warn("Interrompu.")
        return 130
    except Exception as exc:  # noqa: BLE001
        console.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
