"""
Unit tests cho modules video_engine và exporter:
- Kiểm tra ngắt dòng thông minh bằng tiếng Việt.
- Kiểm tra tạo ảnh overlay trong suốt RGBA.
- Kiểm tra xuất video và caption.txt vào output/cho_dang.
- Kiểm tra chuyển video sang output/da_dang.
"""

from pathlib import Path
from PIL import ImageFont
import pytest

from modules.exporter import export_to_pending, list_pending_items, mark_as_published
from modules.history_db import init_db, save_quote
from modules.video_engine import create_text_overlay_image, get_font, probe_video_metadata, wrap_text_to_lines


def test_wrap_text_to_lines_short():
    """Kiểm tra câu ngắn chỉ chiếm 1-2 dòng."""
    font = get_font(font_size=54)
    text = "Bình yên trong tâm hồn."
    lines = wrap_text_to_lines(text, font, max_width=900)
    assert len(lines) == 1
    assert lines[0] == "Bình yên trong tâm hồn."


def test_wrap_text_to_lines_long():
    """Kiểm tra câu dài tự động ngắt thành các dòng hợp lý."""
    font = get_font(font_size=54)
    text = "Bão giông ngoài kia không làm bạn ngã gục. Chỉ có sự rối loạn bên trong mới khiến bạn đánh mất chính mình."
    lines = wrap_text_to_lines(text, font, max_width=900)
    assert 2 <= len(lines) <= 4
    # Ghép lại phải đủ từ không bị mất
    reconstructed = " ".join(lines)
    assert reconstructed == text


def test_create_text_overlay_image():
    """Kiểm tra tạo ảnh chữ Pillow RGBA chuẩn 1080x1920."""
    font = get_font(font_size=54)
    lines = ["Nước sâu tĩnh lặng", "Lúa chín cúi đầu"]
    img = create_text_overlay_image(lines, font, canvas_size=(1080, 1920))
    assert img.size == (1080, 1920)
    assert img.mode == "RGBA"


def test_export_and_publish_flow(tmp_path: Path):
    """Kiểm tra quy trình xuất file vào chờ đăng và chuyển sang đã đăng."""
    test_db = tmp_path / "test_history.db"
    init_db(test_db)

    # 1. Tạo file video giả lập
    src_video = tmp_path / "sample_video.mp4"
    src_video.write_bytes(b"dummy video data")

    cho_dang_dir = tmp_path / "cho_dang"
    da_dang_dir = tmp_path / "da_dang"

    quote_data = {
        "quote": "Kiên trì trong âm thầm.",
        "caption": "Mỗi ngày nỗ lực thêm 1%",
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan"],
        "pexels_url": "https://www.pexels.com/video/123",
        "video_id": 123,
    }
    quote_id = save_quote(quote_data, topic="nỗ lực", custom_path=test_db)
    quote_data["quote_id"] = quote_id

    # 2. Xuất vào chờ đăng
    out_mp4, out_txt = export_to_pending(
        rendered_video_path=src_video,
        quote_data=quote_data,
        output_dir=cho_dang_dir,
        custom_db_path=test_db,
    )

    assert out_mp4.exists()
    assert out_txt.exists()
    assert out_mp4.suffix == ".mp4"
    assert out_txt.suffix == ".txt"

    # Đọc nội dung file text
    content = out_txt.read_text(encoding="utf-8")
    assert "Mỗi ngày nỗ lực thêm 1%" in content
    assert "#phattrienbanthan" in content

    # Kiểm tra danh sách chờ đăng
    pending_items = list_pending_items(output_dir=cho_dang_dir)
    assert len(pending_items) == 1

    # 3. Đánh dấu đã đăng
    pub_mp4, pub_txt = mark_as_published(
        video_path=out_mp4,
        output_dir_published=da_dang_dir,
        custom_db_path=test_db,
    )
    assert pub_mp4.exists()
    assert pub_txt.exists()
    assert not out_mp4.exists()  # Đã di chuyển khỏi chờ đăng
