"""Sofia — interactive deployer for Angular / React / Vite / Node apps."""

from .config import DeployConfig
from .deploy import deploy

__all__ = ["DeployConfig", "deploy"]
__version__ = "1.0.0"
