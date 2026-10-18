"""
Unit tests cho module quote_gen: kiểm tra parse JSON an toàn, làm sạch phản hồi LLM
và thuật toán kiểm tra chống trùng lặp quote.
"""

import json
import pytest
from pathlib import Path

from modules.history_db import calculate_similarity, init_db, is_quote_duplicate, save_quote
from modules.quote_gen import clean_and_parse_json, generate_quote, get_fallback_quote


def test_clean_and_parse_json_valid_clean():
    """Kiểm tra parse JSON thuần hợp lệ."""
    raw = json.dumps({
        "quote": "Bình yên không phải là không có giông bão, mà là tâm tĩnh lặng.",
        "pexels_keywords": ["night street rain", "dark subway"],
        "caption": "Giữ tâm tĩnh giữa bão giông cuộc đời. ✨",
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#diemtinh"]
    })
    result = clean_and_parse_json(raw)
    assert result["quote"] == "Bình yên không phải là không có giông bão, mà là tâm tĩnh lặng."
    assert len(result["pexels_keywords"]) == 2
    assert "#tamtrang" in result["hashtags"]
    assert "#chill" in result["hashtags"]
    assert "#phattrienbanthan" in result["hashtags"]


def test_clean_and_parse_json_markdown_wrapped():
    """Kiểm tra parse phản hồi LLM bị bọc trong khối code markdown ```json ... ```."""
    raw = """
    Dưới đây là nội dung JSON bạn yêu cầu:
    ```json
    {
      "quote": "Nước sâu tĩnh lặng, lúa chín cúi đầu.",
      "pexels_keywords": ["moody rain", "night coffee"],
      "caption": "Sự tĩnh lặng là sức mạnh tối thượng.",
      "hashtags": ["#truongthanh", "#suyngam"]
    }
    ```
    Hy vọng bạn thích nội dung này!
    """
    result = clean_and_parse_json(raw)
    assert result["quote"] == "Nước sâu tĩnh lặng, lúa chín cúi đầu."
    # Tự động bổ sung các hashtag cốt lõi
    assert result["quote"] == "Nước sâu tĩnh lặng, lúa chín cúi đầu."
    assert "#truongthanh" in result["hashtags"]
    assert "#suyngam" in result["hashtags"]


def test_clean_and_parse_json_empty():
    """Kiểm tra báo lỗi khi phản hồi rỗng."""
    with pytest.raises(ValueError, match="Phản hồi từ LLM trống"):
        clean_and_parse_json("")


def test_clean_and_parse_plain_text():
    """Kiểm tra khi LLM trả về văn bản thuần 1 câu quote thay vì JSON."""
    raw = '"Đêm muộn, người lớn chỉ dám thở dài khi xung quanh không còn ai."'
    result = clean_and_parse_json(raw)
    assert result["quote"] == "Đêm muộn, người lớn chỉ dám thở dài khi xung quanh không còn ai."
    assert "hashtags" in result
    assert len(result["hashtags"]) > 0



def test_similarity_calculation():
    """Kiểm tra thuật toán đo độ tương đồng chuỗi."""
    t1 = "Bình yên không phải là không có giông bão"
    t2 = "Bình yên không phải là không có bão giông"
    ratio = calculate_similarity(t1, t2)
    assert ratio > 0.8  # Hai câu rất giống nhau

    t3 = "Tiền bạc không mua được tất cả mọi thứ trên đời"
    ratio2 = calculate_similarity(t1, t3)
    assert ratio2 < 0.4  # Hai câu hoàn toàn khác nhau


def test_is_quote_duplicate(tmp_path: Path):
    """Kiểm tra cơ chế phát hiện quote trùng lặp với SQLite."""
    test_db = tmp_path / "test_history.db"
    init_db(test_db)

    quote_1 = {
        "quote": "Bão giông ngoài kia không làm bạn ngã gục nếu tâm bạn vững vàng.",
        "pexels_keywords": ["night rain"],
        "caption": "Bình yên trong tâm",
        "hashtags": ["#chill"]
    }
    save_quote(quote_1, topic="điềm tĩnh", custom_path=test_db)

    # 1. Quote y hệt -> Báo trùng
    is_dup, ratio, matched = is_quote_duplicate(
        "Bão giông ngoài kia không làm bạn ngã gục nếu tâm bạn vững vàng.",
        threshold=0.70,
        custom_path=test_db
    )
    assert is_dup is True
    assert ratio > 0.95

    # 2. Quote biến thể gần giống -> Báo trùng
    is_dup2, ratio2, _ = is_quote_duplicate(
        "Bão giông ngoài kia không thể làm bạn ngã gục nếu tâm bạn vững vàng.",
        threshold=0.70,
        custom_path=test_db
    )
    assert is_dup2 is True

    # 3. Quote nội dung khác hẳn -> Không trùng
    is_dup3, ratio3, _ = is_quote_duplicate(
        "Mỗi ngày nỗ lực thêm 1% bạn sẽ gặt hái thành quả lớn.",
        threshold=0.70,
        custom_path=test_db
    )
    assert is_dup3 is False


