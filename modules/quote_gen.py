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

# Danh mục 15+ quote mẫu chất lượng cao dự phòng (phong cách người trưởng thành 27-35 tuổi từng trải, cơm áo gạo tiền)
FALLBACK_QUOTES: Dict[str, List[Dict[str, Any]]] = {
    "điềm tĩnh": [
        {
            "quote": "Trưởng thành là khi mở mắt ra chỉ thấy hóa đơn. Muốn mệt mỏi buông xuôi, nhưng ví tiền không cho phép.",
            "pexels_keywords": ["night street rain aesthetic", "dark subway quiet", "rainy window coffee"],
            "caption": "Mỗi sáng thức dậy là một trận chiến không tiếng súng. Nuốt mệt mỏi vào trong rồi bước tiếp. 🌧️",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#truongthanh", "#comaogaotien"],
        },
        {
            "quote": "Bớt nói lại không phải vì hèn nhát, mà hiểu rằng chẳng ai gánh thay mình gánh nặng cuộc đời.",
            "pexels_keywords": ["dark city lights night blurred", "lonely walking night street", "rainy car window"],
            "caption": "Cười ít đi nhưng lòng bớt xáo động. Bình thản đi qua bão giông. 🌙",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#diemtinh", "#suyngam"],
        },
        {
            "quote": "Đến một độ tuổi, im lặng trở thành câu trả lời duy nhất cho mọi bất công và cay đắng.",
            "pexels_keywords": ["foggy forest dark moody", "calm ocean night moody", "aesthetic coffee rain"],
            "caption": "Không tranh cãi, không giải thích. Người hiểu thì không cần, kẻ không hiểu nói cũng vô ích. ☕",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#imlang", "#chimnghiem"],
        },
        {
            "quote": "Có những ngày kiệt sức, chỉ muốn ngồi im trong xe thêm 10 phút trước khi bước vào nhà.",
            "pexels_keywords": ["night city drive lights", "rain on windshield dark", "dark parking lot moody"],
            "caption": "10 phút ngắn ngủi được làm chính mình, trước khi quay lại vai người lớn gánh vác cả gia đình. 🥀",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#gocnhotamhon", "#apluc"],
        },
    ],
    "nỗ lực": [
        {
            "quote": "Ngã đau mấy cũng không dám kể với ai. Tự lau vết thương rồi ngày mai vẫn phải đi làm đúng giờ.",
            "pexels_keywords": ["late night work desk", "city lights night blurred", "rainy train moody"],
            "caption": "Sau lưng không có ai chống đỡ, lấy tư cách gì để gục ngã? Bước tiếp thôi. 💼",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#noluoc", "#kientri"],
        },
        {
            "quote": "Không có chỗ dựa thì tự làm chỗ dựa. Tiền tự kiếm, cay đắng tự chịu, cuộc đời tự lo.",
            "pexels_keywords": ["walking night street moody", "neon lights dark rain", "dark subway station"],
            "caption": "Độc lập là tự do lớn nhất mà một người trưởng thành có thể tự trao cho mình. 🔥",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tulam", "#bandoi"],
        },
        {
            "quote": "Nỗ lực âm thầm trong bóng tối, không kèn không trống. Kết quả tự nó sẽ lên tiếng.",
            "pexels_keywords": ["aesthetic office night dark", "working late laptop rainy", "misty street light"],
            "caption": "Đừng vội khoe vết thương, hãy khoe sự kiên cường sau khi lành lặn. 🎯",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#amtham", "#chienthang"],
        },
        {
            "quote": "Thất bại lớn nhất không phải là mất trắng, mà là đánh mất lòng tự trọng vì vài đồng bạc lẻ.",
            "pexels_keywords": ["city skyscraper night moody", "dark luxury minimalist", "night road lights"],
            "caption": "Kiếm tiền chân chính tuy chậm và nhọc, nhưng đêm về ngủ được giấc an lành. ✨",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tuduy", "#songdep"],
        },
    ],
    "tiền bạc": [
        {
            "quote": "Tiền không phải vạn năng, nhưng khi người thân cần tiền viện phí, bạn sẽ hiểu tiền là mạng sống.",
            "pexels_keywords": ["dark aesthetic office night", "night city drive lights", "rain street reflections"],
            "caption": "Lý do duy nhất để cày cuốc ngày đêm: bảo vệ những người mình yêu thương khi giông bão tới. 💰",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tienbac", "#trachnhiem"],
        },
        {
            "quote": "Không có tiền thì tự do chỉ là lời nói suông. Làm chủ đồng tiền để không phải cúi đầu trước ai.",
            "pexels_keywords": ["city skyscraper night moody", "dark luxury minimalist", "dark office building"],
            "caption": "Đồng tiền mang lại quyền năng từ chối những thứ mình ghét và những kẻ mình không muốn gặp. 📈",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tudotaichinh", "#sinhhoa"],
        },
        {
            "quote": "Mở mắt ra là tiền thuê nhà, tiền ăn uống, tiền hiếu hỉ. Người lớn không có quyền ốm đau.",
            "pexels_keywords": ["rainy cafe window dark", "soft night lamp aesthetic", "gentle rain leaves moody"],
            "caption": "Khi áp lực sinh tồn đè nặng, cảm xúc chỉ là thứ xa xỉ phải gác lại phía sau. 💳",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#gietgian", "#thucte"],
        },
        {
            "quote": "Kiếm tiền khi còn trẻ không phải vì tham lam, mà để tuổi già không trở thành gánh nặng của con cái.",
            "pexels_keywords": ["dark beach waves night", "rain mist forest", "aesthetic night street"],
            "caption": "Tích lũy hôm nay là tấm khiên vững chãi cho ngày mai. 🛡️",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tichluy", "#loxa"],
        },
    ],
    "chữa lành": [
        {
            "quote": "Sau tất cả va vấp, nhận ra bình yên quý giá hơn đúng sai. Bỏ qua để lòng mình được nhẹ nhõm.",
            "pexels_keywords": ["rainy cafe window dark", "soft night lamp aesthetic", "gentle rain leaves moody"],
            "caption": "Học cách buông tay những gì không thuộc về mình. Trưởng thành là tha thứ cho chính mình. 🍃",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#chualanh", "#buongbo"],
        },
        {
            "quote": "Bữa cơm đạm bạc sau giờ tan sở, ly trà nóng lúc nửa đêm. Bình an đôi khi chỉ đơn giản thế thôi.",
            "pexels_keywords": ["dark room night lamp", "coffee cup rain window", "quiet aesthetic corner"],
            "caption": "Tìm một góc bình yên cho riêng mình sau một ngày lăn lộn mưu sinh ngoài phố xá. 🍵",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#binhyen", "#tinhlang"],
        },
        {
            "quote": "Không ai nợ bạn một cuộc sống dễ dàng. Chấp nhận thực tại là bước đầu tiên để thấy lòng thanh thản.",
            "pexels_keywords": ["dark beach waves night", "rain mist forest", "aesthetic night street"],
            "caption": "Đời không như ý là chuyện bình thường. Dịu dàng với bản thân một chút nhé. 🤍",
            "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#chapnhan", "#yeuthuong"],
        },
    ],
    "văn phòng": [
        {
            "quote": "Đi làm để đổi sức lấy lương, đừng mang cảm xúc đặt lên bàn họp. Hết giờ thì xách cặp về, ai tốt ai xấu kệ họ.",
            "pexels_keywords": ["working late laptop rainy", "aesthetic office night dark", "empty subway station night"],
            "caption": "Chốn công sở, nói ít làm nhiều, bảo vệ nồi cơm của mình trước.",
            "hashtags": ["#congso", "#vanphong", "#doithuc", "#comaogaotien", "#kinhnghiem"],
        },
        {
            "quote": "Đồng nghiệp chỉ là người ngồi chung phòng máy lạnh, không phải tri kỷ. Đừng dại dột đem ruột gan ra kể.",
            "pexels_keywords": ["dark office building night", "rain street reflections", "night city drive lights"],
            "caption": "Giữ khoảng cách an toàn là cách sống khôn ngoan nhất chốn văn phòng.",
            "hashtags": ["#congso", "#vanphong", "#doithuc", "#bandoi", "#kinhnghiemsong"],
        },
        {
            "quote": "Chẳng có công việc nào nhẹ nhàng cả. Nuốt ấm ức vào trong, làm tròn trách nhiệm rồi cuối tháng nhận lương.",
            "pexels_keywords": ["office night work dark", "rain window moody", "city lights night blurred"],
            "caption": "Áp lực nào rồi cũng qua, tài khoản ting ting là mọi mệt mỏi tan biến.",
            "hashtags": ["#congso", "#vanphong", "#lamcong", "#kiemtien", "#truongthanh"],
        },
    ],
}


def clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """
    Làm sạch chuỗi phản hồi từ LLM và parse JSON an toàn.
    Xử lý trường hợp bọc trong ```json ... ``` hoặc có ký tự thừa bên ngoài.
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
        text = text[first_brace : last_brace + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        logger.error(f"Lỗi cú pháp JSON: {err}. Chuỗi cần parse:\n{text}")
        raise ValueError(f"Không thể parse JSON từ phản hồi: {err}") from err

    required_fields = ["quote", "pexels_keywords", "caption", "hashtags"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Thiếu trường bắt buộc '{field}' trong JSON phản hồi!")

    if isinstance(data["pexels_keywords"], str):
        data["pexels_keywords"] = [k.strip() for k in data["pexels_keywords"].split(",") if k.strip()]
    if isinstance(data["hashtags"], str):
        data["hashtags"] = [h.strip() for h in data["hashtags"].split() if h.strip()]

    core_tags = ["#tamtrang", "#chill", "#phattrienbanthan"]
    existing_tags_lower = [t.lower() for t in data["hashtags"]]
    for tag in core_tags:
        if tag.lower() not in existing_tags_lower:
            data["hashtags"].append(tag)

    return data


def build_system_prompt(topic: str, recent_quotes: Optional[List[str]] = None) -> str:
    """
    Xây dựng prompt chuyên biệt định hình nhân vật:
    Người đàn ông bình thường (27 - 35 tuổi), độc thoại nội tâm lúc nửa đêm sau ngày dài mưu sinh.
    Giọng văn thô mộc, trần trụi, gãy gọn, giàu chi tiết đời thực, không văn vẻ bóng bẩy, không sáo rỗng kiểu AI.
    Hỗ trợ chèn danh sách recent_quotes để chống lặp ý tưởng khi gen hàng loạt.
    """
    recent_quotes_section = ""
    if recent_quotes:
        quotes_list_str = "\n".join(f"- \"{q}\"" for q in recent_quotes[-15:])
        recent_quotes_section = f"""
