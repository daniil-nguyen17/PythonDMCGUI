import pytest


@pytest.fixture
def tmp_users_path(tmp_path):
    return tmp_path / "users.json"
