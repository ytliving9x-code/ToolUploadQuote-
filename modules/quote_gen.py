"""
Module sinh nội dung Quote, Caption, Hashtags và Pexels Keywords.
Hỗ trợ cả Google Gemini và OpenAI, bắt buộc trả về JSON hợp lệ,
có cơ chế thử lại (retry) và chống trùng lặp dựa trên lịch sử SQLite.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from modules.history_db import is_quote_duplicate, save_quote

logger = logging.getLogger("tiktok_tool.quote_gen")

# Tải biến môi trường từ .env
load_dotenv()

# ==============================================================================
# HỆ THỐNG 6 DANH MỤC ĐỘC QUYỀN & MICRO-SCENARIO CHO TỪNG KÊNH
# ==============================================================================
CHANNEL_CATEGORIES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "saigonbac": {
        "Bữa cơm & Gia đình": {
            "scenario": "Ngoài xã hội chịu đủ ấm ức, ăn vội bữa cơm lề đường nhưng gọi về cho mẹ vẫn cười bảo con sống rất tốt.",
            "visual_keywords": ["rainy window night", "lonely street food night", "city lights blur"],
        },
        "Đêm muộn Sài Gòn": {
            "scenario": "Tan làm muộn không muốn về căn phòng trọ tối đèn, cứ chạy xe máy lòng vòng ngoài đường ngắm dòng người qua lại.",
            "visual_keywords": ["night traffic street", "neon street night", "motorcycle night city"],
        },
        "Gánh nặng tuổi trưởng thành": {
            "scenario": "Nhìn hóa đơn cuối tháng mà thở dài, sợ tốc độ kiếm tiền của mình không đuổi kịp tốc độ già đi của cha mẹ.",
            "visual_keywords": ["empty room night", "silhouette window dusk", "dark moody coffee"],
        },
        "Vai diễn Người ổn": {
            "scenario": "Ban ngày cười nói hòa đồng với mọi người, đêm về tháo lớp mặt nạ xuống chỉ thấy rã rời mà chẳng biết gọi cho ai.",
            "visual_keywords": ["alone on bench night", "dark bedroom window", "rain on glass"],
        },
        "Nỗ lực trong vô định": {
            "scenario": "Đã cố gắng gấp đôi người khác nhưng mọi thứ vẫn dậm chân tại chỗ, cảm giác chênh vênh giữa thành phố lớn.",
            "visual_keywords": ["foggy street night", "lonely bridge dusk", "train window night"],
        },
        "Khép lòng sau tổn thương": {
            "scenario": "Không còn dám tin vào lời hứa hẹn, thà chọn đi ăn một mình, sống một mình còn hơn đặt cược niềm tin thêm lần nữa.",
            "visual_keywords": ["empty cafe night", "walking alone rain", "shadow street lamp"],
        },
    },
    "kenh_moi": {
        "Mưu lược Tư Mã Ý (Ẩn nhẫn)": {
            "scenario": "Khi chưa có vị thế thì cúi đầu nuốt tự ái, giấu kín tham vọng, mặc kệ kẻ tiểu nhân đắc ý nhất thời để chờ đúng thời cơ.",
            "visual_keywords": ["chess pieces dark", "storm clouds timelapse", "dark ocean waves"],
        },
        "Bản chất của Tiền & Vị thế": {
            "scenario": "Sự thật tàn nhẫn của xã hội: Không có tiền và thực lực thì lời nói không có trọng lượng, mọi sự tử tế đều cần có vị thế bảo vệ.",
            "visual_keywords": ["skyscraper night aerial", "luxury watch dark", "city skyline night"],
        },
        "Thuật nhìn người & Mặt nạ": {
            "scenario": "Nhìn thấu kẻ đang diễn kịch, thảo mai hoặc lợi dụng mình nhưng không vạch trần, chỉ mỉm cười giữ khoảng cách.",
            "visual_keywords": ["man in suit shadow", "lion walking dark", "smoke abstract black"],
        },
        "Kỷ luật trong cô độc": {
            "scenario": "Cắt bỏ những cuộc vui vô bổ và bạn bè xã giao trên bàn tiệc để âm thầm tích lũy tài chính và năng lực.",
            "visual_keywords": ["boxing gym dark", "running night alone", "working late dark office"],
        },
        "Kiểm soát cảm xúc": {
            "scenario": "Không để cơn nóng giận làm hỏng đại cuộc, không than vãn để lộ điểm yếu, dùng sự im lặng làm vũ khí.",
            "visual_keywords": ["calm dark water", "mountain peak fog", "fire flames slow motion"],
        },
        "Luật chơi của Kẻ mạnh": {
            "scenario": "Chấp nhận sự bất công của cuộc đời, ngừng trông chờ sự thương hại và tự biến mình thành người nắm quyền chủ động.",
            "visual_keywords": ["eagle flying slow motion", "highway night drive", "chess king piece"],
        },
    },
}

# Danh mục quote mẫu chất lượng cao dự phòng (đúng độ dài 15-26 từ)
FALLBACK_QUOTES: Dict[str, List[Dict[str, Any]]] = {
    # ☕ Kênh saigonbac
    "Bữa cơm & Gia đình": [
        {
            "quote": "Mình chịu bao nhiêu ấm ức ngoài xã hội cũng được, nhưng chỉ cần nghe giọng mẹ qua điện thoại là khóe mắt lại cay.",
            "pexels_keywords": ["rainy window night", "lonely street food night", "city lights blur"],
            "caption": "Ngoài kia bao la sóng gió, chỉ muốn về ăn bữa cơm nhà. 🌧️",
            "hashtags": ["#saigonbac", "#tamtrang", "#giadinh", "#mẹ", "#doithuc"],
        },
        {
            "quote": "Mình đâu muốn xa nhà. Nhưng không đi bươn chải, lấy gì lo bữa cơm và thuốc thang cho bố mẹ lúc ốm đau.",
            "pexels_keywords": ["rainy window night", "lonely street food night", "city lights blur"],
            "caption": "Nỗi niềm người con xa xứ giữa phố thị hoa lệ. 🥀",
            "hashtags": ["#saigonbac", "#tamtrang", "#doithuc", "#xanha", "#nhatky"],
        },
    ],
    "Đêm muộn Sài Gòn": [
        {
            "quote": "Thích nhất những đêm muộn một mình chạy xe ngoài phố. Gió thốc vào mặt, không cần diễn vai một người lớn thành công.",
            "pexels_keywords": ["night traffic street", "neon street night", "motorcycle night city"],
            "caption": "Đêm muộn Sài Gòn, cởi bỏ lớp mặt nạ người lớn. 🌙",
            "hashtags": ["#saigonbac", "#didaodem", "#tamtrang", "#chill", "#saigon"],
        },
    ],
    "Gánh nặng tuổi trưởng thành": [
        {
            "quote": "Không phải mình yêu tiền đến mức thực dụng, mà là không có tiền thì ngay cả tư cách bảo vệ người thân cũng không có.",
            "pexels_keywords": ["empty room night", "silhouette window dusk", "dark moody coffee"],
            "caption": "Áp lực cơm áo gạo tiền của người trưởng thành. ☕",
            "hashtags": ["#saigonbac", "#truongthanh", "#tamtrang", "#comao"],
        },
    ],
    "Vai diễn Người ổn": [
        {
            "quote": "Có thể ngoài mặt vẫn cười nói bình thường, nhưng chỉ mình mới biết trong lòng đã vụn vỡ từ lâu.",
            "pexels_keywords": ["alone on bench night", "dark bedroom window", "rain on glass"],
            "caption": "Sau nụ cười là những vết thương không tên. 🥀",
            "hashtags": ["#saigonbac", "#giaunoibuon", "#tamtrang", "#nguoion"],
        },
    ],
    "Nỗ lực trong vô định": [
        {
            "quote": "Không phải mình không nỗ lực, mà là có những chuyện dù cố gắng đến kiệt cùng vẫn chẳng thể như ý muốn.",
            "pexels_keywords": ["foggy street night", "lonely bridge dusk", "train window night"],
            "caption": "Cố gắng hết sức rồi, đành buông tay cho nhẹ lòng. 🍃",
            "hashtags": ["#saigonbac", "#cogang", "#tamtrang", "#buongbo"],
        },
    ],
    "Khép lòng sau tổn thương": [
        {
            "quote": "Bị phản bội một lần là đủ để sau này đối diện với bất kỳ ai, mình cũng tự giữ lấy một lối lui.",
            "pexels_keywords": ["empty cafe night", "walking alone rain", "shadow street lamp"],
            "caption": "Khép lòng lại sau những vết thương chưa lành. 🌧️",
            "hashtags": ["#saigonbac", "#tonthuong", "#tamtrang", "#khoctin"],
        },
    ],

    # 🎬 Kênh Mới (Tư Mã Ý, Luật Ngầm & Bản Lĩnh)
    "Mưu lược Tư Mã Ý (Ẩn nhẫn)": [
        {
            "quote": "Đừng vội nổi giận khi bị xem thường. Lúc chưa có gì trong tay, im lặng làm việc vẫn có ích hơn tranh cãi.",
            "pexels_keywords": ["chess pieces dark", "storm clouds timelapse", "dark ocean waves"],
            "caption": "Nhẫn để nhìn thấu, chậm để đi xa. ⛰️",
            "hashtags": ["#nhannhin", "#chothoi", "#trietly", "#tumay", "#banlinh"],
        },
        {
            "quote": "Có những chuyện biết mình đúng cũng không cần nói. Khi chưa đủ vị thế, lời giải thích đôi khi chẳng đáng bằng kết quả.",
            "pexels_keywords": ["chess pieces dark", "storm clouds timelapse", "dark ocean waves"],
            "caption": "Kết quả là câu trả lời đanh thép nhất. ♟️",
            "hashtags": ["#trietly", "#banlinh", "#vithe", "#suyngam"],
        },
    ],
    "Bản chất của Tiền & Vị thế": [
        {
            "quote": "Khi chưa có vốn, hãy lấy kiến thức làm vốn. Khi chưa có quan hệ, hãy lấy uy tín làm nền để đi đường dài.",
            "pexels_keywords": ["skyscraper night aerial", "luxury watch dark", "city skyline night"],
            "caption": "Tích lũy thực lực để tự tạo chỗ đứng. 🏛️",
            "hashtags": ["#tienbac", "#vithe", "#trietly", "#thanhcong"],
        },
    ],
    "Thuật nhìn người & Mặt nạ": [
        {
            "quote": "Đừng chỉ nghe người khác nói. Hãy nhìn cách họ đối xử với bạn khi bạn không còn gì để mang lại cho họ.",
            "pexels_keywords": ["man in suit shadow", "lion walking dark", "smoke abstract black"],
            "caption": "Thời gian và lợi ích sẽ cho thấy bản chất lòng người. 🎭",
            "hashtags": ["#nhinnguoi", "#doithuc", "#trietly", "#suyngam"],
        },
    ],
    "Kỷ luật trong cô độc": [
        {
            "quote": "Bị người khác lấn lướt một lần không đáng sợ. Đáng sợ là vì tự ái mà đưa ra quyết định khiến mình trả giá.",
            "pexels_keywords": ["boxing gym dark", "running night alone", "working late dark office"],
            "caption": "Âm thầm tích lũy, đợi đúng thời cơ. 🐺",
            "hashtags": ["#kyluat", "#giautai", "#trietly", "#dongluc"],
        },
    ],
    "Kiểm soát cảm xúc": [
        {
            "quote": "Khi chưa đủ mạnh, hãy học cách giữ bình tĩnh. Đừng để một người chẳng quan trọng quyết định hướng đi của bạn.",
            "pexels_keywords": ["calm dark water", "mountain peak fog", "fire flames slow motion"],
            "caption": "Tâm bất biến giữa dòng đời vạn biến. 🌊",
            "hashtags": ["#kiemsoatcamxuc", "#tamthe", "#banlinh", "#trietly"],
        },
    ],
    "Luật chơi của Kẻ mạnh": [
        {
            "quote": "Người khác có thể coi thường bạn hôm nay, nhưng đừng vì thế mà quên mất việc mình cần làm ngày mai.",
            "pexels_keywords": ["eagle flying slow motion", "highway night drive", "chess king piece"],
            "caption": "Bản lĩnh của người làm chủ cuộc chơi. 🦅",
            "hashtags": ["#luatke manh", "#banlinh", "#quyenluc", "#thanhcong"],
        },
    ],
}


def clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """
    Làm sạch chuỗi phản hồi từ LLM và parse an toàn.
    Hỗ trợ cả 2 trường hợp:
    1. AI trả về JSON chuẩn: {"quote": "...", ...}
    2. AI chỉ xuất duy nhất 1 câu quote văn bản thuần (plain text) theo yêu cầu prompt khắt khe.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Phản hồi từ LLM trống!")

    text = raw_text.strip()

    # Bỏ markdown code blocks nếu có
    if "```" in text:
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()
        else:
            text = re.sub(r"^```[a-zA-Z]*", "", text)
            text = re.sub(r"```$", "", text).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = text[first_brace : last_brace + 1]
        try:
            data = json.loads(json_candidate)
            if isinstance(data, dict) and "quote" in data:
                # Chuẩn hóa trường pexels_keywords & hashtags
                if isinstance(data.get("pexels_keywords"), str):
                    data["pexels_keywords"] = [k.strip() for k in data["pexels_keywords"].split(",") if k.strip()]
                if not data.get("pexels_keywords"):
                    data["pexels_keywords"] = ["night street rain aesthetic", "dark city lonely"]

                if isinstance(data.get("hashtags"), str):
                    data["hashtags"] = [h.strip() for h in data["hashtags"].split() if h.strip()]
                if not data.get("hashtags"):
                    data["hashtags"] = ["#tamtrang", "#chill", "#phattrienbanthan"]

                if not data.get("caption"):
                    data["caption"] = data["quote"]

                return data
        except Exception:
            pass

    # Nếu không phải JSON, nghĩa là AI đã tuân thủ prompt xuất DUY NHẤT 1 CÂU QUOTE VĂN BẢN
    cleaned_quote = text.strip().strip('"').strip("'").strip("`").strip()
    lines = [line.strip().strip('"').strip("'") for line in cleaned_quote.split("\n") if line.strip()]
    final_quote = " ".join(lines) if lines else cleaned_quote

    return {
        "quote": final_quote,
        "pexels_keywords": ["night street rain aesthetic", "dark city lonely", "rainy car window"],
        "caption": final_quote,
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#truongthanh", "#doithuc"],
    }


