"""
Module 1: Tải Ảnh Nền Từ Pixabay (pixabay_fetcher.py)
- Sử dụng Pixabay Image Search API (endpoint: https://pixabay.com/api/)
- Tham số tìm kiếm cố định:
  + q: Từ khóa tìm kiếm tự động (vd: "night cafe", "subway dark", "rain window", "dark street lonely")
  + image_type: "photo"
  + orientation: "vertical" (chỉ lấy ảnh khổ dọc 9:16)
- Tự động tải 1 bức ảnh chất lượng cao (URL từ largeImageURL) về thư mục temp/background.jpg
- Tự động resize/crop ảnh về chuẩn kích thước 1080x1920 bằng Pillow.
"""

import json
import logging
import os
import random
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

logger = logging.getLogger("tiktok_tool.pixabay_fetcher")

DEFAULT_DARK_KEYWORDS = [
    "night street rain",
    "subway dark lonely",
    "rain window night",
    "dark coffee shop",
    "dark street moody",
    "foggy forest dark",
    "city lights night road",
    "night drive rain car",
    "dark room lamp quiet",
]


def resize_and_crop_to_tiktok(image_path: Path, target_size=(1080, 1920)) -> Path:
    """
    Cắt và căn giữa (Center-Crop) ảnh chính xác về khổ 1080x1920 portrait.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        target_w, target_h = target_size
        img_w, img_h = img.size

        target_ratio = target_w / target_h
        current_ratio = img_w / img_h

        if current_ratio > target_ratio:
            # Ảnh rộng hơn tỷ lệ chuẩn -> cắt 2 bên lề
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            top = 0
            img = img.crop((left, top, left + new_w, img_h))
        else:
            # Ảnh hẹp hơn tỷ lệ chuẩn -> cắt phần trên dưới
            new_h = int(img_w / target_ratio)
            left = 0
            top = (img_h - new_h) // 2
            img = img.crop((left, top, img_w, top + new_h))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.save(image_path, format="JPEG", quality=95)

    return image_path


def fetch_pixabay_image(
    query: str,
    api_key: Optional[str] = None,
    output_path: Path | str = Path("temp/background.jpg"),
) -> Path:
    """
    Tìm kiếm và tải 1 ảnh tĩnh dọc từ Pixabay API.
    
    Args:
        query: Từ khóa tìm kiếm hình ảnh (vd: "night cafe", "dark street").
        api_key: Pixabay API key (nếu None sẽ lấy từ .env hoặc config.json).
        output_path: Nơi lưu file ảnh tải về (mặc định temp/background.jpg).
    
    Returns:
        Path dẫn tới file ảnh đã được crop chuẩn 1080x1920.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Lấy API Key (hỗ trợ .env, config.json và Streamlit Cloud Secrets)
    key = api_key or os.getenv("PIXABAY_API_KEY")
    if not key:
        try:
            import streamlit as st
            if "PIXABAY_API_KEY" in st.secrets:
                key = st.secrets["PIXABAY_API_KEY"]
        except Exception:
            pass

    if not key:
        cfg_file = Path("config.json")
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    key = cfg.get("pixabay_api_key")
            except Exception:
                pass

    if not key or key == "your_pixabay_api_key_here":
        # Fallback ảnh chất lượng cao nếu chưa có API key để đảm bảo người dùng vẫn trải nghiệm được mượt mà
        logger.warning("Chưa cấu hình Pixabay API Key! Dùng ảnh aesthetic fallback chất lượng cao.")
        from modules.ai_image_gen import generate_ai_image
        fb_path = generate_ai_image(query)
        with open(fb_path, "rb") as f_src, open(out_file, "wb") as f_dst:
            f_dst.write(f_src.read())
        return resize_and_crop_to_tiktok(out_file)

    clean_query = query.strip() if query else random.choice(DEFAULT_DARK_KEYWORDS)

    # Xây dựng URL request Pixabay
    params = {
        "key": key,
        "q": clean_query,
        "image_type": "photo",
        "orientation": "vertical",
        "safesearch": "true",
        "per_page": 20,
    }

    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    logger.info(f"Đang tìm ảnh Pixabay với từ khóa: '{clean_query}'...")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        hits = data.get("hits", [])
        if not hits:
            logger.warning(f"Pixabay không có kết quả cho '{clean_query}'. Đang thử từ khóa chung...")
            # Thử từ khóa chung
            params["q"] = "night street"
            url_fallback = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
            req_fb = urllib.request.Request(url_fallback, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_fb, timeout=12) as response_fb:
                data_fb = json.loads(response_fb.read().decode("utf-8"))
                hits = data_fb.get("hits", [])

        if hits:
            selected_hit = random.choice(hits)
            img_url = selected_hit.get("largeImageURL") or selected_hit.get("webformatURL")
            logger.info(f"Đang tải ảnh từ: {img_url}...")

            img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                with open(out_file, "wb") as f_out:
                    f_out.write(img_resp.read())

            return resize_and_crop_to_tiktok(out_file)

        raise ValueError(f"Không tìm thấy ảnh phù hợp trên Pixabay.")

    except Exception as e:
        logger.error(f"Lỗi khi gọi Pixabay API: {e}. Đang dùng ảnh aesthetic thay thế...")
        from modules.ai_image_gen import generate_ai_image
        fb_path = generate_ai_image(clean_query)
        with open(fb_path, "rb") as f_src, open(out_file, "wb") as f_dst:
            f_dst.write(f_src.read())
        return resize_and_crop_to_tiktok(out_file)
