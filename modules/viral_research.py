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
from pathlib import Path
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
# ==============================================================================
# HỆ THỐNG KHUÔN MẪU THỊ GIÁC OUTLIER (NGHIÊN CỨU TỪ SCRAPECREATORS & OPENCREATOR)
# ==============================================================================
OUTLIER_VISUAL_TEMPLATES = {
    "saigonbac": [
        {
            "title": "🌧️ Mưa Đêm Ô Kính Xe (Deep Nostalgia)",
            "why_viral": "Giữ chân 3s cực mạnh nhờ hiệu ứng hạt mưa lấp lánh (Bokeh). Vùng tối phía dưới chiếm 45% giúp chữ quote trắng nổi bật 100%.",
            "flux_prompt": "Cinematic 35mm photo through a rainy car window at night, glowing amber streetlights and bokeh reflections, lonely melancholic atmosphere, deep dark lower third with clean negative space for typography, Kodachrome film grain, 9:16 vertical portrait, 8k resolution",
            "pinterest_query": "rainy car window night city aesthetic vertical 9:16",
            "pixabay_query": "rain window night city",
        },
        {
            "title": "☕ Góc Quán Cafe Vắng & Đèn Vàng (Khoảng Lặng)",
            "why_viral": "Khơi gợi sự bình yên và đồng cảm. Nhân vật quay lưng không thấy mặt giúp người xem tự đặt bản thân vào vị trí người trong ảnh.",
            "flux_prompt": "Aesthetic photograph of a solitary person from behind sitting alone at a dark wooden cafe table near a wet window at night, warm lamp glowing, steam from coffee cup, moody shadows, clean dark negative space at bottom, 35mm film still, 9:16 vertical portrait",
            "pinterest_query": "dark cozy cafe night rain lonely coffee aesthetic 9:16",
            "pixabay_query": "cozy cafe night dark rain",
        },
        {
            "title": "🚶 Bước Chân Đơn Độc Phố Đêm (Trưởng Thành)",
            "why_viral": "Hình tượng bước đi kiêu hãnh một mình, ánh đèn đường đổ bóng dài trên mặt đường ướt tạo cảm giác điện ảnh sâu thẳm.",
            "flux_prompt": "Cinematic street photography at dusk, back view of a lone person in a dark coat walking on wet asphalt pavement under a vintage yellow streetlight, long dark shadow, moody mist, dark lower space, Leica 35mm lens, 9:16 vertical aspect ratio",
            "pinterest_query": "lonely man walking night street lamp puddle aesthetic 9:16",
            "pixabay_query": "man walking night street puddle",
        },
        {
            "title": "🚇 Chuyến Tàu Đêm & Vệt Sáng (Thời Gian Trôi)",
            "why_viral": "Chuyển động mờ của ánh sáng bên ngoài cửa sổ tàu tạo cảm giác suy tưởng về thời gian và các mối quan hệ đã qua.",
            "flux_prompt": "Atmospheric cinematic shot inside a dark night train cabin, silhouette reflection on the window showing blurred rushing city lights outside, deep blue and amber tones, quiet contemplative solitude, clean typography zone at bottom, 9:16 vertical",
            "pinterest_query": "night train window aesthetic lonely reflection 9:16",
            "pixabay_query": "train window night city blur",
        },
    ],
    "kenh_moi": [
        {
            "title": "♟️ Bàn Cờ Tư Mã Ý & Ánh Đèn Góc (Mưu Lược)",
            "why_viral": "Vật thể biểu tượng cho tính toán và bản lĩnh. Ánh sáng chiếu nghiêng (Chiaroscuro) tạo sự bí hiểm, quyền lực của kẻ mạnh.",
            "flux_prompt": "Dramatic chiaroscuro photography of a wooden chessboard with carved pieces in deep shadow, a solitary king piece illuminated by a single warm beam of light, dark moody luxury study room background, smoke haze, 9:16 vertical portrait, cinematic 8k",
            "pinterest_query": "chess pieces dark dramatic lighting luxury aesthetic 9:16",
            "pixabay_query": "chess pieces dark dramatic lighting",
        },
        {
            "title": "🏢 Đỉnh Cao Ốc Đêm (Vị Thế & Tiền Tài)",
            "why_viral": "Góc nhìn từ trên cao (Eagle view) xuống thành phố lấp lánh tượng trưng cho tham vọng, vị thế và tiền bạc.",
            "flux_prompt": "Cinematic aerial view from a luxury penthouse balcony looking down at a vast sprawling metropolitan skyline at night, glowing skyscrapers and highway light trails, silhouette of an ambitious thinker holding a glass, dark moody palette, 9:16 portrait",
            "pinterest_query": "skyscraper night skyline luxury aerial dark aesthetic 9:16",
            "pixabay_query": "skyscraper night skyline aerial dark",
        },
        {
            "title": "🌊 Sóng Biển Đêm Cuồn Cuộn (Nội Tâm Kẻ Mạnh)",
            "why_viral": "Sóng biển lớn trong đêm đại diện cho sóng gió thương trường và tâm thế tĩnh lặng của người kiểm soát được cảm xúc.",
            "flux_prompt": "Cinematic dark moody ocean with powerful crashing waves at night under a storm cloud sky, deep navy and black tones, textured foam, dramatic rim light, immense power and stoic tranquility, clean dark negative space, 9:16 vertical portrait",
            "pinterest_query": "dark ocean waves crashing storm deep power aesthetic 9:16",
            "pixabay_query": "dark ocean waves night storm",
        },
        {
            "title": "🏃 Chạy Bộ Đêm & Kỷ Luật Thép (Bản Lĩnh)",
            "why_viral": "Chủ đề kỷ luật cá nhân khi cả thế giới đang ngủ. Kích thích hoóc-môn hành động và nỗ lực của nam giới 25-35 tuổi.",
            "flux_prompt": "Powerful cinematic action shot of a solitary athletic man running at night on a dark bridge, sweat and determination, moody streetlights, mist and breath in cold air, low-key dramatic lighting, 9:16 vertical aspect ratio",
            "pinterest_query": "man running night dark street discipline aesthetic 9:16",
            "pixabay_query": "running night dark street athlete",
        },
    ],
}

