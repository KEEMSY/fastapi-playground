from src.domains.sync_example.database.models import SyncExample
from tests.conftest import sync_client


def test_sync_example_생성(sync_client):
    res = sync_client.post("/api/sync/no-login/sync/example", json={"name": "test1", "description": "test"})
    new_sync_example = SyncExample(**res.json())

    assert res.status_code == 201
    assert new_sync_example.name == "test1"
