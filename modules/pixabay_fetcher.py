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

# 6 Thẻ chủ đề tiếng Việt chọn nhanh phong cách Gam Màu Tối & Đêm Điện Ảnh (1 chạm)
QUICK_THEMES_VI = {
    "🌧️ Mưa Đêm Phố Vắng": "cinematic rainy street night lonely dark",
    "☕ Cà Phê Đêm & Ánh Đèn": "dark night cafe window amber light",
    "🚶 Bước Chân Trong Đêm": "solitary man night walk silhouette street",
    "🚇 Ga Tàu Đêm Cô Độc": "empty subway station night moody dark",
    "🪟 Cửa Sổ Mưa Đêm": "rainy window night city bokeh dark",
    "🌃 Phố Cũ Đèn Vàng": "vintage city street night lights bokeh dark",
}

# Từ điển chuyển đổi tiếng Việt sang từ khóa tìm kiếm Pixabay tiếng Anh
VIETNAMESE_TO_ENGLISH_MAP = {
    "chó sói": "wolf",
    "con sói": "wolf",
    "sói": "wolf",
    "cơn mưa": "rain",
    "trời mưa": "rain",
    "mưa": "rain",
    "cà phê": "coffee cafe",
    "cafe": "coffee cafe",
    "rừng thông": "pine forest",
    "rừng cây": "forest trees",
    "rừng": "forest",
    "ga tàu": "subway station",
    "tàu hỏa": "train",
    "xe lửa": "train",
    "tàu": "train subway",
    "bờ biển": "sea beach",
    "bãi biển": "beach ocean",
    "biển": "sea ocean",
    "sóng biển": "ocean waves",
    "sóng": "waves",
    "đêm khuya": "night",
    "ban đêm": "night",
    "đêm": "night",
    "trời tối": "dark night",
    "tối": "dark night",
    "con đường": "road",
    "đường phố": "street",
    "đường": "road street",
    "thành phố": "city lights",
    "phố xá": "city street",
    "phố": "street",
    "ngọn núi": "mountain",
    "dãy núi": "mountain range",
    "núi": "mountain",
    "mặt hồ": "lake reflection",
    "hồ nước": "lake",
    "hồ": "lake",
    "hàng cây": "trees",
    "cây cối": "trees",
    "cây": "tree",
    "tuyết rơi": "snow falling",
    "bão tuyết": "snow storm",
    "tuyết": "snow winter",
    "đám mây": "clouds",
    "mây trời": "clouds sky",
    "mây": "clouds",
    "sương mù": "fog mist",
    "sương": "fog mist",
    "đàn ông": "man walking alone",
    "người đàn ông": "man",
    "bóng người": "silhouette man",
    "người": "man silhouette",
    "cô đơn": "lonely solitude",
    "một mình": "alone solitary",
    "nỗi buồn": "moody sadness",
    "buồn": "moody",
    "chiếc xe": "car night",
    "ô tô": "car drive",
    "xe hơi": "car",
    "xe": "car drive night",
    "cánh đồng": "field meadow grass",
    "đồng cỏ": "grass field",
    "bông hoa": "flower",
    "hoa": "flower moody",
    "hoàng hôn": "sunset golden hour",
    "bình minh": "sunrise morning",
    "dòng suối": "stream river",
    "suối": "stream",
    "thác nước": "waterfall",
    "thác": "waterfall",
    "cửa kính": "window raindrops",
    "cửa sổ": "window rain",
    "ánh đèn": "city lights bokeh",
    "đèn đường": "street lights",
    "đèn": "lights bokeh",
    "văn phòng": "office late night",
    "công sở": "office building",
    "công việc": "work desk office",
    "tiền bạc": "money skyscraper night",
    "tiền": "skyscraper money",
    "bầu trời": "sky horizon",
    "trời": "sky",
    "cơn gió": "wind blowing",
    "gió": "wind trees",
    "ngôi nhà": "house room window",
    "phòng ngủ": "room dark window",
    "nhà": "house window",
}