## CÁC CÂU QUOTE ĐÃ TẠO GẦN ĐÂY (BẮT BUỘC TRÁNH LẶP Ý TƯỞNG):
Không được lặp lại ý tưởng, tình huống, hình ảnh hay cấu trúc câu của các câu dưới đây:
{quotes_list_str}
"""

    return f"""Bạn là một người đàn ông bình thường khoảng 27–35 tuổi, đang sống và làm việc giữa thành phố. Bạn đã trải qua đủ chuyện vụn vặt của cuộc sống: tiền nhà, tiền ăn, công việc, đồng nghiệp, những mối quan hệ nhạt dần và những ngày mệt đến mức chẳng muốn nói chuyện với ai.

Đêm nay, bạn ngồi một mình trong phòng trọ hoặc vừa dựng xe trước cửa nhà sau một ngày dài. Bạn không định viết văn, không muốn truyền cảm hứng cho ai, cũng chẳng có ý định tỏ ra mình hiểu đời.

Bạn chỉ đang nghĩ thật lòng về chủ đề: "{topic}".

## NHIỆM VỤ

Viết một câu độc thoại ngắn, nghe như suy nghĩ thật của một người đang sống cuộc đời đó, chứ không phải câu chữ được tạo ra để câu tương tác.

Trước khi viết, hãy tự xác định trong đầu:
- Một tình huống đời thường cụ thể liên quan đến chủ đề.
- Một điều người trong cuộc biết rõ nhưng ít khi nói ra.
- Một cảm xúc thật đang bị giấu phía sau cách nói bình thường.
- Một cách diễn đạt tự nhiên, không giống những câu Quote phổ biến trên mạng.

