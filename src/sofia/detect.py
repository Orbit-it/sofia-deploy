from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


FRAMEWORKS = ("angular", "react", "vite", "node")
SERVE_MODES = ("static", "node")


@dataclass
class ProjectHints:
    framework: str
    serve_mode: str
    app_dir: Path
    build_command: str
    start_command: str
    static_root: str
    package_manager: str  # npm | pnpm | yarn


def _read_package_json(path: Path) -> dict:
    pkg = path / "package.json"
    if not pkg.exists():
        return {}
    try:
        return json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _pm(app_dir: Path) -> str:
    if (app_dir / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (app_dir / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _install_cmd(pm: str) -> str:
    return {"npm": "npm ci || npm install", "pnpm": "pnpm install --frozen-lockfile || pnpm install", "yarn": "yarn install --frozen-lockfile || yarn install"}[pm]


def find_app_dir(project_root: Path) -> Path:
    """Prefer project_root, else common subfolders with package.json."""
    root = project_root.resolve()
    if (root / "package.json").exists():
        return root
    for name in ("backend", "frontend", "web", "app", "client", "server"):
        candidate = root / name
        if (candidate / "package.json").exists():
            return candidate
    return root


def detect_project(project_root: Path) -> ProjectHints:
    app_dir = find_app_dir(project_root)
    data = _read_package_json(app_dir)
    deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
    scripts = data.get("scripts") or {}
    pm = _pm(app_dir)
    install = _install_cmd(pm)

    has_angular = "@angular/core" in deps or "@angular/cli" in deps
    has_vite = "vite" in deps
    has_react = "react" in deps
    has_next = "next" in deps

    # Node server entry candidates
    server_candidates = [
        app_dir / "server" / "server.js",
        app_dir / "server.js",
        app_dir / "src" / "server.js",
        app_dir / "index.js",
    ]
    has_server_file = any(p.exists() for p in server_candidates)
    start_script = scripts.get("start") or scripts.get("server") or scripts.get("prod")

    if has_angular:
        framework = "angular"
        build = f"{install} && npx ng build --configuration production"
        # Angular with custom Node server (BrainUp-style) vs pure static
        if has_server_file or (start_script and "node" in str(start_script)):
            serve_mode = "node"
            start = start_script or "node server/server.js"
            # Prefer explicit file if scripts unclear
            for p in server_candidates:
                if p.exists():
                    start = f"node {p.relative_to(app_dir)}"
                    break
            static_root = ""
        else:
            serve_mode = "static"
            start = ""
            # Angular 17+ application builder → dist/<name>/browser
            dist = app_dir / "dist"
            static_root = "dist"
            if dist.is_dir():
                browsers = list(dist.glob("*/browser"))
                if browsers:
                    static_root = str(browsers[0].relative_to(app_dir))
                else:
                    subs = [p for p in dist.iterdir() if p.is_dir()]
                    if len(subs) == 1:
                        static_root = str(subs[0].relative_to(app_dir))
    elif has_next:
        framework = "node"
        serve_mode = "node"
        build = f"{install} && {pm} run build"
        start = start_script or f"{pm} start"
        static_root = ""
    elif has_vite:
        framework = "vite"
        serve_mode = "static"
        build = f"{install} && {pm} run build"
        start = ""
        static_root = "dist"
    elif has_react:
        framework = "react"
        serve_mode = "static"
        build = f"{install} && {pm} run build"
        start = ""
        # CRA → build/, Vite-react already caught above
        static_root = "build" if (app_dir / "build").exists() or "react-scripts" in deps else "dist"
    else:
        framework = "node"
        serve_mode = "node"
        build = f"{install}" + (f" && {pm} run build" if "build" in scripts else "")
        start = start_script or ("node server.js" if (app_dir / "server.js").exists() else f"{pm} start")
        static_root = ""

    return ProjectHints(
        framework=framework,
        serve_mode=serve_mode,
        app_dir=app_dir,
        build_command=build,
        start_command=start,
        static_root=static_root,
        package_manager=pm,
    )