def build_system_prompt(
    topic: str = "buồn một chút",
    recent_quotes: Optional[List[str]] = None,
    style: str = "sad_introspective",
    channel: str = "saigonbac",
) -> str:
    """
    Xây dựng prompt chuyên biệt định hình phong cách đối lập 100% DNA:
    - 'saigonbac' (sad_introspective): Trạm Dừng Cảm Xúc (Chữa lành & Đồng cảm).
      Độc thoại nội tâm xưng 'mình' hoặc khuyết chủ ngữ. CẤM dạy đời, cấm dùng 'bạn' để lên lớp.
    - 'kenh_moi' (deep_philosophical): Luật Ngầm & Bản Lĩnh (Tư duy sắc lạnh & Thực tế, hình tượng Tư Mã Ý).
      Ngôi thứ 3 hoặc 'bạn' đanh thép. CẤM than nghèo kể khổ, cấm ủy mị cô đơn.
    """
    # Đồng bộ style và channel nếu có sự sai lệch
    if channel == "kenh_moi" or style == "deep_philosophical":
        channel = "kenh_moi"
        style = "deep_philosophical"
    else:
        channel = "saigonbac"
        style = "sad_introspective"

    recent_quotes_section = ""
    if recent_quotes:
        quotes_list_str = "\n".join(f"  + \"{q}\"" for q in recent_quotes[-15:])
        recent_quotes_section = f"""- TRÁNH LẶP Ý HOẶC CÂU CHỮ VỚI CÁC CÂU GẦN ĐÂY:
{quotes_list_str}"""

    topic_str = topic if topic and topic.strip() else "Bữa cơm & Gia đình"

    # Lấy micro-scenario tương ứng nếu có
    scenario_info = ""
    channel_cats = CHANNEL_CATEGORIES.get(channel, {})
    if topic in channel_cats:
        scenario = channel_cats[topic].get("scenario", "")
        if scenario:
            scenario_info = f"\nTình huống cụ thể (Micro-Scenario): \"{scenario}\""

    if channel == "kenh_moi":
        return f"""Bạn là một người từng trải, điềm tĩnh như Tư Mã Ý, nhìn cuộc đời và các mối quan hệ như một bàn cờ lợi ích.
Bạn viết quote sắc lạnh, bản lĩnh, mưu lược cho video TikTok B-Roll điện ảnh của KÊNH MỚI.

KHÓA RANH GIỚI KÊNH (BẮT BUỘC TUÂN THỦ 100%):
- TUYỆT ĐỐI KHÔNG viết giọng than thân trách phận, không than nghèo kể khổ, không ủy mị, không kể lể nỗi buồn cá nhân hay nhớ mẹ cay mắt.
- Viết như một quy luật sắc lạnh đúc kết từ thực tế thương trường và cuộc sống: Lạnh lùng, thực tế, nhìn thấu quy luật lòng người.

PHONG CÁCH & NGÔI XƯNG:
- Dùng ngôi thứ 3 ("Người khôn ngoan...", "Kẻ có bản lĩnh...", "Người có thực lực...") hoặc xưng "bạn" với giọng đanh thép, dứt khoát. CẤM xưng "mình" kể khổ.
- Mục đích: Để người xem "Tỉnh ngộ và Mạnh mẽ hơn" — như một gáo nước lạnh giúp tỉnh táo trước lòng người và xã hội.
- Mỗi quote 1-2 câu ngắn, TỔNG ĐỘ DÀI TỪ 15 ĐẾN 26 TỪ (tuyệt đối không quá 28 từ).
- Câu từ sắc bén, đắt giá, phù hợp chạy trên nền video B-Roll chuyển động tông tối điện ảnh (Dark luxury / Cinematic).

CHỦ ĐỀ & TÌNH HUỐNG YÊU CẦU:
- Danh mục: "{topic_str}"{scenario_info}

VÍ DỤ VĂN PHONG ĐẠT CHUẨN (THAM KHẢO, KHÔNG CHÉP LẠI):
- "Cạn túi một lần chính là cái giá rẻ nhất để nhìn thấu lòng người. Đừng oán trách kẻ rời đi, vì bản chất của xã giao vốn là trao đổi giá trị." (29 từ -> Rút gọn: "Cạn túi là cách rẻ nhất để nhìn thấu lòng người. Đừng oán trách kẻ rời đi, vì bản chất xã giao vốn là trao đổi giá trị.")
- "Đừng vội nổi giận khi bị xem thường. Lúc chưa có gì trong tay, im lặng làm việc vẫn có ích hơn tranh cãi." (23 từ)
- "Có những chuyện biết mình đúng cũng không cần nói. Khi chưa đủ vị thế, lời giải thích đôi khi chẳng đáng bằng kết quả." (24 từ)
- "Khi chưa có vốn, hãy lấy kiến thức làm vốn. Khi chưa có quan hệ, hãy lấy uy tín làm nền để đi đường dài." (24 từ)

RÀNG BUỘC KỸ THUẬT:
- ĐỘ DÀI BẮT BUỘC: từ 15 đến 26 từ.
- Không hô khẩu hiệu rẻ tiền, không sáo rỗng.
{recent_quotes_section}

ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC):
- Trả về đúng 1 câu quote duy nhất (có thể ngắt 1-2 dòng ngắn).
- KHÔNG dùng dấu ngoặc kép (""), KHÔNG viết lời chào/lời dẫn, KHÔNG giải thích, KHÔNG kèm hashtag."""

    # Mặc định: saigonbac
    return f"""Bạn là một người trẻ bình thường đang chật vật mưu sinh ở Sài Gòn, biết buồn, biết tủi thân, nhớ nhà lúc đêm muộn.
Bạn viết quote tâm sự đêm cho kênh TikTok saigonbac (Trạm Dừng Cảm Xúc).

KHÓA RANH GIỚI KÊNH (BẮT BUỘC TUÂN THỦ 100%):
- TUYỆT ĐỐI KHÔNG viết giọng triết lý dạy đời, không bàn chuyện mưu lược, thắng thua hay đắc nhân tâm.
- CẤM dùng từ "bạn" để lên lớp dạy bảo người khác. Cấm hô khẩu hiệu hay nói đạo lý làm giàu.
- Chỉ viết như lời tự sự thầm kín trong nhật ký, bộc bạch nỗi lòng đời thường lúc 22h đêm - 2h sáng.

PHONG CÁCH & NGÔI XƯNG:
- BẮT BUỘC xưng "mình" (độc thoại nội tâm) hoặc viết câu khuyết chủ ngữ.
- Mục đích: Để người xem thấy "Có người hiểu nỗi lòng của mình" — được phép yếu lòng sau một ngày dài đóng kịch ngoài xã hội.
- Giọng tâm sự, chân thật, buồn nhẹ, trầm lắng, nghẹn ngào, không sến súa.
- Mỗi quote 1-2 câu ngắn, TỔNG ĐỘ DÀI TỪ 15 ĐẾN 26 TỪ (tuyệt đối không quá 28 từ).

CHỦ ĐỀ & TÌNH HUỐNG YÊU CẦU:
- Danh mục: "{topic_str}"{scenario_info}

VÍ DỤ VĂN PHONG ĐẠT CHUẨN (THAM KHẢO, KHÔNG CHÉP LẠI):
- "Lúc túi còn rủng rỉnh thì cuộc vui nào cũng có mặt, đến ngày hỏi vay vài trăm ngàn mới nhận ra danh bạ toàn người dưng." (26 từ)
- "Có thể mình chịu bao nhiêu ấm ức ngoài xã hội cũng được, nhưng chỉ cần nghe giọng mẹ qua điện thoại là khóe mắt lại cay." (26 từ)
- "Thích nhất những đêm muộn một mình chạy xe ngoài phố. Gió thốc vào mặt, không cần diễn vai một người lớn thành công." (23 từ)
- "Không phải mình yêu tiền đến mức thực dụng, mà là không có tiền thì ngay cả tư cách bảo vệ người thân cũng không có." (24 từ)

RÀNG BUỘC KỸ THUẬT:
- Tuyệt đối không nhắc tự tử, tự hại.
- ĐỘ DÀI BẮT BUỘC: từ 15 đến 26 từ.
{recent_quotes_section}

ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC):
- Trả về đúng 1 câu quote duy nhất (có thể ngắt 1-2 dòng ngắn).
- KHÔNG dùng dấu ngoặc kép (""), KHÔNG viết lời chào/lời dẫn, KHÔNG giải thích, KHÔNG kèm hashtag."""




