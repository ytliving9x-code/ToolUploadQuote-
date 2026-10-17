"""
Module 2: Quản lý câu trích dẫn (quote_manager.py)
Chứa sẵn danh sách các câu quote tâm sự về cơm áo gạo tiền, thất bại trong im lặng,
sự điềm đạm bắt buộc, hỗ trợ lấy ngẫu nhiên hoặc truy xuất theo danh mục.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tiktok_tool.quote_manager")

QUOTES_FILE = Path("quotes.json")


def load_all_quotes() -> List[Dict[str, Any]]:
    """Đọc toàn bộ danh sách quotes từ file quotes.json."""
    if not QUOTES_FILE.exists():
        logger.warning(f"Không tìm thấy file {QUOTES_FILE}, khởi tạo danh sách mặc định.")
        return [
            {
                "id": 1,
                "category": "cơm áo gạo tiền",
                "quote": "Trưởng thành là khi mở mắt ra chỉ thấy hóa đơn. Muốn buông xuôi, nhưng ví tiền chưa bao giờ cho phép.",
                "keywords": ["night street rain aesthetic", "dark city lonely", "rainy car window"],
            }
        ]

    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = json.load(f)
            return quotes if isinstance(quotes, list) else []
    except Exception as e:
        logger.error(f"Lỗi khi đọc file {QUOTES_FILE}: {e}")
        return []


def get_random_quote(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Lấy ngẫu nhiên 1 câu quote.
    Nếu có truyền category thì lọc theo category đó.
    """
    quotes = load_all_quotes()
    if not quotes:
        return {
            "id": 0,
            "category": "cơm áo gạo tiền",
            "quote": "Trưởng thành là khi mở mắt ra chỉ thấy hóa đơn. Ví tiền chưa bao giờ cho phép buông xuôi.",
            "keywords": ["night street rain aesthetic"],
        }

    if category and category != "Tất cả":
        filtered = [q for q in quotes if q.get("category") == category]
        if filtered:
            return random.choice(filtered)

    return random.choice(quotes)


def get_all_categories() -> List[str]:
    """Lấy danh sách các thể loại quote có sẵn."""
    quotes = load_all_quotes()
    categories = sorted(list(set(q.get("category", "khác") for q in quotes if "category" in q)))
    return ["Tất cả"] + categories


def suggest_keywords_from_quote(quote_text: str) -> List[str]:
    """
    Phân tích nội dung câu quote để gợi ý 3-5 từ khóa tìm ảnh Pixabay phù hợp nhất.
    """
    # 1. Tra cứu xem câu quote có sẵn trong quotes.json không
    quotes = load_all_quotes()
    for q in quotes:
        if q.get("quote", "").strip() == quote_text.strip():
            if q.get("keywords"):
                return q["keywords"]

    # 2. Phân tích ngữ nghĩa dựa trên từ khóa tiếng Việt trong câu
    q_lower = quote_text.lower()
    suggested = []

    if any(k in q_lower for k in ["xe", "tan sở", "đường", "về nhà", "phố"]):
        suggested.extend(["night city drive", "rain on car windshield", "night street lonely"])
    elif any(k in q_lower for k in ["hóa đơn", "tiền", "mưu sinh", "cơm áo", "ví"]):
        suggested.extend(["dark aesthetic office night", "night street rain aesthetic", "city skyscraper night moody"])
    elif any(k in q_lower for k in ["ngã", "vết thương", "đau", "gục ngã", "sụp đổ"]):
        suggested.extend(["dark rainy street aesthetic", "lonely walking night street", "misty street light"])
    elif any(k in q_lower for k in ["im lặng", "bớt nói", "tĩnh", "bình yên", "trà", "cà phê"]):
        suggested.extend(["coffee cup rain window", "quiet coffee shop dark", "dark room lamp quiet"])
    elif any(k in q_lower for k in ["mưa", "giông", "bão"]):
        suggested.extend(["rain window night", "dark rainy car window", "gentle rain ripples dark"])
    else:
        suggested.extend(["night street rain aesthetic", "dark subway lonely", "foggy forest dark"])

    return list(dict.fromkeys(suggested))  # Unique items

