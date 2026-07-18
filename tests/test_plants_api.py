def create_plant(client, **overrides):
    data = {
        "common_name": "Test Pothos",
        "collection": "Living Room",
        "tags": "test,aroid",
        "quantity": 3,
        "for_sale": False,
        "user_notes": "pytest",
    }
    data.update(overrides)
    response = client.post("/api/v1/plants", data=data)
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_create_and_get_plant(client):
    plant = create_plant(client)
    assert plant["common_name"] == "Test Pothos"
    assert plant["quantity"] == 3
    assert sorted(plant["tags"]) == ["aroid", "test"]
    assert plant["vault_note_path"] is not None

    fetched = client.get(f"/api/v1/plants/{plant['id']}").json()
    assert fetched["id"] == plant["id"]


def test_list_filters_by_collection_and_tag(client):
    p1 = create_plant(client, common_name="Pothos A", collection="Living Room", tags="climbing")
    create_plant(client, common_name="Cactus B", collection="Office", tags="succulent")

    by_collection = client.get("/api/v1/plants", params={"collection": "Living Room"}).json()
    assert [p["id"] for p in by_collection] == [p1["id"]]

    by_tag = client.get("/api/v1/plants", params={"tag": "climbing"}).json()
    assert [p["id"] for p in by_tag] == [p1["id"]]


def test_search_query(client):
    p1 = create_plant(client, common_name="Monstera", user_notes="loves humidity")
    create_plant(client, common_name="Snake Plant", user_notes="very hardy")

    results = client.get("/api/v1/plants", params={"q": "humidity"}).json()
    assert [p["id"] for p in results] == [p1["id"]]


def test_patch_updates_quantity_and_tags(client):
    plant = create_plant(client)
    response = client.patch(f"/api/v1/plants/{plant['id']}", json={"quantity": 7, "tags": ["rare"]})
    assert response.status_code == 200
    updated = response.json()
    assert updated["quantity"] == 7
    assert updated["tags"] == ["rare"]


def test_delete_removes_plant_and_archives_note(client):
    plant = create_plant(client)
    note_path = plant["vault_note_path"]

    response = client.delete(f"/api/v1/plants/{plant['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/plants/{plant['id']}").status_code == 404

    from app.config import settings

    assert not (settings.vault_local_path / note_path).exists()
    assert (settings.vault_local_path / "Archive/Plants" / note_path.split("/")[-1]).exists()


def test_tags_and_collections_endpoints(client):
    create_plant(client, common_name="A", collection="Greenhouse", tags="rare,tall")
    create_plant(client, common_name="B", collection="Office", tags="rare")

    assert client.get("/api/v1/tags").json() == ["rare", "tall"]
    assert client.get("/api/v1/collections").json() == ["Greenhouse", "Office"]


def test_genus_derived_and_filterable(client):
    p1 = create_plant(client, common_name="Deliciosa", species_scientific="Monstera deliciosa")
    create_plant(client, common_name="Zebrina", species_scientific="Alocasia zebrina")

    assert p1["genus"] == "Monstera"
    assert client.get("/api/v1/genera").json() == ["Alocasia", "Monstera"]

    by_genus = client.get("/api/v1/plants", params={"genus": "Monstera"}).json()
    assert [p["id"] for p in by_genus] == [p1["id"]]


def test_sort_by_name_and_quantity(client):
    create_plant(client, common_name="Zamioculcas", quantity=1)
    create_plant(client, common_name="Alocasia", quantity=5)

    by_name = client.get("/api/v1/plants", params={"sort": "name"}).json()
    assert [p["common_name"] for p in by_name] == ["Alocasia", "Zamioculcas"]

    by_quantity_desc = client.get("/api/v1/plants", params={"sort": "-quantity"}).json()
    assert [p["common_name"] for p in by_quantity_desc] == ["Alocasia", "Zamioculcas"]


def test_photo_upload_delete_and_set_primary(client):
    plant = create_plant(client)
    plant_id = plant["id"]

    def upload(name: str):
        response = client.post(
            f"/api/v1/plants/{plant_id}/photos",
            files={"photo": (name, b"fake-image-bytes", "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = upload("one.jpg")
    second = upload("two.jpg")
    assert first["is_primary"] is True
    assert second["is_primary"] is False

    set_primary = client.post(f"/api/v1/plants/{plant_id}/photos/{second['id']}/set-primary")
    assert set_primary.status_code == 200
    photos = {p["id"]: p["is_primary"] for p in set_primary.json()["photos"]}
    assert photos[second["id"]] is True
    assert photos[first["id"]] is False

    delete_primary = client.delete(f"/api/v1/plants/{plant_id}/photos/{second['id']}")
    assert delete_primary.status_code == 204

    remaining = client.get(f"/api/v1/plants/{plant_id}").json()["photos"]
    assert len(remaining) == 1
    assert remaining[0]["id"] == first["id"]
    assert remaining[0]["is_primary"] is True  # promoted after primary was deleted