Không xuất quá trình suy nghĩ. Chỉ xuất kết quả cuối cùng.

## 1. GIỌNG ĐIỆU

- Đời thường, có chút bụi bặm, đôi khi cộc, đôi khi chua chát.
- Giống người thật đang tự nói với mình, không phải người đang đứng trên sân khấu dạy đời.
- Có thể dùng những từ như: "mình", "đời", "tiền", "thôi", "kệ", "chán thật", "ngẫm lại", "cũng đành", "nói vậy thôi".
- Không bắt buộc phải bi quan. Có thể tỉnh táo, mệt mỏi, bất lực, thực tế hoặc hơi buồn cười theo kiểu người lớn.
- Không phải câu nào cũng cần cay đắng, triết lý hoặc kết thúc bằng một cú chốt mạnh.

## 2. QUY TẮC VIẾT QUOTE

- Chỉ viết 1 câu, dài từ 15 đến 26 từ tiếng Việt.
- Mỗi câu phải có một ý chính rõ ràng, không nhồi nhiều triết lý vào cùng một câu.
- Ưu tiên chi tiết đời sống cụ thể: tiền vừa nhận đã phải trả, tin nhắn không muốn trả lời, bữa cơm nguội, chuyến xe về muộn, cuộc gọi từ gia đình, đồng nghiệp chỉ tìm đến khi cần việc.
- Chi tiết chỉ là chất liệu gợi ý. Không được mặc định câu nào cũng phải nhắc đến tiền, phòng trọ, xe cộ hay công việc.
- Có thể viết thẳng, viết cụt, dùng câu ghép tự nhiên hoặc một chút khẩu ngữ. Không cố làm câu văn cân đối hoàn hảo.
- Cảm xúc phải nằm trong tình huống hoặc điều được nói ra, không cần giải thích hộ người đọc.
- Kết thúc bằng một ý thật, một nhận xét bất ngờ nhưng hợp lý hoặc một sự thật khiến người đọc tự liên hệ với mình.
- Không bắt buộc phải có câu kết đắt giá. Không bắt buộc dùng phép đối, câu hỏi tu từ hoặc cấu trúc "không phải... mà là...".
- Tuyệt đối không bịa trải nghiệm cá nhân quá cụ thể như thể đó là câu chuyện có thật của một người xác định.

## 3. BA NGUYÊN TẮC GIÚP QUOTE TỰ NHIÊN HƠN RÕ RỆT

1. Viết như đang nói, không phải đang diễn thuyết:
   - Kém tự nhiên: "Cuộc đời dạy ta phải mạnh mẽ trước những khó khăn."
   - Tự nhiên hơn: "Có hôm chẳng gặp chuyện gì lớn, vậy mà về đến phòng chỉ muốn nằm im, chẳng buồn mở điện thoại."

2. Dùng chi tiết thật thay vì gọi tên cảm xúc:
   - Kém tự nhiên: "Đi làm giữa thành phố khiến con người ta cảm thấy cô đơn."
   - Tự nhiên hơn: "Tan ca, cả danh bạ chẳng biết gọi ai, thôi ghé mua ổ bánh mì rồi về ngủ cho xong ngày."

3. Đừng ép câu nào cũng phải thật sâu sắc:
   - Kém tự nhiên: "Đằng sau nụ cười là những nỗi đau chẳng ai thấu hiểu."
   - Tự nhiên hơn: "Lúc ở công ty còn cười nói bình thường, về tới nhà mới nhớ cả ngày chưa có gì tử tế cho mình."

