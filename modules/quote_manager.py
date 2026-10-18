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

    # Tiền bạc, áp lực -> Kết hợp đô thị & thiên nhiên u ám / đường vắng
    if any(k in q_lower for k in ["tiền", "kiếm sống", "hóa đơn", "cơm áo", "lương", "tài khoản", "ví"]):
        suggested.extend(["man working late night", "empty road through forest", "dark street b roll", "dark sea cinematic"])
    elif any(k in q_lower for k in ["áp lực", "mệt", "kiệt sức", "nặng nề", "đổ sụp"]):
        suggested.extend(["tired man sitting alone", "dark sea cinematic", "empty road through forest", "man in empty room cinematic"])
    
    # Trưởng thành, cuộc đời -> Núi phủ sương, mây trôi, bước đi
    elif any(k in q_lower for k in ["trưởng thành", "thay đổi", "năm tháng", "cuộc đời", "tuổi trẻ", "tiến về"]):
        suggested.extend(["misty mountains cinematic", "clouds moving over mountains", "man walking alone back view", "foggy forest slow motion"])
    
    # Bản lĩnh, im lặng, không khoe khoang -> Rừng thông, cây lay trong gió, bóng người
    elif any(k in q_lower for k in ["im lặng", "không khoe", "bớt nói", "nhịn", "giấu", "bản lĩnh", "vững vàng"]):
        suggested.extend(["dark pine forest fog", "trees in wind cinematic", "forest trees swaying in wind", "lone man shadow"])
    
    # Cô đơn, thất vọng, mất niềm tin -> Biển rộng, sóng vỗ vào đá, mưa đêm
    elif any(k in q_lower for k in ["thất vọng", "mất niềm tin", "ngã", "đau", "phản bội", "cô đơn", "lòng tin"]):
        suggested.extend(["moody ocean waves", "waves hitting rocky shore", "dark rainy street", "man sitting alone at night"])
    
    # Buông bỏ, bình thản -> Hồ tĩnh lặng, hoàng hôn, sóng biển
    elif any(k in q_lower for k in ["bình thản", "buông bỏ", "phẳng lặng", "thôi thì", "kệ", "nhẹ nhõm", "an yên"]):
        suggested.extend(["sunset lake reflection", "mountain lake reflection", "ocean waves cinematic", "mountain mist cinematic"])
    
    # Thời gian, hoài niệm -> Nắng xuyên rừng, hoàng hôn, phim xưa
    elif any(k in q_lower for k in ["hoài niệm", "thời gian", "ngày xưa", "nhớ", "quá khứ"]):
        suggested.extend(["sunset lake cinematic", "golden hour nature landscape", "nostalgic film footage", "clouds moving over mountains"])
    
    # Công sở, thường ngày
    elif any(k in q_lower for k in ["công sở", "văn phòng", "công ty", "đồng nghiệp", "họp"]):
        suggested.extend(["late night office cinematic", "man sitting in cafe window", "city lights night road"])
    
    # Mưa, đêm, tâm trạng
    elif any(k in q_lower for k in ["mưa", "đêm", "cửa kính", "giọt"]):
        suggested.extend(["rain falling on leaves", "rainy city night cinematic", "rain on window at night", "city lights bokeh rain"])
    
    else:
        # Mặc định kết hợp luân phiên đô thị và thiên nhiên cinematic
        suggested.extend(["misty mountains cinematic", "lonely man walking at night", "moody ocean waves", "man sitting alone at night"])

    return list(dict.fromkeys(suggested))  # Unique items



