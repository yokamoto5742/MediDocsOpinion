from datetime import datetime
from fastapi import status


def test_get_summary_empty(client, test_db):
    """統計サマリー取得 - データなし"""
    response = client.get("/api/statistics/summary")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == 0
    assert data["total_input_tokens"] == 0
    assert data["total_output_tokens"] == 0
    assert data["average_processing_time"] == 0


def test_get_summary_with_data(client, sample_usage_records):
    """統計サマリー取得 - データあり"""
    response = client.get("/api/statistics/summary")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == 2
    assert data["total_input_tokens"] == 3000
    assert data["total_output_tokens"] == 1300
    assert 2.0 < data["average_processing_time"] < 3.5


def test_get_summary_filtered_by_model(client, sample_usage_records):
    """統計サマリー取得 - モデルフィルター"""
    response = client.get("/api/statistics/summary?model=Claude")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == 1
    assert data["total_input_tokens"] == 1000
    assert data["total_output_tokens"] == 500


def test_get_summary_filtered_by_date(client, sample_usage_records):
    """統計サマリー取得 - 日付フィルター"""
    start_date = datetime.now().isoformat()
    response = client.get(f"/api/statistics/summary?start_date={start_date}")
    assert response.status_code == status.HTTP_200_OK


def test_get_records_empty(client, test_db):
    """使用統計レコード取得 - データなし"""
    response = client.get("/api/statistics/records")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_get_records_with_data(client, sample_usage_records):
    """使用統計レコード取得 - データあり"""
    response = client.get("/api/statistics/records")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["department"] in ["眼科", "default"]


def test_get_records_with_pagination(client, sample_usage_records):
    """使用統計レコード取得 - ページネーション"""
    response = client.get("/api/statistics/records?limit=1&offset=0")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1

    response = client.get("/api/statistics/records?limit=1&offset=1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1


def test_get_records_respects_limit(client, sample_usage_records):
    """使用統計レコード取得 - limit制限"""
    response = client.get("/api/statistics/records?limit=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) <= 10
