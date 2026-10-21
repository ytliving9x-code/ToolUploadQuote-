"""
Unit tests cho tính năng phân tách 2 kênh TikTok:
- Kiểm tra cấu hình channels trong config.json.
- Kiểm tra AI sinh quote theo 2 phong cách khác nhau: sad_introspective (saigonbac) và deep_philosophical (kênh mới).
- Kiểm tra xuất file video vào đúng thư mục độc lập của từng kênh.
"""

import json
from pathlib import Path
import pytest

from modules.quote_gen import build_system_prompt, generate_quote, get_fallback_quote
from modules.video_renderer import render_18s_video, render_video_from_footage
from modules.video_fetcher import get_local_footages


def test_config_channels_structure():
    """Kiểm tra cấu hình phân tách 2 kênh trong config.json."""
    cfg_path = Path("config.json")
    assert cfg_path.exists()
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    assert "channels" in cfg
    channels = cfg["channels"]
    assert "saigonbac" in channels
    assert "new_channel" in channels

    # Kiểm tra kênh saigonbac
    sg = channels["saigonbac"]
    assert sg["signature"] == "saigonbac"
    assert sg["format"] == "photo_18s"
    assert "saigonbac" in sg["output_folder"]
    assert len(sg["topics"]) == 6
    assert "nhẫn nhịn và chờ thời" not in sg["topics"]
    assert "Tĩnh Tại & Chữa Lành" in sg["topics"]

    # Kiểm tra kênh Lặng
    new_ch = channels["new_channel"]
    assert new_ch["format"] == "video_broll"
    assert "kenh_moi" in new_ch["output_folder"]
    assert len(new_ch["topics"]) == 6
    assert "Mưu lược Tư Mã Ý (Ẩn nhẫn)" in new_ch["topics"]
    assert "Lặng" in new_ch["channel_name"]


def test_quote_styles_prompt_differentiation():
    """Kiểm tra prompt sinh quote được phân hóa và khóa ranh giới 100% DNA giữa 2 kênh."""
    prompt_sg = build_system_prompt(topic="Tĩnh Tại & Chữa Lành", channel="saigonbac")
    assert "saigonbac" in prompt_sg or "Trạm Dừng Cảm Xúc" in prompt_sg
    assert "CẤM dạy đời" in prompt_sg
    assert 'cấm dùng từ "bạn"' in prompt_sg or 'CẤM dùng từ "bạn"' in prompt_sg
    assert "CẤM dùng các từ ngữ sến súa" in prompt_sg
    assert "Tĩnh Tại & Chữa Lành" in prompt_sg

    prompt_new = build_system_prompt(topic="Mưu lược Tư Mã Ý (Ẩn nhẫn)", channel="kenh_moi")
    assert "Tư Mã Ý" in prompt_new
    assert "TUYỆT ĐỐI KHÔNG viết giọng than thân trách phận" in prompt_new
    assert "Mưu lược Tư Mã Ý (Ẩn nhẫn)" in prompt_new
    assert "saigonbac" not in prompt_new


def test_quotes_json_and_channel_isolation():
    """Kiểm tra cấu trúc quotes.json phân 2 nhánh độc lập và số lượng câu quote."""
    from modules.quote_manager import load_all_quotes, get_all_categories
    
    # 1. Kênh saigonbac
    sg_quotes = load_all_quotes(channel="saigonbac")
    assert len(sg_quotes) == 24
    sg_cats = get_all_categories(channel="saigonbac")
    assert "nhẫn nhịn và chờ thời" not in sg_cats
    assert "Tĩnh Tại & Chữa Lành" in sg_cats
    assert "Khoảng Lặng Vô Thanh" in sg_cats

    # 2. Kênh Mới (Tư Mã Ý)
    km_quotes = load_all_quotes(channel="kenh_moi")
    assert len(km_quotes) == 30
    km_cats = get_all_categories(channel="kenh_moi")
    assert "Mưu lược Tư Mã Ý (Ẩn nhẫn)" in km_cats
    assert "Bản chất của Tiền & Vị thế" in km_cats


