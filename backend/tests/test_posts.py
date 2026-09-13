import pytest


@pytest.fixture
def community(client, auth_headers):
    r = client.post("/communities", json={"name": "python"}, headers=auth_headers)
    return r.json()["id"]


def test_create_post_requires_auth(client, community):
    r = client.post(f"/communities/{community}/posts", json={"title": "hi"})
    assert r.status_code == 403


def test_create_post_in_nonexistent_community_404(client, auth_headers):
    r = client.post("/communities/9999/posts", json={"title": "ghost"}, headers=auth_headers)
    assert r.status_code == 404


def test_create_post_success(client, auth_headers, community):
    r = client.post(f"/communities/{community}/posts", json={"title": "hello", "content": "world"}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "hello"
    assert body["author_id"] == 1
    assert body["community_id"] == community


def test_list_posts_nonexistent_community_404(client):
    r = client.get("/communities/9999/posts")
    assert r.status_code == 404


def test_pagination_across_two_pages(client, auth_headers, community):
    for i in range(25):
        client.post(f"/communities/{community}/posts", json={"title": f"post {i}"}, headers=auth_headers)

    r = client.get(f"/communities/{community}/posts", params={"page": 1})
    data = r.json()
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert data["page"] == 1

    r = client.get(f"/communities/{community}/posts", params={"page": 2})
    data = r.json()
    assert len(data["items"]) == 5


def test_invalid_page_rejected(client, community):
    r = client.get(f"/communities/{community}/posts", params={"page": 0})
    assert r.status_code == 422


def test_page_size_over_max_rejected(client, community):
    r = client.get(f"/communities/{community}/posts", params={"page_size": 9999})
    assert r.status_code == 422