def call_gemini(prompt: str, model_name: str = "gemini-3.8-flash", api_key: Optional[str] = None) -> str:
    """Gọi Google Gemini API sử dụng thư viện google-genai, có cơ chế fallback model tự động."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        try:
            import streamlit as st
            if "GEMINI_API_KEY" in st.secrets:
                key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

    if not key or key == "your_gemini_api_key_here":
        raise ValueError("Chưa cấu hình GEMINI_API_KEY!")

    from google import genai
    client = genai.Client(api_key=key)

    candidate_models = [model_name, "gemini-3.8-flash", "gemini-3.5-flash-lite"]
    # Loại bỏ model trùng lặp nhưng giữ thứ tự ưu tiên
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    from google.genai import types
    config_call = types.GenerateContentConfig(
        temperature=1.0,
    )

    last_error = None
    for m in models_to_try:
        try:
            logger.info(f"Đang gọi Gemini model: {m}...")
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=config_call,
            )
            if response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Lỗi khi gọi model {m}: {e}. Đang thử model tiếp theo...")
            last_error = e

    logger.error(f"Tất cả các model Gemini đều thất bại: {last_error}")
    if last_error is not None:
        raise last_error
    raise RuntimeError("Không có model Gemini nào được gọi thành công.")


def call_openai(prompt: str, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None) -> str:
    """Gọi OpenAI API sử dụng thư viện openai."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or key == "your_openai_api_key_here":
        raise ValueError("Chưa cấu hình OPENAI_API_KEY trong file .env!")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a professional content creator. Always respond strictly in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.75,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI trả về nội dung rỗng!")
        return content
    except Exception as e:
        logger.error(f"Lỗi khi gọi OpenAI API ({model_name}): {e}")
        raise


