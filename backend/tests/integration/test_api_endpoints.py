import io
import uuid
from http import HTTPStatus

from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from tests.conftest import TOPIC_CONF_THRESHOLD


def test_get_groups_empty(client: TestClient):
    response = client.get("/groups")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert isinstance(data, list)
    # В новой БД список должен быть пуст
    assert len(data) == 0

def test_get_groups_with_data(
        client: TestClient,
        db_session: Session,
        test_group_id: str,
):
    # Создаем тестовый креатив, чтобы группа появилась
    creative = Creative(
        creative_id=str(uuid.uuid4()),
        group_id=test_group_id,
        original_filename="test.jpg",
        file_path=f"creatives/{uuid.uuid4()!s}.jpg",
        file_size=1024,
        file_format="jpg",
        image_width=800,
        image_height=600,
    )
    db_session.add(creative)
    db_session.commit()

    response = client.get("/groups")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    group_ids = [g['group_id'] for g in data]
    assert test_group_id in group_ids

def test_get_creative_not_found(client: TestClient):
    fake_id = "non-existent-id"
    response = client.get(f"/creatives/{fake_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_get_creative_success(
        client: TestClient,
        db_session: Session,  # noqa: ARG001
        create_test_creative,
        create_test_analysis,  # noqa: ARG001
):

    creative_id = create_test_creative.creative_id
    response = client.get(f"/creatives/{creative_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data["creative_id"] == creative_id
    assert data["overall_status"] == "SUCCESS"
    assert data["main_topic"] == "clocks"
    assert data["topic_confidence"] == TOPIC_CONF_THRESHOLD

def test_upload_files_success(client: TestClient, test_group_id: str):
    # Создаем временную картинку в памяти
    img_byte_arr = io.BytesIO()
    image = Image.new('RGB', (100, 100), color = 'red')
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    files = [
        ("files", ("test_image1.jpg", img_byte_arr, "image/jpeg")),
    ]
    creative_id = str(uuid.uuid4())
    data = {
        "group_id": test_group_id,
        "creative_ids": [creative_id],
        "original_filenames": ["test_image1.jpg"],
    }

    response = client.post("/upload", files=files, data=data)
    assert response.status_code == HTTPStatus.OK
    json_data = response.json()
    assert "uploaded" in json_data

def test_upload_files_mismatched_data(client: TestClient, test_group_id: str):
    img_byte_arr = io.BytesIO()
    image = Image.new('RGB', (100, 100))
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    files = [
        ("files", ("test_image1.jpg", img_byte_arr, "image/jpeg")),
        ("files", ("test_image2.jpg", img_byte_arr, "image/jpeg")),
    ]
    data = {
        "group_id": test_group_id,
        "creative_ids": [str(uuid.uuid4())],
        "original_filenames": ["test_image1.jpg"],
    }

    response = client.post("/upload", files=files, data=data)
    assert response.status_code == HTTPStatus.BAD_REQUEST

def test_get_status_not_found(client: TestClient):
    fake_id = "non-existent-id"
    response = client.get(f"/status/{fake_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_get_status_pending(
        client: TestClient,
        db_session: Session,
        create_test_creative,
):
    creative_id = create_test_creative.creative_id
    analysis = CreativeAnalysis(creative_id=creative_id)
    db_session.add(analysis)
    db_session.commit()

    response = client.get(f"/status/{creative_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["creative_id"] == creative_id

def test_get_analytics_empty(client: TestClient):
    # Запрашиваем аналитику для несуществующей группы
    response = client.get("/analytics/group/non_existent_group_id")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_get_analytics_all_empty(client: TestClient):
     # Запрашиваем общую аналитику, когда данных нет
     response = client.get("/analytics/all")
     assert response.status_code == HTTPStatus.OK
     data = response.json()
     assert isinstance(data, dict)
