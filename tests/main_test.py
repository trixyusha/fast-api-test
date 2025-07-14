import pytest
import httpx
from fastapi.testclient import TestClient
from main import app, datetime

client = TestClient(app)

@pytest.fixture
def auth_token():
    response = client.post("/token/", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_root_available():
    response = client.get("/")
    assert response.status_code in (200, 404)

def test_get_user(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/users/1", headers=headers)
    assert response.status_code == 200 or response.status_code == 404 or response.status_code == 400

def test_create_task(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    task_data = {
        "name": "сделать тесты",
        "description": "тут описание задачи",
        "create_date": str(datetime.now()),
        "update_date": None,
        "author": 1
    }
    response = client.post("/tasks/", json=task_data, headers=headers)
    assert response.status_code == 200

def test_get_tasks(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/tasks/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)