from __future__ import annotations

"""
Module sinh nội dung Quote, Caption, Hashtags và Pexels Keywords.
Hỗ trợ cả Google Gemini và OpenAI cho Sài Gòn Bạc Studio.
Bao gồm:
1. Sáng tác quote theo prompt người dùng (generate_quote_from_user_prompt).
2. Đọc ảnh tham khảo và copy ý tưởng/biến tấu quote (generate_quote_from_inspiration_image).
3. Sinh quote tự động theo chủ đề cho script/CLI (generate_quote).
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from modules.history_db import is_quote_duplicate, save_quote

logger = logging.getLogger("tiktok_tool.quote_gen")


# Quote mẫu dự phòng an toàn khi mất mạng hoặc chưa nhập API Key
DEFAULT_FALLBACK_QUOTE: Dict[str, Any] = {
    "quote": "Đi qua những ngày mưa bão mới hiểu được, hóa ra bình yên lớn nhất chính là một buổi sáng thảnh thơi ngồi ngắm nắng lên.",
    "pexels_keywords": ["morning coffee", "sunlit window", "cozy room"],
    "caption": "Bình yên là khi tâm hồn không còn nổi sóng gió. ☕🌿",
    "hashtags": ["#saigonbac", "#tinhtai", "#chualanh", "#binhyen"],
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
                    data["hashtags"] = ["#saigonbac", "#tamtrang", "#binhyen"]

                if not data.get("caption"):
                    data["caption"] = data["quote"]

                return data
        except Exception:
            pass

    # Nếu không phải JSON, AI xuất DUY NHẤT 1 CÂU QUOTE VĂN BẢN
    cleaned_quote = text.strip().strip('"').strip("'").strip("`").strip()
    raw_lines = [line.strip().strip('"').strip("'").strip("`").strip() for line in cleaned_quote.split("\n") if line.strip()]

    filtered_lines = []
    for line in raw_lines:
        lower_l = line.lower()
        if any(lower_l.startswith(p) for p in [
            "đây là", "dưới đây là", "câu quote", "quote:", "gợi ý:", "ý tưởng:", "câu mới:", "kết quả:"
        ]) and len(line) < 60:
            continue
        filtered_lines.append(line)

    final_quote = " ".join(filtered_lines) if filtered_lines else cleaned_quote
    final_quote = final_quote.strip('"').strip("'").strip("`").strip()

    return {
        "quote": final_quote,
        "pexels_keywords": ["night street rain aesthetic", "dark city lonely", "rainy car window"],
        "caption": final_quote,
        "hashtags": ["#saigonbac", "#tamtrang", "#binhyen", "#chualanh"],
    }


def call_gemini(prompt: Union[str, List[Any]], model_name: str = "gemini-3.8-flash", api_key: Optional[str] = None) -> str:
    """Gọi Google Gemini API sử dụng thư viện google-genai, có cơ chế fallback model tự động. Hỗ trợ cả text và multimodal."""
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

    candidate_models = [
        model_name,
        "gemini-2.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
        "gemini-2.5-flash-lite",
    ]
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
                {"role": "system", "content": "You are a professional content creator for SaigonBac channel. Always respond strictly in valid JSON."},
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


def get_fallback_quote(
    topic: str = "chữa lành",
    channel: str = "saigonbac",
    custom_db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Lấy quote mẫu có sẵn khi chưa có API key hoặc mạng gián đoạn."""
    chosen = DEFAULT_FALLBACK_QUOTE.copy()
    quote_id = save_quote(chosen, topic=topic, channel=channel, custom_path=custom_db_path)
    chosen["topic"] = topic
    chosen["quote_id"] = quote_id
    chosen["channel"] = channel
    chosen["is_ai_generated"] = False
    return chosen


