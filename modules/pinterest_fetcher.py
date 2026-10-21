"""
Module cào và tải ảnh tranh minh họa nghệ thuật từ Pinterest (modules/pinterest_fetcher.py).
Sử dụng pinterest-dl để lấy trực tiếp ảnh gốc độ phân giải cao nhất từ các artist:
- Retro Comic Book / Ligne Claire / Graphic Novel.
- Muted Vintage Colors, Edward Hopper mood, Melancholic Couple & Stoic Solo.
- Tự động crop và tối ưu về chuẩn TikTok dọc 1080x1920 (9:16).
"""

import logging
import os
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

logger = logging.getLogger("tiktok_tool.pinterest_fetcher")

PINTEREST_CACHE_DIR = Path("data/cache/pinterest_images")
PINTEREST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Bộ từ khóa tìm kiếm tối ưu trên Pinterest theo gu các kênh TikTok triệu view
PINTEREST_CURATED_THEMES: Dict[str, str] = {
    "👫 Cặp Đôi Lãng Mạn (Gu Just.breathe)": "retro comic couple illustration vintage ligne claire aesthetic",
    "🌧️ Phố Mưa & Bóng Ôm Nhau": "vintage comic couple rain street shadow aesthetic 1980s",
    "♟️ Bàn Cờ & Mưu Lược (Tư Mã Ý)": "retro comic noir stoic thinker chess library vintage art",
    "🚶 Bước Đi Trong Đêm (Kỷ Luật Cô Độc)": "retro comic solitary man walking night city street trench coat",
    "🌊 Bờ Biển Trăng Sao & Hoàng Hôn": "vintage comic couple seaside night moon stars retro art",
    "☕ Quán Cà Phê & Cửa Sổ Mưa": "retro comic cafe rainy window coffee aesthetic ligne claire",
    "🏢 Cao Ốc Đêm & Thành Phố": "retro graphic novel noir city skyline night solitary thinker",
}


def crop_to_tiktok_portrait(image_path: Path | str, width: int = 1080, height: int = 1920) -> Path:
    """Resize và center-crop ảnh về chuẩn khổ dọc 1080x1920 (9:16) bằng Pillow."""
    img_p = Path(image_path)
    if not img_p.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh: {img_p}")

    with Image.open(img_p) as img:
        img = img.convert("RGB")
        img_w, img_h = img.size
        target_ratio = width / height
        curr_ratio = img_w / img_h

        if curr_ratio > target_ratio:
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, img_h))
        else:
            new_h = int(img_w / target_ratio)
            top = (img_h - new_h) // 2
            img = img.crop((0, top, img_w, top + new_h))

        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img.save(img_p, "JPEG", quality=95)

    return img_p


def search_and_download_pinterest(
    query: str,
    limit: int = 4,
    output_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm và tải ảnh gốc chất lượng cao từ Pinterest.
    
    Args:
        query: Từ khóa tìm kiếm (tiếng Anh hoặc chọn từ PINTEREST_CURATED_THEMES).
        limit: Số lượng ảnh cần tải (mặc định 4).
        output_dir: Thư mục lưu ảnh.
        
    Returns:
        Danh sách dict chứa {"path": Path, "id": str, "query": str}.
    """
    dest_dir = Path(output_dir) if output_dir else PINTEREST_CACHE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    search_query = PINTEREST_CURATED_THEMES.get(query, query)
    logger.info(f"Đang tìm kiếm và tải {limit} ảnh Pinterest với từ khóa: '{search_query}'...")

    results: List[Dict[str, Any]] = []

    try:
        from pinterest_dl import PinterestDL
        client = PinterestDL.with_api()

        downloaded_files = client.search_and_download(
            query=search_query,
            output_dir=str(dest_dir),
            num=limit,
        )

        if downloaded_files:
            for f in downloaded_files:
                loc = getattr(f, "local_path", None)
                if not loc:
                    loc = str(f)
                f_path = Path(loc)
                if f_path.exists() and f_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    # Crop về khổ 9:16
                    try:
                        crop_to_tiktok_portrait(f_path)
                        results.append({
                            "path": str(f_path),
                            "name": f_path.name,
                            "query": search_query,
                        })
                    except Exception as ce:
                        logger.warning(f"Lỗi crop ảnh {f_path}: {ce}")

        return results

    except Exception as e:
        logger.warning(f"Lỗi khi cào Pinterest: {e}. Đang quét ảnh có sẵn trong cache...")
        cached_files = list(dest_dir.glob("*.jpg")) + list(dest_dir.glob("*.png"))
        if cached_files:
            for f_path in cached_files[:limit]:
                results.append({
                    "path": str(f_path),
                    "name": f_path.name,
                    "query": search_query,
                })
        return results


def get_cached_pinterest_images(limit: int = 8) -> List[Dict[str, Any]]:
    """Lấy danh sách các ảnh Pinterest đã tải về trong thư mục cache."""
    cached = list(PINTEREST_CACHE_DIR.glob("*.jpg")) + list(PINTEREST_CACHE_DIR.glob("*.png"))
    results = []
    for c in cached[:limit]:
        results.append({
            "path": str(c),
            "name": c.name,
        })
    return results
