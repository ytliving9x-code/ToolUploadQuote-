"""
Unit tests cho module pexels_api: kiểm tra thuật toán chọn video file tối ưu (gần 1080px, portrait),
bỏ qua 4K, lọc thời lượng và loại trừ footage đã sử dụng.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from modules.history_db import init_db, mark_footage_used
from modules.pexels_api import find_and_select_footage, select_best_video_file


def test_select_best_video_file_prefers_1080_portrait():
    """Kiểm tra chọn chính xác file portrait 1080x1920 khi có nhiều độ phân giải."""
    files = [
        {"id": 1, "width": 1920, "height": 1080, "file_type": "video/mp4", "link": "http://example.com/landscape.mp4"},
        {"id": 2, "width": 2160, "height": 3840, "file_type": "video/mp4", "link": "http://example.com/4k.mp4"},
        {"id": 3, "width": 720, "height": 1280, "file_type": "video/mp4", "link": "http://example.com/720p.mp4"},
        {"id": 4, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": "http://example.com/1080p.mp4"},
    ]
    best = select_best_video_file(files, target_width=1080)
    assert best is not None
    assert best["id"] == 4
    assert best["width"] == 1080
    assert best["height"] == 1920


def test_select_best_video_file_avoids_4k_when_lower_res_available():
    """Kiểm tra ưu tiên độ phân giải thấp hơn (720p) thay vì tải 4K (2160p) tốn băng thông."""
    files = [
        {"id": 1, "width": 2160, "height": 3840, "file_type": "video/mp4", "link": "http://example.com/4k.mp4"},
        {"id": 2, "width": 720, "height": 1280, "file_type": "video/mp4", "link": "http://example.com/720p.mp4"},
    ]
    best = select_best_video_file(files, target_width=1080)
    assert best is not None
    assert best["id"] == 2
    assert best["width"] == 720


def test_select_best_video_file_filters_invalid_types():
    """Kiểm tra loại bỏ các định dạng không phải MP4 hoặc không có link."""
    files = [
        {"id": 1, "width": 1080, "height": 1920, "file_type": "video/webm", "link": "http://example.com/vid.webm"},
        {"id": 2, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": ""},
        {"id": 3, "width": 720, "height": 1280, "file_type": "video/mp4", "link": "http://example.com/vid.mp4"},
    ]
    best = select_best_video_file(files, target_width=1080)
    assert best is not None
    assert best["id"] == 3


def test_select_best_video_file_empty():
    """Kiểm tra xử lý danh sách rỗng."""
    assert select_best_video_file([]) is None


def test_find_and_select_footage_filtering(tmp_path: Path):
    """Kiểm tra lọc video theo thời lượng >= 8s và bỏ qua video đã từng dùng."""
    test_db = tmp_path / "test_history.db"
    init_db(test_db)

    # Đánh dấu video ID 102 là đã dùng
    mark_footage_used(pexels_video_id=102, custom_path=test_db)

    mock_search_response = {
        "videos": [
            # Video 101: quá ngắn (5s < 8s) -> Bị loại
            {
                "id": 101,
                "duration": 5,
                "video_files": [{"id": 1, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": "http://vid1.mp4"}]
            },
            # Video 102: độ dài đủ (12s) nhưng ĐÃ DÙNG -> Bị loại
            {
                "id": 102,
                "duration": 12,
                "video_files": [{"id": 2, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": "http://vid2.mp4"}]
            },
            # Video 103: hợp lệ (10s, chưa dùng) -> Được chọn!
            {
                "id": 103,
                "duration": 10,
                "video_files": [{"id": 3, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": "http://vid3.mp4"}]
            },
        ]
    }

    with patch("modules.pexels_api.search_pexels_videos", return_value=mock_search_response):
        result = find_and_select_footage(
            keywords=["rain night"],
            min_duration=8,
            api_key="mock_key",
            custom_db_path=test_db
        )

        assert result is not None
        vid, chosen_file, matched_kw = result
        assert vid["id"] == 103
        assert chosen_file["id"] == 3
        assert matched_kw == "rain night"