def generate_quote_from_user_prompt(
    user_prompt: str,
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
    check_duplicate: bool = False,
    custom_db_path: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """
    Gửi trực tiếp Prompt của người dùng tới AI để sinh quote theo đúng ý muốn.
    Người dùng hoàn toàn tự chủ động viết prompt, không dùng prompt mẫu hay khuôn mẫu định sẵn.
    """
    clean_prompt = (user_prompt or "").strip()
    if not clean_prompt:
        raise ValueError("Vui lòng nhập prompt của bạn trước khi yêu cầu AI viết quote!")

    if config is None:
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    provider = config.get("llm_provider", "gemini").lower()
    gemini_model = config.get("gemini_model", "gemini-3.5-flash-lite")
    openai_model = config.get("openai_model", "gpt-4o-mini")

    for attempt in range(1, max_retries + 1):
        logger.info(f"Đang gửi custom prompt của người dùng tới LLM (Lần {attempt}/{max_retries}, Provider={provider})...")
        try:
            if provider == "openai":
                raw_response = call_openai(clean_prompt, model_name=openai_model)
            else:
                raw_response = call_gemini(clean_prompt, model_name=gemini_model)

            parsed = clean_and_parse_json(raw_response)
            quote_id = save_quote(parsed, topic="user_custom_prompt", channel="saigonbac", custom_path=custom_db_path)
            parsed["topic"] = clean_prompt
            parsed["quote_id"] = quote_id
            parsed["channel"] = "saigonbac"
            parsed["is_ai_generated"] = True
            return parsed

        except ValueError as ve:
            err_msg = str(ve)
            if "Chưa cấu hình" in err_msg or "API_KEY" in err_msg:
                raise ve
            logger.warning(f"Lỗi phản hồi ở lần {attempt}: {ve}")
        except Exception as e:
            logger.error(f"Lỗi gọi API ở lần {attempt}: {e}")
            if attempt == max_retries:
                raise e

    raise RuntimeError("Không thể nhận phản hồi từ AI sau các lần thử.")


def generate_quote_from_inspiration_image(
    image_input: Union[Path, str, Any, bytes],
    custom_instruction: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
    custom_db_path: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """
    Nhận diện câu chữ trong ảnh tham khảo (inspiration image) và sáng tác câu quote mới
    có ý tưởng, phong cách và cảm xúc tương tự (copy idea & rewrite).
    """
    from PIL import Image, ImageOps
    import io

    if isinstance(image_input, (str, Path)):
        img = Image.open(str(image_input))
    elif isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
    elif hasattr(image_input, "convert"):
        img = image_input
    else:
        raise ValueError("Định dạng ảnh không hợp lệ!")

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    img = img.convert("RGB")

    # Giảm kích thước nếu ảnh quá lớn để tối ưu hoá bộ nhớ và tốc độ truyền lên Gemini
    if max(img.size) > 2048:
        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

    if config is None:
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    gemini_model = config.get("gemini_model", "gemini-3.5-flash-lite")

    extra_note = f"\nYêu cầu bổ sung từ bạn: {custom_instruction.strip()}" if custom_instruction and custom_instruction.strip() else ""

    vision_prompt = f"""Bạn là một chuyên gia sáng tác quote cho video ngắn TikTok (kênh Sài Gòn Bạc - hoài niệm, sâu sắc, chữa lành, tĩnh tại).
Hãy thực hiện các bước sau dựa trên bức ảnh được đính kèm:
1. Đọc và nhận diện toàn bộ câu chữ / câu quote / thông điệp có trong bức ảnh này (nếu có).
2. Phân tích phong cách, cảm xúc, chủ đề và cấu trúc câu của nội dung đó.
3. Sáng tác 1 câu quote MỚI có phong cách, ý tứ và cảm xúc tương tự (học hỏi ý tưởng, biến tấu tinh tế và sâu sắc, tuyệt đối không sao chép nguyên văn từng chữ để đảm bảo tính độc bản).
   - Nếu trong ảnh có câu chữ: Hãy học hỏi ý tưởng đó và sáng tác 1 câu mới mang phong cách Sài Gòn Bạc tương tự.
   - Nếu ảnh không có chữ hoặc chữ mờ: Hãy cảm nhận tâm trạng/khung cảnh của bức ảnh và sáng tác 1 câu quote hoài niệm, sâu sắc phù hợp.
4. Độ dài chuẩn cho video 18s: từ 15 đến 26 từ (không quá ngắn và không quá 28 từ), câu từ thấm thía, ngắt nhịp tự nhiên.{extra_note}

QUY TẮC ĐẦU RA (BẮT BUỘC):
- Trả về đúng duy nhất 1 câu quote tiếng Việt mới sáng tác.
- Tuyệt đối không dùng dấu ngoặc kép, không viết bất kỳ lời dẫn giải thích nào (như 'Đây là câu quote...', 'Gợi ý:').
- Không kèm hashtag hay icon mở đầu câu."""

    for attempt in range(1, max_retries + 1):
        logger.info(f"Đang phân tích ảnh tham khảo và sáng tác quote tương tự (Lần {attempt}/{max_retries})...")
        try:
            raw_response = call_gemini(
                prompt=[img, vision_prompt],
                model_name=gemini_model,
            )
            parsed = clean_and_parse_json(raw_response)
            quote_id = save_quote(parsed, topic="inspiration_image", channel="saigonbac", custom_path=custom_db_path)
            parsed["topic"] = "Copy ý tưởng từ ảnh tham khảo"
            parsed["quote_id"] = quote_id
            parsed["channel"] = "saigonbac"
            parsed["is_ai_generated"] = True
            return parsed

        except ValueError as ve:
            err_msg = str(ve)
            if "Chưa cấu hình" in err_msg or "API_KEY" in err_msg:
                raise ve
            logger.warning(f"Lỗi phản hồi ở lần {attempt}: {ve}")
        except Exception as e:
            logger.error(f"Lỗi gọi Vision API ở lần {attempt}: {e}")
            if attempt == max_retries:
                raise e

    raise RuntimeError("Không thể nhận diện ảnh và sinh quote sau các lần thử.")


def generate_quote(
    topic: str = "Bình yên",
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
    check_duplicate: bool = True,
    custom_db_path: Optional[Union[str, Path]] = None,
    style: str = "sad_introspective",
    channel: str = "saigonbac",
) -> Dict[str, Any]:
    """
    Sinh quote theo chủ đề cho CLI và automation scripts.
    """
    prompt = (
        f"Hãy sáng tác đúng 1 câu quote tiếng Việt (độ dài 15 đến 26 từ) cho kênh Sài Gòn Bạc "
        f"về chủ đề: '{topic}'. Phong cách hoài niệm, sâu sắc, tĩnh tại, xưng 'mình' hoặc khuyết chủ ngữ. "
        f"Trả về duy nhất 1 câu quote hoàn chỉnh, không có dấu ngoặc kép, không lời dẫn."
    )
    try:
        res = generate_quote_from_user_prompt(
            user_prompt=prompt,
            config=config,
            max_retries=max_retries,
            check_duplicate=check_duplicate,
            custom_db_path=custom_db_path,
        )
        res["topic"] = topic
        return res
    except Exception as e:
        logger.warning(f"Lỗi khi gọi AI sinh quote theo chủ đề ({e}), chuyển sang dùng quote dự phòng.")
        return get_fallback_quote(topic=topic, channel=channel, custom_db_path=custom_db_path)
