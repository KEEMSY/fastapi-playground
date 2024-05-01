from src.domains.sync_example.database.models import SyncExample


def test_sync_example_생성(client):
    res = client.post("/api/sync/no-login/sync/example", json={"name": "test1", "description": "test"})
    new_sync_example = SyncExample(**res.json())

    assert res.status_code == 201
    assert new_sync_example.name == "test1"
