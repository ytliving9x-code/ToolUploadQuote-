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

# Danh mục quote mẫu chất lượng cao dự phòng (phong cách buồn một chút, tâm sự chân thật, 15-35 từ)
FALLBACK_QUOTES: Dict[str, List[Dict[str, Any]]] = {
    "tự mình chịu đựng": [
        {
            "quote": "Không phải mình không muốn chia sẻ, mà là có những nỗi buồn nói ra chỉ khiến người khác thêm bận lòng.",
            "pexels_keywords": ["night street rain aesthetic", "lone wolf dark moody", "calm ocean night moody"],
            "caption": "Tự ôm lấy mình đi qua bão giông. 🌙",
            "hashtags": ["#buonmotchut", "#tamtrang", "#doithuc", "#tuchan", "#suyngam"],
        },
        {
            "quote": "Mình có mạnh mẽ đâu. Nhưng ngoài việc tự lau nước mắt rồi bước tiếp, mình còn biết dựa vào ai...",
            "pexels_keywords": ["dark rainy street aesthetic", "lonely walking night street", "rainy car window"],
            "caption": "Là do cuộc sống này quá khó khăn, hay là do mình chưa đủ may mắn...",
            "hashtags": ["#buonmotchut", "#tamtrang", "#côđơn", "#imlang", "#chill"],
        },
    ],
    "giấu nỗi buồn": [
        {
            "quote": "Có thể ngoài mặt vẫn cười nói bình thường, nhưng chỉ mình mới biết trong lòng đã vụn vỡ từ lâu.",
            "pexels_keywords": ["city lights night blurred", "dark office building night", "rain street reflections"],
            "caption": "Sau nụ cười là những vết thương không tên. 🥀",
            "hashtags": ["#buonmotchut", "#giaunoibuon", "#tamtrang", "#gocnhotamhon"],
        },
        {
            "quote": "Có thể người ta thấy anh luôn ổn và điềm tĩnh, nhưng chỉ mình anh biết đã phải trải qua bao đêm thức trắng để học cách im lặng.",
            "pexels_keywords": ["rainy window coffee", "night city drive lights", "quiet aesthetic corner"],
            "caption": "Trưởng thành là học cách nuốt nước mắt vào trong. ☕",
            "hashtags": ["#buonmotchut", "#imlang", "#tamtrang", "#nhatky"],
        },
    ],
    "cô đơn": [
        {
            "quote": "Mình có thích ở một mình đâu. Nhưng việc phải giải thích nỗi buồn của mình cho người khác còn mệt mỏi hơn gấp vạn lần.",
            "pexels_keywords": ["foggy forest dark moody", "calm ocean night moody", "aesthetic coffee rain"],
            "caption": "Đôi khi cô đơn lại là khoảng lặng bình yên nhất. 🍃",
            "hashtags": ["#buonmotchut", "#codon", "#tamtrang", "#langdong"],
        },
    ],
    "đi dạo một mình buổi tối": [
        {
            "quote": "Mình thích cái cảm giác đi lang thang một mình vào buổi tối. Không ai nhìn rõ mình, còn mình có thể nhìn thấu bản thân.",
            "pexels_keywords": ["night street rain aesthetic", "dark subway quiet", "rainy window coffee"],
            "caption": "Đêm muộn, đối diện với chính tâm can mình. 🌙",
            "hashtags": ["#buonmotchut", "#didaodem", "#tamtrang", "#chill"],
        },
    ],
    "cố gắng nhưng không như ý": [
        {
            "quote": "Không phải mình không nỗ lực, mà là có những chuyện dù cố gắng đến kiệt cùng vẫn chẳng thể như ý muốn.",
            "pexels_keywords": ["dark aesthetic office night", "foggy forest dark moody", "rain street reflections"],
            "caption": "Cố gắng hết sức rồi, đành buông tay cho nhẹ lòng. 🥀",
            "hashtags": ["#buonmotchut", "#cogang", "#tamtrang", "#buongbo"],
        },
    ],
    "chấp nhận buông bỏ": [
        {
            "quote": "Đến một lúc nào đó, im lặng không còn là tức giận nữa, mà là một sự chấp nhận buông bỏ nhẹ nhõm và bình an.",
            "pexels_keywords": ["dark beach waves night", "rain mist forest", "aesthetic night street"],
            "caption": "Buông tay để tìm lại bình yên cho chính mình. 🤍",
            "hashtags": ["#buonmotchut", "#buongbo", "#tamtrang", "#binhyen"],
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
    # Ghép các dòng lại thành câu hoàn chỉnh (nếu có xuống dòng)
    final_quote = " ".join(lines) if lines else cleaned_quote

    return {
        "quote": final_quote,
        "pexels_keywords": ["night street rain aesthetic", "dark city lonely", "rainy car window"],
        "caption": final_quote,
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#truongthanh", "#doithuc"],
    }



def build_system_prompt(topic: str = "buồn một chút", recent_quotes: Optional[List[str]] = None) -> str:
    """
    Xây dựng prompt chuyên biệt định hình:
    Người viết quote 'buồn một chút' cho video TikTok tiếng Việt.
    Giọng tâm sự, chân thật, buồn nhẹ, trầm lắng, không sến, không kêu gào.
    """
    recent_quotes_section = ""
    if recent_quotes:
        quotes_list_str = "\n".join(f"  + \"{q}\"" for q in recent_quotes[-15:])
        recent_quotes_section = f"""- TRÁNH LẶP Ý HOẶC CÂU CHỮ VỚI CÁC CÂU GẦN ĐÂY:
{quotes_list_str}"""

    topic_str = topic if topic and topic.strip() else "tự mình chịu đựng"

    return f"""Bạn là người viết quote "buồn một chút" cho video TikTok tiếng Việt.

PHONG CÁCH:
- Giọng tâm sự, chân thật, buồn nhẹ, trầm lắng, không sến và không kêu gào.
- Xưng "mình" (tự sự) hoặc "bạn" (nói với người xem). Thỉnh thoảng dùng "anh" như một lời tự thú.
- Mỗi quote 1-3 câu, tổng 15-35 từ. Có thể ngắt thành 2 đoạn ngắn (dùng dấu xuống dòng hoặc dấu câu rõ ràng).
- Văn nói đời thường, không dùng từ hoa mỹ hay sáo rỗng.

CHỦ ĐỀ ĐANG YÊU CẦU:
"{topic_str}"
(Các chủ đề xoay vòng thường gặp: giấu nỗi buồn không cho ai thấy, tự mình chịu đựng, cô đơn, áp lực tiền bạc và trưởng thành, cha mẹ và gia đình, bị phản bội rồi khó tin người, cố gắng nhưng không được như ý, chấp nhận buông bỏ, đi dạo một mình buổi tối).

CẤU TRÚC (linh hoạt áp dụng đa dạng một trong các dạng sau):
1. "Không phải X, mà là Y."
2. "Có thể A, nhưng chỉ mình mới biết B."
3. Mở đầu bằng câu phủ định nhẹ rồi nói điều thật lòng ("Mình có hạnh phúc đâu. Nhưng...")
4. Kết bằng câu hỏi tu từ hoặc dấu "..." để lửng.
5. "Sau này... bạn nhớ rằng..."

VÍ DỤ TIÊU BIỂU VỀ VĂN PHONG (THAM KHẢO, KHÔNG ĐƯỢC CHÉP LẠI):
- "Thứ khiến con người ta buồn nhất không phải là mất mát, mà là đã cố gắng rất nhiều nhưng mọi chuyện chẳng như mong muốn."
- "Mình thích cái cảm giác đi lang thang một mình vào buổi tối. Không ai nhìn rõ mình, còn mình có thể nhìn thấu bản thân."
- "Là do cuộc sống này quá khó khăn, hay là do mình chưa được may mắn..."
- "Mình có hạnh phúc đâu. Nhưng mình không muốn để người khác thấy mình khổ."

RÀNG BUỘC AN TOÀN & NỘI DUNG:
- Tuyệt đối không nhắc tự tử, tự hại hay phương pháp làm đau bản thân.
- Buồn nhưng vẫn giữ chút ấm áp hoặc chấp nhận ở cuối.
- Không sến súa, không giật gân, không rao giảng đạo lý.
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
    topic: str = "trưởng thành",
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
    fallback_default = next(iter(FALLBACK_QUOTES.values()))
    quote_list = FALLBACK_QUOTES.get(topic_key, fallback_default)
    chosen = random.choice(quote_list).copy()

    # Lưu vào CSDL
    quote_id = save_quote(chosen, topic=topic, custom_path=custom_db_path)
    chosen["topic"] = topic
    chosen["quote_id"] = quote_id
    chosen["is_ai_generated"] = False
    return chosen
