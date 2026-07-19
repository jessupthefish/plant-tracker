import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _path(env_var: str, default: str) -> Path:
    value = os.environ.get(env_var, default)
    p = Path(value)
    return p if p.is_absolute() else PROJECT_ROOT / p


class Settings:
    plantnet_api_key: str = os.environ.get("PLANTNET_API_KEY", "")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    trefle_api_key: str = os.environ.get("TREFLE_API_KEY", "")
    api_bearer_token: str = os.environ.get("API_BEARER_TOKEN", "")

    db_path: Path = _path("DB_PATH", "data/plants.db")
    photos_dir: Path = _path("PHOTOS_DIR", "data/photos")

    vault_ssh_host: str = os.environ.get("VAULT_SSH_HOST", "local")
    vault_local_path: Path = Path(
        os.environ.get("VAULT_LOCAL_PATH", str(Path.home() / "Documents" / "Symbiote"))
    )
    vault_remote_path: str = os.environ.get("VAULT_REMOTE_PATH", "Documents/Symbiote")


settings = Settings()
settings.photos_dir.mkdir(parents=True, exist_ok=True)
settings.db_path.parent.mkdir(parents=True, exist_ok=True)