def generate_quote(
    topic: str = "Bữa cơm & Gia đình",
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    check_duplicate: bool = True,
    custom_db_path: Optional[str | Path] = None,
    style: str = "sad_introspective",
    channel: str = "saigonbac",
) -> Dict[str, Any]:
    """
    Sinh quote hoàn chỉnh theo chủ đề và kênh độc lập, kiểm tra chống trùng lặp và lưu vào database.

    Args:
        topic: Chủ đề (danh mục của kênh).
        config: Cấu hình từ config.json.
        max_retries: Số lần thử lại tối đa nếu JSON lỗi hoặc quote bị trùng lặp.
        check_duplicate: Có kiểm tra trùng lặp trong SQLite hay không.
        custom_db_path: Đường dẫn CSDL tùy chọn (dùng khi chạy test).
        style: Phong cách quote ('sad_introspective' cho saigonbac, 'deep_philosophical' cho kenh_moi).
        channel: Kênh ('saigonbac' hoặc 'kenh_moi').

    Returns:
        Dict chứa 'quote', 'pexels_keywords', 'caption', 'hashtags', 'topic', 'quote_id', 'channel'.
    """
    # Đồng bộ channel và style
    if channel == "kenh_moi" or style == "deep_philosophical":
        channel = "kenh_moi"
        style = "deep_philosophical"
    else:
        channel = "saigonbac"
        style = "sad_introspective"

    # Nạp cấu hình nếu không truyền vào
    if config is None:
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    provider = config.get("llm_provider", "gemini").lower()
    gemini_model = config.get("gemini_model", "gemini-2.5-flash")
    openai_model = config.get("openai_model", "gpt-4o-mini")
    similarity_thresh = config.get("anti_duplicate", {}).get("similarity_threshold", 0.70)

    # Lấy recent_quotes từ lịch sử ĐÚNG KÊNH để AI tránh lặp ý tưởng
    recent_quotes: List[str] = []
    try:
        from modules.history_db import get_history
        history_items = get_history(limit=15, channel=channel, custom_path=custom_db_path)
        recent_quotes = [item["quote"] for item in history_items if item.get("quote")]
    except Exception as e:
        logger.debug(f"Không thể lấy recent_quotes từ CSDL cho kênh {channel}: {e}")

    prompt = build_system_prompt(topic, recent_quotes=recent_quotes, style=style, channel=channel)

    # Lấy visual keywords mặc định cho category nếu có
    cat_info = CHANNEL_CATEGORIES.get(channel, {}).get(topic, {})
    default_keywords = cat_info.get("keywords", ["night street rain aesthetic", "dark city lonely"])

    for attempt in range(1, max_retries + 1):
        logger.info(f"Đang sinh quote cho kênh [{channel}] - chủ đề '{topic}' (Lần {attempt}/{max_retries}, Provider={provider})...")
        try:
            # Gọi LLM tương ứng
            if provider == "openai":
                raw_response = call_openai(prompt, model_name=openai_model)
            else:
                raw_response = call_gemini(prompt, model_name=gemini_model)

            parsed = clean_and_parse_json(raw_response)
            quote_text = parsed["quote"]

            # Bổ sung visual keywords chuẩn từ category nếu LLM trả về rỗng hoặc generic
            if not parsed.get("pexels_keywords") or parsed.get("pexels_keywords") == ["night street rain aesthetic", "dark city lonely"]:
                parsed["pexels_keywords"] = default_keywords

            # Kiểm tra chống trùng lặp theo đúng kênh
            if check_duplicate:
                is_dup, ratio, matched = is_quote_duplicate(
                    quote_text, threshold=similarity_thresh, channel=channel, custom_path=custom_db_path
                )
                if is_dup:
                    logger.warning(
                        f"Quote bị trùng lặp với quote cũ trong kênh [{channel}] (độ tương đồng {ratio:.1%}): '{matched}'. Đang thử lại..."
                    )
                    continue

            # Lưu vào CSDL kèm channel
            quote_id = save_quote(parsed, topic=topic, channel=channel, custom_path=custom_db_path)
            parsed["topic"] = topic
            parsed["quote_id"] = quote_id
            parsed["channel"] = channel
            parsed["is_ai_generated"] = True
            return parsed

        except ValueError as ve:
            # Nếu chưa có API key, hỗ trợ fallback sang bộ dữ liệu mẫu có sẵn để kiểm thử
            err_msg = str(ve)
            if "Chưa cấu hình" in err_msg or "API_KEY" in err_msg:
                logger.warning(f"{err_msg}. Sử dụng quote mẫu dự phòng cho chủ đề '{topic}' kênh [{channel}].")
                return get_fallback_quote(topic, channel=channel, custom_db_path=custom_db_path)
            logger.warning(f"Lỗi parse JSON ở lần {attempt}: {ve}")
        except Exception as e:
            logger.error(f"Lỗi gọi API ở lần {attempt}: {e}")

    # Nếu sau max_retries vẫn lỗi, dùng fallback an toàn
    logger.warning("Đã hết số lần thử sinh quote qua API. Đang sử dụng quote mẫu fallback an toàn.")
    return get_fallback_quote(topic, channel=channel, custom_db_path=custom_db_path)