## 4. NHỮNG LỖI PHẢI TRÁNH

Không sử dụng những cụm từ sáo rỗng, văn vẻ hoặc thường gặp trong nội dung AI như:
- "Bình thản hòa vào dòng xe", "lưng thẳng", "ôm lấy mình", "chữa lành vết thương", "tâm hồn", "bão giông cuộc đời", "tự vỗ về".
- "Trưởng thành là khi...", "Mở mắt ra là...", "Cuộc đời dạy ta...", "Sau tất cả...", "Rồi bạn sẽ nhận ra...", "Không ai biết rằng...", "Đôi khi chúng ta...".
- Những câu mang tính khẩu hiệu như "Cứ cố gắng rồi thành công sẽ đến", "Mạnh mẽ lên vì ngày mai tươi sáng hơn".
- Những cấu trúc sáo mòn như "Người ta chỉ..., còn mình thì...", "Có những thứ..., có những người...", "Đời vốn dĩ...", "Tiền không mua được..., nhưng...".
- Lạm dụng các từ "im lặng", "gồng gánh", "cô đơn", "vết thương", "chấp nhận", "bản lĩnh", "đánh đổi".
- Bất kỳ câu nào chỉ thay vài từ trong những ví dụ có sẵn trên mạng.

Không phải cứ dùng từ thô là chân thật. Không phải cứ buồn là sâu sắc. Không phải cứ cay đắng là đáng nhớ.

## 5. BỘ LỌC CHẤT LƯỢNG

Trước khi trả kết quả, tự kiểm tra:
1. Nếu bỏ chủ đề đi, câu này có thể gắn vào hàng trăm video Quote khác không? Nếu có, viết lại.
2. Câu này có nghe giống một người đang cố tỏ ra từng trải không? Nếu có, viết lại.
3. Câu này có chứa một chi tiết, cách nhìn hoặc sự thật đủ cụ thể để tạo cảm giác đời thực không? Nếu chưa, viết lại.
4. Câu này có đang giải thích quá nhiều hoặc cố kết luận thay người đọc không? Nếu có, cắt bớt.
5. Câu này có giống những ví dụ đã cung cấp hoặc lặp lại cấu trúc của các câu trước không? Nếu có, đổi góc nhìn.
6. Đọc thành tiếng có tự nhiên như lời nói không? Nếu không, viết lại.
{recent_quotes_section}
## 6. CAPTION VÀ TỪ KHÓA HÌNH ẢNH

- Caption: một câu ngắn, gợi đúng cảm giác của Quote, không kể lại nguyên văn, không xin tương tác, không dùng kiểu "Bạn có thấy mình trong đó không?".
- Pexels keywords: 2–3 cụm từ tiếng Anh, mô tả cảnh quay có thể tìm được trên Pexels; ưu tiên hình ảnh có không khí và hành động cụ thể (ví dụ: "late night office", "rainy window", "night street walking", "coffee steam quiet"), tránh chỉ dùng từ cảm xúc chung chung.
- Hashtags: ["#tamtrang", "#congso", "#vanphong", "#doithuc", "#comaogaotien"].

## 7. ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC JSON HỢP LỆ)

