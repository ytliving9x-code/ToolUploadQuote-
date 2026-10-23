import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from modules.quote_gen import (
    generate_quote_from_user_prompt,
    generate_quote_from_inspiration_image,
)
from modules.video_renderer import render_18s_video
from modules.video_engine import probe_video_metadata
from app import crop_image_to_tiktok_portrait



def test_generate_quote_from_user_prompt_mocked():
    mock_quote = "Đi qua những ngày mưa bão mới hiểu được, bình yên lớn nhất chính là một buổi sáng ngồi ngắm nắng lên."
    with patch("modules.quote_gen.call_gemini", return_value=mock_quote):
        res = generate_quote_from_user_prompt(
            user_prompt="Bình yên sau bão giông",
            config={"llm_provider": "gemini"},
            check_duplicate=False,
        )
        assert res["quote"] == mock_quote
        assert res["channel"] == "saigonbac"
        assert res["is_ai_generated"] is True


def test_generate_quote_from_inspiration_image_mocked():
    mock_quote = "Sau giông bão, người ta chỉ mong một buổi sớm ngồi ngắm nắng lên yên bình."
    test_img = Image.new("RGB", (300, 300), color=(50, 60, 70))
    with patch("modules.quote_gen.call_gemini", return_value=mock_quote):
        res = generate_quote_from_inspiration_image(
            image_input=test_img,
            custom_instruction="giọng sâu sắc",
            config={"gemini_model": "gemini-3.5-flash-lite"},
        )
        assert res["quote"] == mock_quote
        assert res["channel"] == "saigonbac"
        assert res["is_ai_generated"] is True



def test_crop_image_to_tiktok_portrait():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "test_img.jpg"
        # Tạo ảnh ngang 1920x1080
        img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
        img.save(tmp_path)

        # Cắt về dọc 1080x1920
        out = crop_image_to_tiktok_portrait(tmp_path)
        with Image.open(out) as cropped_img:
            assert cropped_img.size == (1080, 1920)


def test_render_saigonbac_18s_smoke():
    with tempfile.TemporaryDirectory() as tmp_dir:
        bg_path = Path(tmp_dir) / "bg.jpg"
        out_vid = Path(tmp_dir) / "test_18s.mp4"

        # Tạo ảnh nền test 1080x1920
        img = Image.new("RGB", (1080, 1920), color=(40, 50, 60))
        img.save(bg_path)

        quote = "Đi qua những ngày mưa bão mới hiểu được, hóa ra bình yên lớn nhất là một buổi sáng ngồi ngắm nắng lên."
        res_vid = render_18s_video(
            image_path=bg_path,
            quote=quote,
            output_path=out_vid,
            duration=2.0,  # Test nhanh 2s để tiết kiệm thời gian test
            signature="saigonbac",
        )

        assert res_vid.exists()
        meta = probe_video_metadata(res_vid)
        assert meta["width"] == 1080
        assert meta["height"] == 1920
        assert meta["has_audio"] is False
