def test_create_community_requires_auth(client):
    r = client.post("/communities", json={"name": "python"})
    assert r.status_code == 403  # HTTPBearer itself rejects -- no header at all


def test_create_community_with_bad_token_rejected(client):
    r = client.post("/communities", json={"name": "python"}, headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401  # our own check inside get_current_user


def test_create_community_success(client, auth_headers):
    r = client.post("/communities", json={"name": "python", "description": "py talk"}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "python"
    assert body["owner_id"] == 1


def test_create_duplicate_community_name_rejected(client, auth_headers):
    client.post("/communities", json={"name": "python"}, headers=auth_headers)
    r = client.post("/communities", json={"name": "python"}, headers=auth_headers)
    assert r.status_code == 409


def test_list_communities_requires_no_auth(client, auth_headers):
    client.post("/communities", json={"name": "python"}, headers=auth_headers)
    r = client.get("/communities")  # no headers at all
    assert r.status_code == 200
    assert len(r.json()) == 1
