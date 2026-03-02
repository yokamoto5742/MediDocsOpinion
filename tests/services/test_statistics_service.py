from datetime import datetime, timedelta

from app.services import statistics_service


def test_get_usage_summary_empty(test_db):
    """使用統計サマリー取得 - データなし"""
    summary = statistics_service.get_usage_summary(test_db)
    assert summary["total_count"] == 0
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0
    assert summary["average_processing_time"] == 0


def test_get_usage_summary_with_data(test_db, sample_usage_records):
    """使用統計サマリー取得 - データあり"""
    summary = statistics_service.get_usage_summary(test_db)
    assert summary["total_count"] == 2
    assert summary["total_input_tokens"] == 3000
    assert summary["total_output_tokens"] == 1300
    assert 2.0 < summary["average_processing_time"] < 3.5


def test_get_usage_summary_filtered_by_model(test_db, sample_usage_records):
    """使用統計サマリー取得 - モデルフィルター"""
    summary = statistics_service.get_usage_summary(test_db, model="Claude")
    assert summary["total_count"] == 1
    assert summary["total_input_tokens"] == 1000
    assert summary["total_output_tokens"] == 500


def test_get_usage_summary_filtered_by_date_range(test_db, sample_usage_records):
    """使用統計サマリー取得 - 日付範囲フィルター"""
    now = datetime.now()
    start_date = now - timedelta(days=1)
    end_date = now + timedelta(days=1)

    summary = statistics_service.get_usage_summary(
        test_db,
        start_date=start_date,
        end_date=end_date,
    )
    assert summary["total_count"] == 2


def test_get_usage_summary_no_data_in_range(test_db, sample_usage_records):
    """使用統計サマリー取得 - 範囲外の日付"""
    start_date = datetime.now() + timedelta(days=10)
    end_date = datetime.now() + timedelta(days=20)

    summary = statistics_service.get_usage_summary(
        test_db,
        start_date=start_date,
        end_date=end_date,
    )
    assert summary["total_count"] == 0


def test_get_usage_records_empty(test_db):
    """使用統計レコード取得 - データなし"""
    records = statistics_service.get_usage_records(test_db)
    assert records == []


def test_get_usage_records_with_data(test_db, sample_usage_records):
    """使用統計レコード取得 - データあり"""
    records = statistics_service.get_usage_records(test_db)
    assert len(records) == 2
    assert records[0].department in ["眼科", "default"]


def test_get_usage_records_with_limit(test_db, sample_usage_records):
    """使用統計レコード取得 - limit指定"""
    records = statistics_service.get_usage_records(test_db, limit=1)
    assert len(records) == 1


def test_get_usage_records_with_offset(test_db, sample_usage_records):
    """使用統計レコード取得 - offset指定"""
    all_records = statistics_service.get_usage_records(test_db)
    offset_records = statistics_service.get_usage_records(test_db, offset=1)

    assert len(offset_records) == 1
    assert offset_records[0].id != all_records[0].id


def test_get_usage_records_ordering(test_db, sample_usage_records):
    """使用統計レコード取得 - 降順ソート"""
    records = statistics_service.get_usage_records(test_db)
    if len(records) >= 2:
        assert records[0].date >= records[1].date