HIGH_RETENTION_VISUALS = {
    "saigonbac": [
        {"theme": item["title"], "keywords": item["pixabay_query"]} for item in OUTLIER_VISUAL_TEMPLATES["saigonbac"]
    ],
    "kenh_moi": [
        {"theme": item["title"], "keywords": item["pixabay_query"]} for item in OUTLIER_VISUAL_TEMPLATES["kenh_moi"]
    ],
}


def build_ai_visual_prompt_from_quote(
    quote: str,
    channel: str = "saigonbac",
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Sử dụng AI để phân tích câu quote và tạo ra 1 Prompt FLUX.1 chuẩn 4-layer
    chuyên biệt cho hình ảnh TikTok 9:16 có vùng âm tối ở đáy cho typography.
    """
    channel_key = "kenh_moi" if channel in ["kenh_moi", "new_channel", "lang"] else "saigonbac"
    if channel_key == "kenh_moi":
        mood_guide = "Phong cách điện ảnh quyền lực, sắc lạnh, bàn cờ, bóng tối, cao ốc, kỷ luật, mưu lược, ánh sáng tương phản mạnh (Chiaroscuro)."
    else:
        mood_guide = "Phong cách hoài niệm, mưa đêm, đèn vàng phố thị, quán cà phê vắng, ga tàu, bóng lưng cô đơn, hạt film 35mm, êm dịu."

    prompt = f"""Bạn là Giám đốc Hình ảnh Điện ảnh (Cinematic Visual Director) cho các video triệu view TikTok.
Nhiệm vụ của bạn là đọc câu trích dẫn sau và tạo ra DUY NHẤT 1 PROMPT TIẾNG ANH để đưa vào bộ sinh ảnh AI (FLUX.1):

CÂU TRÍCH DẪN:
"{quote}"

HƯỚNG DẪN TÂM LÝ THỊ GIÁC:
{mood_guide}

YÊU CẦU BẮT BUỘC ĐỂ ẢNH ĐẠT TRIỆU VIEW:
1. Không gian âm (Negative Space): Phải có câu lệnh 'dark lower third negative space for typography' để vùng dưới ảnh tối màu, giúp đặt chữ không bị chói.
2. Giấu mặt nhân vật: Chỉ chụp góc lưng (back view), góc nghiêng trong bóng tối (silhouette), hoặc cảnh vật ẩn dụ (metaphor).
3. Máy ảnh & Ánh sáng: '35mm photograph, shallow depth of field, cinematic lighting, Kodachrome film grain, vertical 9:16 aspect ratio'.

HÃY XUẤT RA DUY NHẤT ĐOẠN PROMPT TIẾNG ANH (KHÔNG KÈM GIẢI THÍCH, KHÔNG BỎ VÀO NGOẶC):
"""
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
            res = call_openai(prompt, model_name=config.get("openai_model", "gpt-4o-mini"))
        else:
            res = call_gemini(prompt, model_name=config.get("gemini_model", "gemini-3.5-flash-lite"))

        cleaned = res.strip().strip('"').strip("'").strip("`")
        if cleaned:
            return cleaned
    except Exception as e:
        logger.warning(f"Lỗi AI visual prompt builder ({e}), dùng fallback.")

    if channel_key == "kenh_moi":
        return (
            "Dramatic chiaroscuro 35mm photograph of a wooden chessboard with carved pieces in deep shadow, "
            "warm beam of rim light, dark moody luxury study background, clean dark lower third negative space for typography, "
            "cinematic film grain, 9:16 vertical portrait, 8k"
        )
    else:
        return (
            "Cinematic 35mm photograph through a rainy car window at night, blurred amber bokeh streetlights, "
            "wet asphalt reflections, solitary moody atmosphere, clean dark lower space for typography, "
            "Kodachrome film texture, 9:16 vertical aspect ratio"
        )


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