# 10 Từ khóa ưu tiên hàng đầu
TOP_PRIORITY_CINEMATIC_KEYWORDS = list(QUICK_THEMES_VI.values())
NATURE_PRIORITY_KEYWORDS = [
    "misty mountains cinematic",
    "foggy forest slow motion",
    "moody ocean waves",
    "waves hitting rocky shore",
    "empty road through forest",
    "forest river cinematic",
    "rain falling on leaves",
    "sunset lake reflection",
    "dark pine forest fog",
    "clouds moving over mountains",
    "waterfall in forest cinematic",
    "wind blowing through grass",
]
NATURE_KEYWORD_CATEGORIES = {
    "Núi rừng phủ sương": ["misty mountains cinematic", "foggy forest sunrise", "mountain clouds slow motion", "clouds moving over mountains"],
    "Biển rộng, sóng vỗ": ["moody ocean waves", "dark sea cinematic", "ocean waves cloudy sky", "waves hitting rocky shore"],
    "Con đường xuyên rừng": ["empty road through forest", "foggy forest road cinematic", "winding road mountain mist"],
    "Mưa rơi trên lá cây": ["rain falling on leaves", "rainy forest cinematic", "forest after rain slow motion"],
    "Hoàng hôn trên hồ": ["sunset lake cinematic", "mountain lake reflection", "golden hour nature landscape", "sunset lake reflection"],
    "Rừng cây và gió": ["forest trees swaying in wind", "dark pine forest fog", "trees in wind cinematic", "waterfall in forest cinematic", "wind blowing through grass"],
}
DEFAULT_DARK_KEYWORDS = list(QUICK_THEMES_VI.values())