def get_fallback_quote(topic: str, channel: str = "saigonbac", custom_db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Lấy quote mẫu có sẵn khi chưa có API key hoặc mạng gián đoạn, đúng channel."""
    import random

    topic_key = topic.strip()
    if topic_key not in FALLBACK_QUOTES:
        # Tìm chủ đề mặc định theo channel
        if channel == "kenh_moi":
            fallback_default = FALLBACK_QUOTES.get("Mưu lược Tư Mã Ý (Ẩn nhẫn)")
        else:
            fallback_default = FALLBACK_QUOTES.get("Bữa cơm & Gia đình")
        if not fallback_default:
            fallback_default = next(iter(FALLBACK_QUOTES.values()))
        quote_list = fallback_default
    else:
        quote_list = FALLBACK_QUOTES[topic_key]

    chosen = random.choice(quote_list).copy()

    # Lưu vào CSDL kèm channel
    quote_id = save_quote(chosen, topic=topic, channel=channel, custom_path=custom_db_path)
    chosen["topic"] = topic
    chosen["quote_id"] = quote_id
    chosen["channel"] = channel
    chosen["is_ai_generated"] = False
    return chosen


def review_viral_potential(
    quote: str,
    channel_style: str = "sad_introspective",
    channel: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Thẩm định (AI Review) tiềm năng viral của câu quote trên TikTok:
    - Điểm số: 0 - 100
    - Nhận định: 🌟 Rất tiềm năng viral / 🔥 Khá cuốn, chạm cảm xúc / ⚠️ Cần gọt giũa thêm
    - Phân tích điểm mạnh
    - Gợi ý tối ưu
    - Phiên bản viết lại bén hơn (improved_quote) nếu cần cải thiện
    """
    clean_q = quote.strip().strip('"').strip("'")
    if not clean_q:
        return {
            "score": 0,
            "verdict": "⚠️ Quote trống",
            "word_count": 0,
            "strengths": "Chưa có nội dung câu quote.",
            "suggestions": "Vui lòng nhập câu quote trước khi review.",
            "improved_quote": None,
        }

    words = clean_q.split()
    word_count = len(words)

    if channel:
        if channel == "kenh_moi":
            channel_style = "deep_philosophical"
        else:
            channel_style = "sad_introspective"

    if config is None:
        cfg_p = Path("config.json")
        if cfg_p.exists():
            try:
                with open(cfg_p, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        else:
            config = {}

    provider = config.get("llm_provider", "gemini").lower()
    gemini_model = config.get("gemini_model", "gemini-3.8-flash")
    openai_model = config.get("openai_model", "gpt-4o-mini")

    if channel_style == "deep_philosophical":
        style_desc = (
            "Kênh Mới (Luật Ngầm & Bản Lĩnh): Hình tượng Tư Mã Ý, nhìn đời như bàn cờ lợi ích, tư duy sắc lạnh, "
            "thực tế, đanh thép. Dùng ngôi thứ 3 hoặc 'bạn' đanh thép. CẤM than nghèo kể khổ, cấm ủy mị cô đơn. "
            "Mục đích: Tỉnh ngộ và mạnh mẽ hơn như một gáo nước lạnh."
        )
    else:
        style_desc = (
            "Kênh saigonbac (Trạm Dừng Cảm Xúc): Một người trẻ bình thường chật vật mưu sinh, biết buồn, biết tủi thân lúc đêm muộn. "
            "Xưng 'mình' hoặc khuyết chủ ngữ. CẤM dạy đời, cấm dùng 'bạn' để lên lớp đạo lý hay mưu lược. "
            "Mục đích: Đồng cảm, được phép yếu lòng sau ngày dài đóng kịch."
        )

    prompt = f"""Bạn là chuyên gia phân tích nội dung TikTok (TikTok Content & Viral Strategist hàng đầu).
Nhiệm vụ của bạn là thẩm định và đánh giá (Review) tiềm năng VIRAL của câu quote sau:

CÂU QUOTE CẦN ĐÁNH GIÁ:
"{clean_q}"
(Số lượng từ hiện tại: {word_count} từ)

ĐỊNH VỊ PHONG CÁCH KÊNH ĐỐI LẬP (DNA RIÊNG):
{style_desc}

HÃY ĐÁNH GIÁ DỰA TRÊN 4 TIÊU CHÍ CỐT LÕI CỦA THUẬT TOÁN TIKTOK:
1. Hook & Giữ chân (3s đầu): Có khiến người xem dừng lướt ngay lập tức không?
2. Độ chuẩn DNA kênh: Câu quote có vi phạm điều cấm của kênh không? (saigonbac cấm dạy đời/xưng bạn; Kênh Mới cấm than thở kể khổ).
3. Độ dài & Nhịp điệu: Có nằm trong khung vàng 15 đến 26 từ không?
4. Đề xuất phiên bản tối ưu hơn (improved_quote): Viết lại câu quote này một cách sắc bén hơn, chuẩn phong cách kênh hơn (độ dài 15 - 26 từ).

ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (DUY NHẤT 1 JSON OBJECT HỢP LỆ, KHÔNG KÈM GIẢI THÍCH):
{{
  "score": <số nguyên từ 50 đến 99>,
  "verdict": "<🌟 Rất tiềm năng viral | 🔥 Khá tốt, chạm cảm xúc | ⚠️ Cần gọt giũa thêm>",
  "strengths": "<Điểm mạnh nổi bật nhất của câu quote>",
  "suggestions": "<Nhận xét cụ thể để câu này dễ bùng nổ tương tác hơn>",
  "improved_quote": "<Phiên bản viết lại bén hơn, chuẩn phong cách kênh hơn (15-26 từ)>"
}}
"""

    try:
        if provider == "openai":
            raw_res = call_openai(prompt, model_name=openai_model)
        else:
            raw_res = call_gemini(prompt, model_name=gemini_model)

        parsed = {}
        first_b = raw_res.find("{")
        last_b = raw_res.rfind("}")
        if first_b != -1 and last_b != -1 and last_b > first_b:
            parsed = json.loads(raw_res[first_b : last_b + 1])

        score = int(parsed.get("score", 82))
        verdict = parsed.get("verdict", "🔥 Khá tốt, chạm cảm xúc")
        strengths = parsed.get("strengths", "Câu từ tự nhiên, đúng định vị phong cách.")
        suggestions = parsed.get("suggestions", "Có thể gọt giũa thêm để câu ngắn gọn và đắt giá hơn.")
        improved_quote = parsed.get("improved_quote")

        return {
            "score": max(50, min(100, score)),
            "verdict": verdict,
            "word_count": word_count,
            "strengths": strengths,
            "suggestions": suggestions,
            "improved_quote": improved_quote,
        }

    except Exception as e:
        logger.warning(f"Lỗi khi gọi AI review quote ({e}), sử dụng bộ đánh giá nội bộ fallback.")
        score = 80
        if 15 <= word_count <= 26:
            score += 8
        elif word_count < 10 or word_count > 30:
            score -= 15

        verdict = "🔥 Khá tốt, chạm cảm xúc" if score >= 80 else "⚠️ Cần gọt giũa thêm"
        return {
            "score": score,
            "verdict": verdict,
            "word_count": word_count,
            "strengths": "Câu từ mạch lạc, thể hiện rõ phong cách kênh.",
            "suggestions": "Đảm bảo độ dài trong khoảng 15-26 từ để người xem kịp đọc trọn vẹn trong video ngắn.",
            "improved_quote": None,
        }

