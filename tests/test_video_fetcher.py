"""
Unit tests cho module video_fetcher và tính năng lấy video b-roll:
- Kiểm tra dịch từ khóa tiếng Việt sang tiếng Anh cho video.
- Kiểm tra quét thư viện video b-roll cục bộ.
- Kiểm tra trích xuất frame từ video footage bằng FFmpeg.
- Kiểm tra tìm kiếm video Pixabay.
- Kiểm tra render quote lên video footage chuẩn 1080x1920 và No Audio.
"""

from pathlib import Path
import pytest

from modules.video_fetcher import (
    VIDEO_QUICK_THEMES_VI,
    translate_vi_to_video_query,
    get_local_footages,
    extract_video_frame,
    search_pixabay_videos,
)
from modules.video_renderer import render_video_from_footage, render_any_media_quote
from modules.video_engine import probe_video_metadata


def test_translate_vi_to_video_query_quick_themes():
    """Kiểm tra dịch các chủ đề video 1 chạm chuẩn xác."""
    for theme_label, expected_kw in VIDEO_QUICK_THEMES_VI.items():
        translated = translate_vi_to_video_query(theme_label)
        assert translated == expected_kw


def test_translate_vi_to_video_query_custom_text():
    """Kiểm tra dịch từ khóa tự nhập tiếng Việt."""
    q1 = translate_vi_to_video_query("con sói")
    assert "wolf" in q1

    q2 = translate_vi_to_video_query("trời mưa ban đêm")
    assert "rain" in q2
    assert "night" in q2


def test_get_local_footages():
    """Kiểm tra quét kho video cục bộ assets/footages/."""
    footages = get_local_footages()
    assert len(footages) >= 4
    for f in footages:
        assert Path(f["path"]).exists()
        assert f["filename"].endswith(".mp4")
        assert f["size_mb"] > 0
        assert f["name"] != ""


def test_extract_video_frame(tmp_path: Path):
    """Kiểm tra trích xuất 1 khung hình từ video để làm ảnh xem trước."""
    footages = get_local_footages()
    sample_vid = footages[0]["path"]
    out_frame = tmp_path / "frame_test.jpg"

    res = extract_video_frame(sample_vid, output_path=out_frame, timestamp_sec=1.0)
    assert res.exists()
    assert res.stat().st_size > 1000


def test_search_pixabay_videos_mock_or_live():
    """Kiểm tra tìm kiếm video Pixabay trả về đúng cấu trúc hit."""
    results = search_pixabay_videos("rain", per_page=3, page=1)
    # Nếu có API key và mạng, kết quả trả về danh sách dict
    assert isinstance(results, list)
    if results:
        v = results[0]
        assert "id" in v
        assert "download_url" in v
        assert "thumbnail" in v
        assert "duration" in v


def test_render_video_from_footage(tmp_path: Path):
    """Kiểm tra render quote lên video footage chuẩn TikTok 1080x1920 không tiếng."""
    footages = get_local_footages()
    sample_vid = footages[0]["path"]
    out_mp4 = tmp_path / "test_render.mp4"

    rendered = render_video_from_footage(
        footage_path=sample_vid,
        quote="Hạnh phúc giản đơn là những khoảnh khắc bình yên.",
        output_path=out_mp4,
        duration=5.0,
        signature="saigonbac",
    )

    assert rendered.exists()
    assert rendered.stat().st_size > 10000

    meta = probe_video_metadata(rendered)
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["has_audio"] is False
    assert 4.5 <= meta["duration"] <= 6.0


def test_render_any_media_quote_dispatch(tmp_path: Path):
    """Kiểm tra dispatch tự động giữa video và ảnh tĩnh."""
    footages = get_local_footages()
    sample_vid = footages[0]["path"]
    out_mp4 = tmp_path / "test_dispatch_vid.mp4"

    res_vid = render_any_media_quote(
        media_path=sample_vid,
        quote="Bình yên là nhà.",
        output_path=out_mp4,
        duration=5.0,
    )
    assert res_vid.exists()
    meta_vid = probe_video_metadata(res_vid)
    assert meta_vid["has_audio"] is False