def test_fallback_quote_generation(tmp_path: Path):
    """Kiểm tra sinh quote qua fallback khi không có API key."""
    test_db = tmp_path / "test_history.db"
    data = get_fallback_quote("chữa lành", custom_db_path=test_db)
    assert "quote" in data
    assert len(data["quote"]) > 10
    assert data["quote_id"] > 0


def test_nature_cinematic_keywords_and_suggestions():
    """Kiểm tra từ khóa Cinematic Nature và thuật toán gợi ý theo cảm xúc quote."""
    from modules.pixabay_fetcher import NATURE_PRIORITY_KEYWORDS, NATURE_KEYWORD_CATEGORIES
    from modules.quote_manager import suggest_keywords_from_quote

    # 1. Kiểm tra đủ 12 từ khóa thiên nhiên ưu tiên
    assert len(NATURE_PRIORITY_KEYWORDS) == 12
    assert "misty mountains cinematic" in NATURE_PRIORITY_KEYWORDS
    assert "moody ocean waves" in NATURE_PRIORITY_KEYWORDS
    assert "sunset lake reflection" in NATURE_PRIORITY_KEYWORDS

    # 2. Kiểm tra đủ 6 danh mục thiên nhiên
    assert len(NATURE_KEYWORD_CATEGORIES) == 6

    # 3. Gợi ý quote về trưởng thành & cuộc đời -> Núi phủ sương / mây trôi
    kw_truongthanh = suggest_keywords_from_quote("Trưởng thành là khi ta nhận ra cuộc đời không như ta nghĩ.")
    assert "misty mountains cinematic" in kw_truongthanh or "clouds moving over mountains" in kw_truongthanh

    # 4. Gợi ý quote về tiền bạc & áp lực -> Đường vắng xuyên rừng / biển tối
    kw_tienbac = suggest_keywords_from_quote("Cơm áo gạo tiền đè nặng khiến ta mệt mỏi.")
    assert "empty road through forest" in kw_tienbac or "dark sea cinematic" in kw_tienbac


def test_vietnamese_pixabay_query_translation():
    """Kiểm tra chức năng chuyển đổi tiếng Việt sang từ khóa Pixabay tiếng Anh chuẩn."""
    from modules.pixabay_fetcher import QUICK_THEMES_VI, translate_vietnamese_to_pixabay_query

    # 1. Kiểm tra đủ 6 nút chủ đề tiếng Việt
    assert len(QUICK_THEMES_VI) == 6
    assert "🐺 Con Sói Bản Lĩnh" in QUICK_THEMES_VI
    assert "🌧️ Mưa Phố Đêm" in QUICK_THEMES_VI
    assert "🌲 Rừng Đêm & Sương" in QUICK_THEMES_VI
    assert "☕ Quán Cà Phê Khuya" in QUICK_THEMES_VI
    assert "🌊 Biển Đêm Tĩnh Lặng" in QUICK_THEMES_VI
    assert "🛣️ Con Đường Đơn Độc" in QUICK_THEMES_VI

    # 2. Bấm 1 chạm vào thẻ: Con Sói Bản Lĩnh
    q_soi = translate_vietnamese_to_pixabay_query("🐺 Con Sói Bản Lĩnh")
    assert "lone wolf" in q_soi
    assert "vertical" in q_soi

    # 3. Gõ tiếng Việt tự do: con sói và trời mưa
    q_tu_do = translate_vietnamese_to_pixabay_query("con sói trời mưa")
    assert "wolf" in q_tu_do
    assert "rain" in q_tu_do
    assert "dark" in q_tu_do
    assert "moody" in q_tu_do
    assert "vertical" in q_tu_do

    # 4. Gõ tiếng Việt: cánh đồng, ga tàu
    q_field = translate_vietnamese_to_pixabay_query("cánh đồng đêm khuya")
    assert "field" in q_field or "grass" in q_field
    assert "night" in q_field


