"""
Unit tests cho tính năng cào tranh Pinterest và sinh ảnh AI FLUX.1 (Kênh Lặng).
"""

from pathlib import Path
from PIL import Image
import pytest

from modules.pinterest_fetcher import (
    PINTEREST_CURATED_THEMES,
    crop_to_tiktok_portrait,
    get_cached_pinterest_images,
)
from modules.ai_image_gen import (
    RETRO_COMIC_PRESETS,
    generate_retro_comic_image,
)


def test_pinterest_curated_themes():
    """Kiểm tra danh mục chủ đề Pinterest được chuẩn hóa theo gu Just.breathe."""
    assert len(PINTEREST_CURATED_THEMES) >= 5
    assert "👫 Cặp Đôi Lãng Mạn (Gu Just.breathe)" in PINTEREST_CURATED_THEMES
    assert "♟️ Bàn Cờ & Mưu Lược (Tư Mã Ý)" in PINTEREST_CURATED_THEMES
    assert "ligne claire" in PINTEREST_CURATED_THEMES["👫 Cặp Đôi Lãng Mạn (Gu Just.breathe)"]


def test_crop_to_tiktok_portrait(tmp_path: Path):
    """Kiểm tra thuật toán crop ảnh tỷ lệ dọc 1080x1920 (9:16)."""
    # Tạo ảnh vuông test 800x800
    test_img_path = tmp_path / "square.jpg"
    img = Image.new("RGB", (800, 800), color=(120, 60, 40))
    img.save(test_img_path, "JPEG")

    cropped = crop_to_tiktok_portrait(test_img_path, width=1080, height=1920)
    assert cropped.exists()

    with Image.open(cropped) as res:
        assert res.size == (1080, 1920)


def test_retro_comic_presets_exist():
    """Kiểm tra các preset tranh Retro Comic cho Kênh Lặng."""
    assert len(RETRO_COMIC_PRESETS) >= 6
    assert "🌧️ Bên Cửa Sổ Mưa Đêm (Trầm Tư & Bản Lĩnh)" in RETRO_COMIC_PRESETS
    assert "♟️ Bàn Cờ Tư Mã Ý (Mưu Lược & Ẩn Nhẫn)" in RETRO_COMIC_PRESETS


def test_get_cached_pinterest_images():
    """Kiểm tra hàm quét ảnh Pinterest từ cache."""
    cached = get_cached_pinterest_images(limit=5)
    assert isinstance(cached, list)
    if cached:
        assert "path" in cached[0]
        assert Path(cached[0]["path"]).exists()
