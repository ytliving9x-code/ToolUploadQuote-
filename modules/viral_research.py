from __future__ import annotations

"""
Module nghiên cứu nội dung Outlier và Tối ưu Hook Viral cho TikTok (viral_research.py).
Lấy cảm hứng từ ScrapeCreators Social Media Research:
1. Thư viện Outlier Hook Templates phân tích từ các video triệu view trên TikTok.
2. Công cụ AI 'Hook Booster': Đánh giá điểm Retention 3 giây đầu và viết lại câu quote theo cấu trúc giữ chân người xem.
3. Gợi ý Aesthetic Visual Keywords có tỷ lệ giữ chân thị giác (visual retention) cao nhất.
"""

import json
import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("tiktok_tool.viral_research")

# ==============================================================================
# THƯ VIỆN OUTLIER HOOK TEMPLATES (ĐÃ KIỂM CHỨNG TRIỆU VIEW TRÊN TIKTOK)
# ==============================================================================
VIRAL_HOOK_PATTERNS = {
    "saigonbac": {
        "Nghịch Lý Đời Thường": [
            "Người ta cứ bảo thời gian chữa lành mọi thứ, nhưng sự thật là...",
            "Càng tử tế với người khác, càng dễ phải học cách...",
            "Đến một độ tuổi nào đó, bạn sẽ nhận ra một điều kỳ lạ:",
            "Đừng bao giờ tin câu nói 'cứ sống tốt rồi trời xanh tự an bài'...",
            "Im lặng đôi khi không phải là bỏ cuộc, mà là...",
        ],
        "Tâm Sự Đêm Muộn (Chạm Đáy Nỗi Đau)": [
            "Có những ngày mệt mỏi đến mức chỉ muốn tắt điện thoại và...",
            "Nỗi buồn của người trưởng thành lạ lùng lắm:",
            "Đêm nay thành phố đông người quá, nhưng trong lòng lại...",
            "Chúng ta từng hứa sẽ không thay đổi, cho đến khi...",
            "Đoạn đường này từng có hai người, giờ chỉ còn...",
        ],
        "Sự Thật Tuổi 25-35": [
            "Bước qua tuổi 25, điều tàn nhẫn nhất không phải là hết tiền, mà là...",
            "Sau nhiều lần va vấp, mới hiểu vì sao người thông minh thường...",
            "Cách người trưởng thành kết thúc một mối quan hệ không phải là cãi vã, mà là...",
            "Có những bài học phải trả bằng rất nhiều sự tự tôn mới hiểu được:",
            "Học cách chấp nhận rằng có những người chỉ đi cùng mình một đoạn đường ngắn...",
        ],
    },
    "kenh_moi": {
        "Mưu Lược & Ẩn Nhẫn (Tư Mã Ý)": [
            "Kẻ có mưu lược thực sự không bao giờ hơn thua bằng lời nói...",
            "Cúi đầu trước kẻ tiểu nhân không phải hèn, mà là...",
            "Muốn đi xa, trước hết phải học cách nuốt trôi tự ái...",
            "Khi chưa có vị thế, vũ khí sắc bén nhất của bạn chính là...",
            "Đừng để người khác nhìn thấu tham vọng trong mắt bạn...",
        ],
        "Bản Chất Tiền Bạc & Vị Thế": [
            "Có một sự thật rất tàn nhẫn về lòng người và tiền bạc:",
            "Khi bạn không có tiền, mọi sự tử tế của bạn đều bị coi là...",
            "Xã hội này chỉ tôn trọng hai thứ: Năng lực và Kết quả...",
            "Đừng trách người khác thực dụng, hãy tự hỏi vị thế của mình ở đâu...",
            "Người nghèo dạy đạo lý, kẻ mạnh chỉ nhìn vào thực lực...",
        ],
        "Thuật Nhìn Người & Kỷ Luật": [
            "Muốn biết bản chất thật của một người, chỉ cần nhìn 1 điểm duy nhất:",
            "Cắt bỏ 90% các mối quan hệ xã giao là bước đầu tiên để...",
            "Kẻ nguy hiểm nhất không phải kẻ to tiếng, mà là kẻ...",
            "Đừng bao giờ kể bí mật cho người mà bạn chưa từng cùng họ vượt qua...",
            "Kiểm soát được cảm xúc chính là bạn đã làm chủ 80% cuộc chơi...",
        ],
    },
}

