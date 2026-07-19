import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="plant-tracker-test-"))
os.environ["DB_PATH"] = str(_TEST_ROOT / "test.db")
os.environ["PHOTOS_DIR"] = str(_TEST_ROOT / "photos")
os.environ["VAULT_LOCAL_PATH"] = str(_TEST_ROOT / "vault")
os.environ["VAULT_SSH_HOST"] = "local"
os.environ["API_BEARER_TOKEN"] = ""

from sqlmodel import SQLModel  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    init_db()
    shutil.rmtree(_TEST_ROOT / "photos", ignore_errors=True)
    shutil.rmtree(_TEST_ROOT / "vault", ignore_errors=True)

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
