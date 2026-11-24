# Sofia

Interactive Linux deployer for **Angular**, **React**, **Vite** and **Node.js** apps.

SSH into your server, run Sofia, answer a few questions — it installs Node, nginx,
Let’s Encrypt, systemd, builds your app and goes live.

> PyPI name is `sofia-deploy` (`sofia` was already taken).  
> CLI and Python import remain **`sofia`**.

## Install

```bash
pip install sofia-deploy
# or with root for system-wide CLI:
sudo pip install sofia-deploy
```

## Usage (on the target server)

```bash
cd /path/to/your/app
sudo sofia
```

Sofia will:

1. Detect Angular / React / Vite / Node from `package.json`
2. Ask domain, SSL email, port, build/start commands
3. Install dependencies (Node, nginx, certbot)
4. Build the app
5. Configure **systemd** + **nginx** reverse proxy (or static hosting)
6. Issue a **Let’s Encrypt** certificate

### Non-interactive

```bash
sudo sofia --non-interactive --config sofia.env
```

### Python API

```python
from sofia import DeployConfig, deploy

cfg = DeployConfig(
    project_root="/var/www/myapp",
    app_name="myapp",
    domain="example.com",
    email="admin@example.com",
    framework="vite",       # angular | react | vite | node
    serve_mode="static",    # static | node
    build_command="npm ci && npm run build",
    static_root="dist",
    enable_ssl=True,
)
deploy(cfg)
```

## Supported project types

| Framework | Typical build | Serve mode |
|-----------|---------------|------------|
| Angular   | `ng build` | `node` (custom server) or `static` |
| React (CRA) | `npm run build` | `static` → `build/` |
| Vite / Vite+React | `npm run build` | `static` → `dist/` |
| Node API / full stack | custom | `node` → `npm start` / `node server.js` |

## Requirements

- Linux (Amazon Linux, Ubuntu, Debian, RHEL/Rocky)
- Root (`sudo`)
- DNS A/AAAA pointing to the server
- Ports **80** and **443** open

## Publish (maintainers)

```bash
python -m pip install build twine
python -m build
twine upload dist/*
```
