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

# 10 Từ khóa ưu tiên hàng đầu theo phong cách Cinematic, Trầm, Cô độc
TOP_PRIORITY_CINEMATIC_KEYWORDS = [
    "lonely man walking at night",
    "rainy city night cinematic",
    "man sitting alone at night",
    "man looking out window",
    "dark street b roll",
    "man walking alone back view",
    "night city lights cinematic",
    "man drinking coffee alone",
    "cinematic urban solitude",
    "moody city b roll",
]

# Toàn bộ kho từ khóa phân loại theo concept
CINEMATIC_KEYWORD_CATEGORIES = {
    "Đường phố ban đêm — trầm, lạnh": [
        "lonely man walking at night",
        "rainy city night cinematic",
        "dark street b roll",
        "night city lights cinematic",
        "man walking alone rain",
    ],
    "Một mình suy nghĩ — nội tâm": [
        "man sitting alone at night",
        "man looking out window cinematic",
        "lonely man silhouette window",
        "man thinking alone dark room",
        "man sitting in car at night",
    ],
    "Người đàn ông bước đi — trưởng thành": [
        "man walking alone back view",
        "man walking in city cinematic",
        "silhouette man walking sunset",
        "man walking empty road",
        "lonely man urban b roll",
    ],
    "Mưa, cửa kính, ánh đèn — tâm trạng": [
        "rain on window at night",
        "city lights bokeh rain",
        "rainy window cinematic",
        "night traffic rain reflections",
        "moody street lights b roll",
    ],
    "Tiền bạc & Áp lực cuộc sống": [
        "man working late night",
        "man walking alone city",
        "night shift worker cinematic",
        "tired man sitting alone",
        "man in empty room cinematic",
    ],
    "Bình thản & Thường ngày": [
        "man drinking coffee alone",
        "late night office cinematic",
        "man sitting in cafe window",
        "ocean waves cinematic",
        "empty road sunset",
        "mountain mist cinematic",
    ],
}

DEFAULT_DARK_KEYWORDS = TOP_PRIORITY_CINEMATIC_KEYWORDS



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
def get_pixabay_api_key(api_key: Optional[str] = None) -> str:
    """Lấy API Key Pixabay từ tham số, .env, Streamlit secrets hoặc config.json."""
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
    return key or ""


def search_pixabay_images(
    query: str = "",
    api_key: Optional[str] = None,
    colors: Optional[str] = None,
    orientation: str = "vertical",
    per_page: int = 12,
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm danh sách ảnh từ Pixabay để hiển thị lưới gallery cho người dùng chọn.
    Trả về danh sách dict chứa: id, preview_url, large_url, tags.
    """
    key = get_pixabay_api_key(api_key)
    if not key or key == "your_pixabay_api_key_here":
        return []

    clean_query = query.strip() if query else random.choice(DEFAULT_DARK_KEYWORDS)

    params: Dict[str, Any] = {
        "key": key,
        "q": clean_query,
        "image_type": "photo",
        "orientation": orientation or "vertical",
        "safesearch": "true",
        "per_page": min(per_page, 30),
    }
    if colors and colors.lower() not in ["all", "none", ""]:
        params["colors"] = colors.lower()

    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    logger.info(f"Đang tìm gallery ảnh Pixabay với query='{clean_query}', params={params}...")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        hits = data.get("hits", [])
        if not hits:
            # Thử từ khóa mở rộng hơn
            params["q"] = "night street"
            url_fb = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
            req_fb = urllib.request.Request(url_fb, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_fb, timeout=12) as response_fb:
                data_fb = json.loads(response_fb.read().decode("utf-8"))
                hits = data_fb.get("hits", [])

        results = []
        for h in hits:
            results.append({
                "id": h.get("id"),
                "preview_url": h.get("webformatURL") or h.get("previewURL"),
                "large_url": h.get("largeImageURL") or h.get("webformatURL"),
                "tags": h.get("tags", ""),
            })
        return results
    except Exception as e:
        logger.error(f"Lỗi khi tìm gallery Pixabay: {e}")
        return []


def download_and_crop_pixabay_image(image_url: str, output_path: Optional[Path] = None) -> Path:
    """Tải một ảnh cụ thể từ URL và crop chuẩn 1080x1920."""
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    img_req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(img_req, timeout=15) as img_resp:
        with open(out_file, "wb") as f_out:
            f_out.write(img_resp.read())

    return resize_and_crop_to_tiktok(out_file)


def fetch_pixabay_image(
    query: str = "",
    api_key: Optional[str] = None,
    output_path: Optional[Path] = None,
    colors: Optional[str] = None,
    orientation: str = "vertical",
    default_prefix: str = "",
) -> Path:
    """
    Tự động tìm kiếm và tải 1 bức ảnh chất lượng cao khổ dọc từ Pixabay.
    Crop chuẩn 1080x1920 portrait.
    """
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    key = get_pixabay_api_key(api_key)

    user_query = query.strip() if query else ""
    if default_prefix and default_prefix.strip():
        if user_query:
            if default_prefix.lower() in user_query.lower():
                combined_query = user_query
            else:
                combined_query = f"{default_prefix.strip()} {user_query}".strip()
        else:
            combined_query = default_prefix.strip()
    else:
        combined_query = user_query or random.choice(DEFAULT_DARK_KEYWORDS)

    if not key or key == "your_pixabay_api_key_here":
        logger.warning("Chưa cấu hình Pixabay API Key! Dùng ảnh aesthetic fallback.")
        from modules.ai_image_gen import generate_ai_image
        fb_path = generate_ai_image(combined_query)
        with open(fb_path, "rb") as f_src, open(out_file, "wb") as f_dst:
            f_dst.write(f_src.read())
        return resize_and_crop_to_tiktok(out_file)

    # Lấy danh sách ảnh
    hits = search_pixabay_images(
        query=combined_query,
        api_key=key,
        colors=colors,
        orientation=orientation,
        per_page=20,
    )

    if hits:
        chosen = random.choice(hits)
        return download_and_crop_pixabay_image(chosen["large_url"], out_file)

    # Fallback an toàn
    from modules.ai_image_gen import generate_ai_image
    fb_path = generate_ai_image(combined_query)
    with open(fb_path, "rb") as f_src, open(out_file, "wb") as f_dst:
        f_dst.write(f_src.read())
    return resize_and_crop_to_tiktok(out_file)

