from test_native_storage import env, folder, upload


def batch(client, action, ids, parent_id=None):
    response = client.post(
        "/api/files/batch", json={"action": action, "ids": ids, "parent_id": parent_id}
    )
    assert response.status_code == 200, response.text
    return {item["id"]: item["status"] for item in response.json()["items"]}


def test_batch_move_keeps_child_with_selected_folder(env):
    client, _ = env
    source = folder(client, "Source")
    destination = folder(client, "Destination")
    item, _ = upload(client, parent=source)
    assert batch(client, "move", [item["id"], source, item["id"]], destination) == {
        source: "applied",
        item["id"]: "covered",
    }
    assert client.get(f"/api/files/{source}").json()["parent_id"] == destination
    assert client.get(f"/api/files/{item['id']}").json()["parent_id"] == source


def test_batch_move_reports_conflict_stale_item_and_denied_item(env):
    client, _ = env
    destination = folder(client, "Destination")
    conflict = folder(client, "Conflict")
    folder(client, "Conflict", destination)
    movable = folder(client, "Movable")
    stale = folder(client, "Trashed")
    assert client.post(f"/api/files/{stale}/trash").status_code == 200
    with_other_user = client.post(
        "/api/files/folders", json={"name": "Other user's folder"}, headers={"x-test-user": "2"}
    )
    other_id = with_other_user.json()["id"]
    assert batch(client, "move", [conflict, movable, stale, other_id], destination) == {
        conflict: "failed",
        movable: "applied",
        stale: "failed",
        other_id: "failed",
    }
    assert client.get(f"/api/files/{movable}").json()["parent_id"] == destination
    assert client.get(f"/api/files/{conflict}").json()["parent_id"] is None
    assert client.get(f"/api/files/{other_id}", headers={"x-test-user": "2"}).json()["parent_id"] is None


def test_batch_trash_covers_selected_children_and_restores_as_a_tree(env):
    client, _ = env
    source = folder(client, "Source")
    item, _ = upload(client, parent=source)
    assert batch(client, "trash", [item["id"], source]) == {source: "applied", item["id"]: "covered"}
    assert [item["id"] for item in client.get("/api/files?trash=true").json()["items"]] == [source]
    assert client.post(f"/api/files/{source}/restore").status_code == 200
    assert client.get(f"/api/files/{item['id']}").json()["parent_id"] == source
