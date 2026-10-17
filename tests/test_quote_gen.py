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
    assert "#tamtrang" in result["hashtags"]
    assert "#chill" in result["hashtags"]
    assert "#phattrienbanthan" in result["hashtags"]


def test_clean_and_parse_json_missing_field():
    """Kiểm tra báo lỗi khi JSON thiếu trường bắt buộc."""
    raw = json.dumps({
        "quote": "Một câu nói hay.",
        "caption": "Caption ngắn."
        # Thiếu pexels_keywords và hashtags
    })
    with pytest.raises(ValueError, match="Thiếu trường bắt buộc"):
        clean_and_parse_json(raw)


def test_clean_and_parse_json_malformed():
    """Kiểm tra báo lỗi khi văn bản không phải JSON."""
    raw = "Đây chỉ là đoạn văn bản thông thường không có cấu trúc JSON nào cả."
    with pytest.raises(ValueError):
        clean_and_parse_json(raw)


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
    assert "pexels_keywords" in data
    assert len(data["pexels_keywords"]) >= 2
    assert "#tamtrang" in data["hashtags"]
    assert data["quote_id"] > 0