def translate_vietnamese_to_pixabay_query(text: str) -> str:
    """
    Dịch cụm từ tiếng Việt tự do sang truy vấn tiếng Anh tối ưu cho Pixabay.
    Luôn tự động bổ sung '+ dark moody vertical' để ảnh có tone tối và chuẩn khổ dọc.
    """
    if not text or not text.strip():
        return "night city rain street dark moody vertical"

    clean_text = text.strip()

    # 1. Nếu là một trong 6 thẻ chủ đề chọn nhanh
    if clean_text in QUICK_THEMES_VI:
        return f"{QUICK_THEMES_VI[clean_text]} vertical"

    # 2. Quét từ điển tiếng Việt -> tiếng Anh
    lower_text = clean_text.lower()
    matched_en_words = []

    # Ưu tiên các cụm từ dài trước (chó sói, cánh đồng, hoàng hôn...)
    sorted_vi_keys = sorted(VIETNAMESE_TO_ENGLISH_MAP.keys(), key=lambda k: len(k), reverse=True)
    for vi_word in sorted_vi_keys:
        if vi_word in lower_text:
            en_val = VIETNAMESE_TO_ENGLISH_MAP[vi_word]
            matched_en_words.append(en_val)
            # Thay thế để tránh khớp trùng lặp từ con
            lower_text = lower_text.replace(vi_word, "")

    if matched_en_words:
        # Gom các từ đã dịch và loại trùng
        en_query = " ".join(dict.fromkeys(matched_en_words))
    else:
        # Nếu người dùng đã gõ tiếng Anh hoặc từ không có trong từ điển
        en_query = clean_text

    # 3. Luôn nối thêm hậu tố '+ dark moody vertical' nếu chưa có
    suffix_terms = []
    for term in ["dark", "moody", "vertical"]:
        if term not in en_query.lower():
            suffix_terms.append(term)

    if suffix_terms:
        final_query = f"{en_query} {' '.join(suffix_terms)}".strip()
    else:
        final_query = en_query.strip()

    return final_query





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
    per_page: int = 4,
    page: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm danh sách ảnh từ Pixabay để hiển thị 4 ảnh xem trước cho người dùng chọn.
    Tự động dịch từ khóa tiếng Việt sang tiếng Anh và thêm 'dark moody vertical'.
    Hỗ trợ tham số page để nhảy sang các trang khác nhau, tránh lặp lại ảnh cũ.
    """
    key = get_pixabay_api_key(api_key)
    if not key or key == "your_pixabay_api_key_here":
        return []

    # Dịch tiếng Việt tự do sang query tiếng Anh chuẩn Pixabay
    clean_query = translate_vietnamese_to_pixabay_query(query)

    target_page = page if (page and page > 0) else 1

    params: Dict[str, Any] = {
        "key": key,
        "q": clean_query,
        "image_type": "photo",          # Cố định ngầm: chỉ lấy ảnh thật
        "orientation": "vertical",       # Cố định ngầm: chỉ lấy ảnh khổ dọc 9:16
        "safesearch": "true",           # Cố định ngầm: lọc nội dung an toàn
        "per_page": min(max(per_page, 4), 20),
        "page": target_page,
    }
    if colors and colors.lower() not in ["all", "none", ""]:
        params["colors"] = colors.lower()

    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    logger.info(f"Đang tìm gallery ảnh Pixabay (Trang {target_page}) với query='{clean_query}'...")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        hits = data.get("hits", [])
        if not hits and target_page > 1:
            # Nếu trang quá xa không có ảnh, quay về trang 1
            params["page"] = 1
            url_p1 = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
            req_p1 = urllib.request.Request(url_p1, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_p1, timeout=12) as resp_p1:
                data_p1 = json.loads(resp_p1.read().decode("utf-8"))
                hits = data_p1.get("hits", [])

        if not hits:
            # Thử từ khóa mở rộng hơn
            params["q"] = "night street dark moody vertical"
            params["page"] = 1
            url_fb = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
            req_fb = urllib.request.Request(url_fb, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_fb, timeout=12) as response_fb:
                data_fb = json.loads(response_fb.read().decode("utf-8"))
                hits = data_fb.get("hits", [])

        results = []
        for h in hits[:4]:  # Giữ tối đa 4 ảnh cho lưới 2x2
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
    Tự động nhảy trang ngẫu nhiên (page=1..8) để ảnh luôn mới toanh, không trùng lặp.
    Crop chuẩn 1080x1920 portrait.
    """
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    key = get_pixabay_api_key(api_key)
    combined_query = translate_vietnamese_to_pixabay_query(query)

    if not key or key == "your_pixabay_api_key_here":
        logger.warning("Chưa cấu hình Pixabay API Key! Dùng ảnh aesthetic fallback.")
        from modules.ai_image_gen import generate_ai_image
        fb_path = generate_ai_image(combined_query)
        with open(fb_path, "rb") as f_src, open(out_file, "wb") as f_dst:
            f_dst.write(f_src.read())
        return resize_and_crop_to_tiktok(out_file)

    # Nhảy trang ngẫu nhiên từ 1 đến 8 để mỗi lần tải là 1 ảnh mới hoàn toàn
    rnd_page = random.randint(1, 8)
    hits = search_pixabay_images(
        query=combined_query,
        api_key=key,
        colors=colors,
        orientation="vertical",
        per_page=12,
        page=rnd_page,
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


def fetch_dark_moody_image_for_quote(
    quote_text: str,
    api_key: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Tự động phân tích câu quote và tải 1 ảnh nền gam màu tối (dark moody / night / rain / cinematic)
    phù hợp với ngữ cảnh câu quote.
    """
    from modules.quote_manager import suggest_keywords_from_quote

    # 1. Lấy danh sách từ khóa gợi ý theo ngữ cảnh quote
    keywords = suggest_keywords_from_quote(quote_text)
    primary_kw = keywords[0] if keywords else "night street rain aesthetic"

    # 2. Bổ sung các chỉ định màu tối, cinematic để bảo đảm gam màu trầm lắng
    dark_mood_modifiers = [
        "dark moody night",
        "rainy night dark cinematic",
        "dark lonely street night",
        "night lights bokeh dark",
        "foggy dark misty night",
    ]
    modifier = random.choice(dark_mood_modifiers)
    query_str = f"{primary_kw} {modifier}".strip()

    logger.info(f"Đang tự động tìm ảnh nền màu tối cho quote: '{query_str}'")
    return fetch_pixabay_image(
        query=query_str,
        api_key=api_key,
        output_path=output_path,
        colors="black,grayscale",  # Ưu tiên tone đen, xám tối
    )