def test_generate_quote_with_styles(tmp_path: Path):
    """Kiểm tra sinh quote fallback theo từng chủ đề và channel của 2 kênh."""
    # Kênh saigonbac
    q_sg = get_fallback_quote("Tĩnh Tại & Chữa Lành", channel="saigonbac", custom_db_path=tmp_path / "hist.db")
    assert q_sg["quote"] != ""
    assert q_sg["channel"] == "saigonbac"

    # Kênh mới
    q_new = get_fallback_quote("Mưu lược Tư Mã Ý (Ẩn nhẫn)", channel="kenh_moi", custom_db_path=tmp_path / "hist.db")
    assert q_new["quote"] != ""
    assert q_new["channel"] == "kenh_moi"


def test_isolated_render_folders(tmp_path: Path):
    """Kiểm tra render và lưu vào 2 thư mục riêng biệt của từng kênh."""
    footages = get_local_footages()
    sample_vid = footages[0]["path"]

    # 1. Thư mục kênh saigonbac
    sg_dir = tmp_path / "output" / "saigonbac"
    sg_dir.mkdir(parents=True, exist_ok=True)
    out_sg = sg_dir / "tiktok_saigonbac_test.mp4"

    # Dùng frame đầu làm ảnh nền test cho saigonbac
    from modules.video_fetcher import extract_video_frame
    bg_img = extract_video_frame(sample_vid, tmp_path / "bg_sg.jpg")

    rendered_sg = render_18s_video(
        image_path=bg_img,
        quote="Có những ngày chỉ muốn bình yên.",
        output_path=out_sg,
        duration=2.0,  # Thời lượng ngắn phục vụ test
        signature="saigonbac",
    )
    assert rendered_sg.exists()
    assert "saigonbac" in str(rendered_sg.parent)

    # 2. Thư mục Kênh Mới
    new_dir = tmp_path / "output" / "kenh_moi"
    new_dir.mkdir(parents=True, exist_ok=True)
    out_new = new_dir / "tiktok_broll_test.mp4"

    rendered_new = render_video_from_footage(
        footage_path=sample_vid,
        quote="Kỷ luật tạo nên bản lĩnh.",
        output_path=out_new,
        duration=3.0,
        signature="saigonchill",
    )
    assert rendered_new.exists()
    assert "kenh_moi" in str(rendered_new.parent)


def test_review_viral_potential():
    """Kiểm tra chức năng AI thẩm định tiềm năng Viral của quote."""
    from modules.quote_gen import review_viral_potential

    # 1. Test quote đạt tiêu chuẩn cho kênh saigonbac
    good_quote = "Sài Gòn những ngày mưa rơi lặng lẽ, lòng người bỗng chùng xuống vì những vết thương chưa lành."
    review_sg = review_viral_potential(good_quote, channel_style="sad_introspective")
    assert "score" in review_sg
    assert 50 <= review_sg["score"] <= 100
    assert "verdict" in review_sg
    assert review_sg["word_count"] > 0
    assert "strengths" in review_sg
    assert "suggestions" in review_sg

    # 2. Test quote cho Kênh Mới (triết lý / bản lĩnh)
    quote_new = "Kỷ luật không phải là sự giam cầm, mà là chìa khóa duy nhất mở ra tự do của một người trưởng thành."
    review_new = review_viral_potential(quote_new, channel_style="deep_philosophical")
    assert review_new["score"] >= 60
    assert "verdict" in review_new
    assert len(review_new["strengths"]) > 0
    assert len(review_new["suggestions"]) > 0


def test_retro_comic_slide_generation(tmp_path: Path):
    """Kiểm tra tạo slide ảnh Retro Comic 1080x1920 cho TikTok Photo Mode của Kênh Lặng."""
    from modules.video_engine import generate_retro_comic_slide
    sample_img = Path("assets/samples/retro_comic/sample_stoic_man.jpg")
    out_slide = tmp_path / "test_slide.jpg"
    res = generate_retro_comic_slide(
        image_path=sample_img,
        quote="Cạn túi một lần để nhìn thấu lòng người.",
        output_path=out_slide,
        font_family="PatrickHand-Regular.ttf",
        font_size=52,
        position="upper_center",
        all_caps=True,
        signature="— LẶNG —",
    )
    assert res.exists()
    assert res.stat().st_size > 10000