# ==============================================================================
# BỘ TỪ KHÓA VISUAL CINEMATIC RETENTION CAO (B-ROLL ĐIỆN ẢNH)
# ==============================================================================
HIGH_RETENTION_VISUALS = {
    "saigonbac": [
        {"theme": "Mưa đêm qua ô kính xe", "keywords": "rainy car window night city blur lights"},
        {"theme": "Góc quán cà phê vắng", "keywords": "dark cozy cafe window rain solitary coffee"},
        {"theme": "Bước chân đơn độc phố đêm", "keywords": "lonely man walking night street lamp puddle"},
        {"theme": "Hoàng hôn buông trên tầng cao", "keywords": "dusk rooftop silhouette city horizon deep blue"},
        {"theme": "Ga tàu & chuyến đi muộn", "keywords": "subway train window reflection night commute"},
    ],
    "kenh_moi": [
        {"theme": "Bàn cờ & bóng tối", "keywords": "chess pieces dramatic lighting dark background"},
        {"theme": "Góc nhìn từ đỉnh cao ốc đêm", "keywords": "skyscraper night skyline aerial luxury dark"},
        {"theme": "Chạy bộ đêm & kỷ luật thép", "keywords": "man running night dark street determination"},
        {"theme": "Sóng biển đêm cuồn cuộn", "keywords": "dark ocean waves crashing storm deep power"},
        {"theme": "Khói mờ & ánh sáng ven", "keywords": "smoke dark silhouette rim light cinematic 4k"},
    ],
}


def get_random_outlier_hooks(channel: str = "saigonbac", limit: int = 5) -> List[Dict[str, str]]:
    """Lấy danh sách các mẫu hook outlier theo kênh."""
    channel_key = "kenh_moi" if channel in ["kenh_moi", "new_channel", "lang"] else "saigonbac"
    cat_dict = VIRAL_HOOK_PATTERNS.get(channel_key, VIRAL_HOOK_PATTERNS["saigonbac"])
    
    results = []
    for cat_name, hooks in cat_dict.items():
        for h in hooks:
            results.append({"category": cat_name, "hook": h})
            
    random.shuffle(results)
    return results[:limit]


def score_hook_strength(quote_or_hook: str) -> Dict[str, Any]:
    """
    Đánh giá độ mạnh của 3 giây đầu tiên (Hook Score) theo quy tắc tâm lý người lướt TikTok:
    - Độ dài: Dưới 10 từ ở phần mở đầu.
    - Từ kích thích thị giác/cảm xúc mạnh (Power words).
    - Có yếu tố tò mò (Open Loop) hoặc đối lập (Contradiction).
    """
    text = quote_or_hook.strip()
    words = text.split()
    total_words = len(words)
    
    # Tách 7 từ đầu tiên làm Hook giả định
    first_chunk = " ".join(words[:min(8, total_words)])
    
    score = 70
    reasons = []
    
    # 1. Kiểm tra từ khóa tò mò / đối lập / thực tế
    power_keywords = [
        "sự thật", "tàn nhẫn", "nhận ra", "càng", "đừng bao giờ", "im lặng",
        "tử tế", "bản chất", "kẻ mạnh", "thời gian", "nỗi buồn", "đến khi",
        "sau nhiều lần", "người thông minh", "mệt mỏi", "buông bỏ", "vị thế",
        "tiền bạc", "tiểu nhân", "cúi đầu", "mưu lược"
    ]
    matched_words = [kw for kw in power_keywords if kw in text.lower()]
    if matched_words:
        score += min(18, len(matched_words) * 6)
        reasons.append(f"Chứa {len(matched_words)} từ khóa kích thích tâm lý: {', '.join(matched_words[:3])}")
    else:
        score -= 8
        reasons.append("Thiếu từ khóa đòn bẩy cảm xúc mạnh trong 3s đầu.")

    # 2. Kiểm tra dấu hiệu ngắt nhịp (dấu phẩy, dấu hai chấm, dấu ba chấm)
    if any(p in first_chunk for p in [":", "...", " - ", ","]):
        score += 6
        reasons.append("Có nhịp ngắt (Pacing) tốt giúp người xem nắm bắt ý nhanh.")
    
    # 3. Độ dài tối ưu tổng thể
    if 15 <= total_words <= 26:
        score += 6
        reasons.append(f"Độ dài lý tưởng ({total_words} từ) cho video 8-15s.")
    elif total_words > 32:
        score -= 10
        reasons.append(f"Hơi dài ({total_words} từ), người xem dễ lướt qua trước khi đọc hết.")

    final_score = max(55, min(98, score))
    
    if final_score >= 88:
        retention_grade = "🔥 Rất Cao (Dễ bùng nổ view & tỷ lệ xem hết > 25%)"
    elif final_score >= 75:
        retention_grade = "✨ Tốt (Tỷ lệ giữ chân 3s trên 60%)"
    else:
        retention_grade = "⚠️ Trung Bình (Cần thêm câu mở đầu giật tò mò)"

    return {
        "score": final_score,
        "grade": retention_grade,
        "word_count": total_words,
        "first_hook_words": first_chunk,
        "reasons": reasons,
    }


