import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from main import app
from auth import get_current_user

client = TestClient(app)

# Override the auth dependency for all tests to act as an authenticated Professor
def override_get_current_user():
    return {"user_id": str(uuid.uuid4()), "role": "professor", "email": "prof@test.com"}

app.dependency_overrides[get_current_user] = override_get_current_user


def test_compare_rejects_identical_submissions():
    """Ensure the engine correctly rejects requests to compare a submission against itself."""
    sub_id = str(uuid.uuid4())
    assign_id = str(uuid.uuid4())
    
    response = client.post(
        f"/engine/assignments/{assign_id}/compare",
        json={"submission_a_id": sub_id, "submission_b_id": sub_id}
    )
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


@patch("routes_engine.get_db_connection")
def test_list_submissions_endpoint(mock_get_db):
    """Ensure the endpoint fetches available submissions without failure using mocked DB."""
    assign_id = str(uuid.uuid4())
    
    # Mock the database connection context manager
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    
    # Mock the fetchall response from the DB query (empty list of submissions)
    mock_cursor.fetchall.return_value = []
    
    mock_get_db.return_value = mock_conn
    
    response = client.get(f"/engine/assignments/{assign_id}/submissions")
    
    assert response.status_code == 200
    assert response.json() == []


@patch("routes_engine.get_db_connection")
def test_similarity_score_rejects_identical_queries(mock_get_db):
    """Ensure getting similarity score fails if both IDs are the same."""
    sub_id = str(uuid.uuid4())
    
    response = client.get(
        f"/engine/similarity-score",
        params={"submission_a_id": sub_id, "submission_b_id": sub_id}
    )
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]