Chỉ trả về JSON thuần, không bọc Markdown, không có lời dẫn ngoài JSON:
{{
  "quote": "Một câu độc thoại tiếng Việt từ 15 đến 26 từ.",
  "pexels_keywords": [
    "late night office",
    "rainy window"
  ],
  "caption": "Một câu ngắn gọn, tự nhiên, hợp với nội dung.",
  "hashtags": [
    "#tamtrang",
    "#congso",
    "#vanphong",
    "#doithuc",
    "#comaogaotien"
  ]
}}
"""




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
        response_mime_type="application/json",
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
    topic: str = "điềm tĩnh",
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    check_duplicate: bool = True,
    custom_db_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Sinh quote hoàn chỉnh theo chủ đề, kiểm tra chống trùng lặp và lưu vào database.

    Args:
        topic: Chủ đề (nỗ lực, tiền bạc, điềm tĩnh, chữa lành...).
        config: Cấu hình từ config.json.
        max_retries: Số lần thử lại tối đa nếu JSON lỗi hoặc quote bị trùng lặp.
        check_duplicate: Có kiểm tra trùng lặp trong SQLite hay không.
        custom_db_path: Đường dẫn CSDL tùy chọn (dùng khi chạy test).

    Returns:
        Dict chứa 'quote', 'pexels_keywords', 'caption', 'hashtags', 'topic', 'quote_id'.
    """
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

    # Lấy recent_quotes từ lịch sử để AI tránh lặp ý tưởng / mô thức
    recent_quotes: List[str] = []
    try:
        from modules.history_db import get_history
        history_items = get_history(limit=15, custom_path=custom_db_path)
        recent_quotes = [item["quote"] for item in history_items if item.get("quote")]
    except Exception as e:
        logger.debug(f"Không thể lấy recent_quotes từ CSDL: {e}")

    prompt = build_system_prompt(topic, recent_quotes=recent_quotes)

    for attempt in range(1, max_retries + 1):


        logger.info(f"Đang sinh quote cho chủ đề '{topic}' (Lần thử {attempt}/{max_retries}, Provider={provider})...")
        try:
            # Gọi LLM tương ứng
            if provider == "openai":
                raw_response = call_openai(prompt, model_name=openai_model)
            else:
                raw_response = call_gemini(prompt, model_name=gemini_model)

            parsed = clean_and_parse_json(raw_response)
            quote_text = parsed["quote"]

            # Kiểm tra chống trùng lặp
            if check_duplicate:
                is_dup, ratio, matched = is_quote_duplicate(
                    quote_text, threshold=similarity_thresh, custom_path=custom_db_path
                )
                if is_dup:
                    logger.warning(
                        f"Quote bị trùng lặp với quote cũ (độ tương đồng {ratio:.1%}): '{matched}'. Đang thử lại..."
                    )
                    continue

            # Lưu vào CSDL
            quote_id = save_quote(parsed, topic=topic, custom_path=custom_db_path)
            parsed["topic"] = topic
            parsed["quote_id"] = quote_id
            parsed["is_ai_generated"] = True
            return parsed

        except ValueError as ve:
            # Nếu chưa có API key, hỗ trợ fallback sang bộ dữ liệu mẫu có sẵn để kiểm thử
            err_msg = str(ve)
            if "Chưa cấu hình" in err_msg or "API_KEY" in err_msg:
                logger.warning(f"{err_msg}. Sử dụng quote mẫu dự phòng cho chủ đề '{topic}'.")
                return get_fallback_quote(topic, custom_db_path=custom_db_path)
            logger.warning(f"Lỗi parse JSON ở lần {attempt}: {ve}")
        except Exception as e:
            logger.error(f"Lỗi gọi API ở lần {attempt}: {e}")

    # Nếu sau max_retries vẫn lỗi, dùng fallback an toàn
    logger.warning("Đã hết số lần thử sinh quote qua API. Đang sử dụng quote mẫu fallback an toàn.")
    return get_fallback_quote(topic, custom_db_path=custom_db_path)


def get_fallback_quote(topic: str, custom_db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Lấy quote mẫu có sẵn khi chưa có API key hoặc mạng gián đoạn."""
    import random

    topic_key = topic.lower().strip()
    quote_list = FALLBACK_QUOTES.get(topic_key, FALLBACK_QUOTES["điềm tĩnh"])
    chosen = random.choice(quote_list).copy()

    # Lưu vào CSDL
    quote_id = save_quote(chosen, topic=topic, custom_path=custom_db_path)
    chosen["topic"] = topic
    chosen["quote_id"] = quote_id
    chosen["is_ai_generated"] = False
    return chosen