def boost_quote_with_ai(
    original_quote: str,
    channel: str = "saigonbac",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Sử dụng AI để tái cấu trúc một câu quote bình thường thành 3 phiên bản Hook Outlier
    có tỷ lệ giữ chân 3 giây đầu cao gấp 3 lần.
    """
    channel_key = "kenh_moi" if channel in ["kenh_moi", "new_channel", "lang"] else "saigonbac"
    
    if channel_key == "kenh_moi":
        channel_name = "Kênh Lặng (Tư duy sắc lạnh, Tư Mã Ý, vị thế, bản lĩnh)"
        forbidden = "CẤM than nghèo kể khổ, cấm ủy mị cô đơn, cấm giọng văn sách vở sáo rỗng."
    else:
        channel_name = "Kênh Sài Gòn Bạc (Tâm sự đêm muộn, hoài niệm, chữa lành, khoảng lặng)"
        forbidden = "CẤM dạy đời, cấm dùng từ 'bạn' để lên lớp đạo lý, cấm hô hào sáo rỗng."

    prompt = f"""Bạn là bậc thầy tối ưu nội dung ngắn TikTok (Short-form Retention & Hook Specialist).
Nhiệm vụ của bạn là lấy cảm hứng từ câu nói gốc sau và viết lại thành 3 PHIÊN BẢN HOOK VIRAL ĐỈNH CAO:

CÂU GỐC:
"{original_quote}"

KÊNH: {channel_name}
NGUYÊN TẮC: {forbidden}

YÊU CẦU ĐẶC BIỆT CỦA THUẬT TOÁN TIKTOK:
1. Dòng đầu tiên (3 giây đầu) phải là 'Hook giật nảy' (Pattern Interrupt): Đảo ngược định kiến, sự thật tàn nhẫn hoặc câu chạm đúng nỗi đau tâm lý.
2. Dòng tiếp theo là 'Payoff / Đúc kết': Sâu sắc, khiến người xem gật gù và bấm 'Lưu video' hoặc 'Chia sẻ'.
3. Độ dài mỗi phiên bản: Đúng 15 đến 24 từ tiếng Việt.

HÃY XUẤT ĐẦU RA DUY NHẤT 1 JSON HỢP LỆ VỚI CẤU TRÚC:
{{
  "hook_contradiction": {{
    "hook_type": "Nghịch lý & Đảo ngược tư duy",
    "quote": "<Phiên bản 1 (15-24 từ, dòng 1 gây sốc hoặc phản trực giác)>",
    "why_it_works": "<Lý do vì sao câu này níu chân người lướt TikTok>"
  }},
  "hook_harsh_truth": {{
    "hook_type": "Sự thật trần trụi tuổi trưởng thành",
    "quote": "<Phiên bản 2 (15-24 từ, đánh thẳng vào lòng người/vị thế/cơm áo)>",
    "why_it_works": "<Lý do vì sao câu này níu chân người lướt TikTok>"
  }},
  "hook_open_loop": {{
    "hook_type": "Mở rộng tò mò (Open Loop) khiến người xem phải đọc hết",
    "quote": "<Phiên bản 3 (15-24 từ, mở đầu bỏ lửng gây tò mò)>",
    "why_it_works": "<Lý do vì sao câu này níu chân người lướt TikTok>"
  }}
}}
"""
    # Gọi AI bằng cách import an toàn hàm call_gemini / call_openai từ quote_gen
    try:
        from modules.quote_gen import call_gemini, call_openai
        if config is None:
            cfg_p = Path("config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

        provider = config.get("llm_provider", "gemini").lower()
        if provider == "openai":
            raw_text = call_openai(prompt, model_name=config.get("openai_model", "gpt-4o-mini"))
        else:
            raw_text = call_gemini(prompt, model_name=config.get("gemini_model", "gemini-3.5-flash-lite"))

        first_b = raw_text.find("{")
        last_b = raw_text.rfind("}")
        if first_b != -1 and last_b != -1 and last_b > first_b:
            result = json.loads(raw_text[first_b : last_b + 1])
            return result
    except Exception as e:
        logger.warning(f"Lỗi khi gọi AI Hook Booster ({e}), dùng fallback.")

    # Fallback chất lượng cao nếu offline/lỗi API
    if channel_key == "kenh_moi":
        return {
            "hook_contradiction": {
                "hook_type": "Nghịch lý & Đảo ngược tư duy",
                "quote": "Kẻ tầm thường mới thích thắng bằng lời nói. Người bản lĩnh chỉ im lặng nâng cao vị thế và năng lực.",
                "why_it_works": "Đối lập trực tiếp giữa kẻ tầm thường và người bản lĩnh.",
            },
            "hook_harsh_truth": {
                "hook_type": "Sự thật trần trụi tuổi trưởng thành",
                "quote": "Khi bạn chưa có tiền, sự tử tế cũng hóa thừa thãi. Xã hội này chỉ tôn trọng kẻ có thực lực.",
                "why_it_works": "Đánh thẳng vào nỗi đau tiền bạc và địa vị của nam giới 25-35.",
            },
            "hook_open_loop": {
                "hook_type": "Mở rộng tò mò khiến người xem phải đọc hết",
                "quote": "Cúi đầu trước kẻ tiểu nhân không phải hèn. Đó là sự ẩn nhẫn chờ đúng thời cơ lật ngược ván cờ.",
                "why_it_works": "Tạo câu hỏi 'vì sao cúi đầu lại là đúng?' giữ chân xem hết video.",
            },
        }
    else:
        return {
            "hook_contradiction": {
                "hook_type": "Nghịch lý & Đảo ngược tư duy",
                "quote": "Người ta cứ nghĩ cô đơn là khi một mình. Nhưng đáng sợ nhất là đứng giữa đám đông mà lòng trống rỗng.",
                "why_it_works": "Định nghĩa lại khái niệm cô đơn, tạo sự đồng cảm sâu sắc.",
            },
            "hook_harsh_truth": {
                "hook_type": "Sự thật trần trụi tuổi trưởng thành",
                "quote": "Bước qua tuổi 25 mới hiểu, điều bình yên nhất không phải tình yêu nồng cháy, mà là một đêm ngon giấc.",
                "why_it_works": "Chạm đúng tâm trạng kiệt sức vì công việc của người đi làm.",
            },
            "hook_open_loop": {
                "hook_type": "Mở rộng tò mò khiến người xem phải đọc hết",
                "quote": "Có những ngày mệt mỏi đến mức, chỉ muốn đứng dưới mưa để chẳng ai thấy mắt mình đang ướt.",
                "why_it_works": "Hình ảnh ẩn dụ giàu cảm xúc, khiến người xem xem lại nhiều lần.",
            },
        }
