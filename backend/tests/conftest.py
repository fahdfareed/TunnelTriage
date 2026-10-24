import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from app.config import get_config  # noqa: E402


@pytest.fixture
def cfg():
    return get_config()
