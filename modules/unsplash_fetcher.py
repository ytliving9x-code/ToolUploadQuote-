import urllib.request
import urllib.parse
import re
import random
import logging
from pathlib import Path
from typing import Optional, Tuple
from modules.pixabay_fetcher import resize_and_crop_to_tiktok, fetch_pixabay_image

logger = logging.getLogger("tiktok_tool.unsplash_fetcher")

UNSPLASH_SEARCH_URL = "https://unsplash.com/s/photos/"


def fetch_unsplash_photo(
    query: str,
    access_key: Optional[str] = None,
    output_path: Optional[Path] = None,
    target_size: Tuple[int, int] = (1080, 1920),
) -> Path:
    """
    Tìm kiếm và tải ảnh chất lượng cao khổ dọc (portrait) từ Unsplash.
    - Nếu có access_key: gọi qua Unsplash Official API.
    - Nếu chưa có access_key: tự động tìm ảnh portrait trực tiếp từ kho Unsplash không cần đăng ký tài khoản.
    - Tự động crop chuẩn tỷ lệ 1080x1920 cho TikTok.
    - Nếu có sự cố, tự động fallback an toàn sang Pixabay.
    """
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    clean_query = query.strip() if query else "dark moody night"

    # Kiểm tra key nếu có trong biến môi trường hoặc Streamlit secrets
    import os
    key = access_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not key:
        try:
            import streamlit as st
            if "UNSPLASH_ACCESS_KEY" in st.secrets:
                key = st.secrets["UNSPLASH_ACCESS_KEY"]
        except Exception:
            pass

    # Cách 1: Dùng Official API nếu người dùng có key
    if key:
        try:
            import requests
            api_url = "https://api.unsplash.com/search/photos"
            params = {
                "query": clean_query,
                "orientation": "portrait",
                "per_page": 20,
            }
            headers = {"Authorization": f"Client-ID {key}"}
            resp = requests.get(api_url, params=params, headers=headers, timeout=12)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    chosen = random.choice(results)
                    raw_url = chosen.get("urls", {}).get("raw") or chosen.get("urls", {}).get("regular")
                    if raw_url:
                        dl_url = f"{raw_url}&w=1080&q=85&fit=crop"
                        img_data = requests.get(dl_url, timeout=15).content
                        with open(out_file, "wb") as f_out:
                            f_out.write(img_data)
                        return resize_and_crop_to_tiktok(out_file, target_size=target_size)
        except Exception as e:
            logger.warning(f"Lỗi gọi Unsplash API: {e}, chuyển sang tải trực tiếp...")

    # Cách 2: Tìm trực tiếp từ Unsplash qua web search (Không cần API key)
    try:
        encoded_q = urllib.parse.quote(clean_query)
        search_url = f"{UNSPLASH_SEARCH_URL}{encoded_q}?orientation=portrait"
        logger.info(f"Đang tìm ảnh Unsplash với từ khóa: '{clean_query}'...")
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Trích xuất các liên kết ảnh Unsplash chất lượng cao
        photo_urls = re.findall(r"https://images\.unsplash\.com/photo-[a-zA-Z0-9_\-]+", html)
        photo_urls = list(dict.fromkeys(photo_urls))  # Loại bỏ trùng

        if photo_urls:
            # Chọn ngẫu nhiên 1 ảnh trong số các kết quả hàng đầu
            selected_base = random.choice(photo_urls[:15])
            # Tải ảnh với kích thước tối ưu 1080px chiều rộng
            dl_url = f"{selected_base}?q=85&w=1080&auto=format&fit=crop"
            logger.info(f"Đang tải ảnh Unsplash: {dl_url[:60]}...")

            img_req = urllib.request.Request(
                dl_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                with open(out_file, "wb") as f_out:
                    f_out.write(img_resp.read())

            return resize_and_crop_to_tiktok(out_file, target_size=target_size)

        raise ValueError(f"Không tìm thấy ảnh Unsplash cho '{clean_query}'.")

    except Exception as e:
        logger.warning(f"Lỗi khi tìm ảnh Unsplash: {e}. Đang tự động chuyển sang Pixabay...")
        return fetch_pixabay_image(query=clean_query, output_path=out_file)
