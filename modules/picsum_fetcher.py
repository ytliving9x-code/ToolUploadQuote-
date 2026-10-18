"""
Module: Tải Ảnh Thật Nghệ Thuật Từ Picsum Photos (picsum_fetcher.py)
- Nguồn ảnh thật chất lượng cao hoàn toàn MIỄN PHÍ 100%, không cần bất kỳ API Key nào.
- Tự động chuẩn hóa khổ dọc 1080x1920 portrait cho video TikTok.
"""

import json
import logging
import random
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

logger = logging.getLogger("tiktok_tool.picsum_fetcher")


def fetch_picsum_image(output_path: Optional[Path] = None, grayscale: bool = False) -> Path:
    """
    Tải trực tiếp 1 bức ảnh chụp thật chất lượng cao từ Picsum Photos.
    Không cần API Key, mỗi lần gọi là 1 ảnh mới ngẫu nhiên.
    """
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    rnd_seed = int(time.time() * 1000) % 100000
    if grayscale:
        url = f"https://picsum.photos/1080/1920?grayscale&random={rnd_seed}"
    else:
        url = f"https://picsum.photos/1080/1920?random={rnd_seed}"

    logger.info(f"Đang tải ảnh thật từ Picsum Photos: {url}...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        with open(out_file, "wb") as f_out:
            f_out.write(resp.read())

    # Đảm bảo chuẩn hóa 1080x1920 và hệ màu RGB
    with Image.open(out_file) as img:
        img = img.convert("RGB")
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        img.save(out_file, format="JPEG", quality=95)

    return out_file


def get_picsum_gallery(page: Optional[int] = None, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Lấy danh sách 4 ảnh chụp thật từ Picsum Photos để hiển thị lưới gallery xem trước.
    """
    p = page if page and page > 0 else random.randint(1, 20)
    url = f"https://picsum.photos/v2/list?page={p}&limit={limit}"

    logger.info(f"Đang lấy gallery Picsum Photos trang {p}...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in data:
            item_id = item.get("id")
            # Tạo preview vuông/nhẹ và link ảnh dọc 1080x1920
            preview_url = f"https://picsum.photos/id/{item_id}/600/900"
            large_url = f"https://picsum.photos/id/{item_id}/1080/1920"
            results.append({
                "id": f"picsum_{item_id}",
                "preview_url": preview_url,
                "large_url": large_url,
                "author": item.get("author", "Picsum"),
            })
        return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy gallery Picsum: {e}")
        return []
