"""
Module: Lấy Video B-Roll Miễn Phí (video_fetcher.py)
Chịu trách nhiệm:
1. Tìm kiếm và tải video footage b-roll miễn phí từ Pixabay Video Search API (100% free bản quyền thương mại, có sẵn API key).
2. Tự động dịch từ khóa tiếng Việt sang tiếng Anh và cung cấp các chủ đề 1 chạm (Mưa đêm, Sói, Cà phê chill, Phố vắng...).
3. Quét và quản lý thư viện video cục bộ trong assets/footages/.
4. Trích xuất frame hình ảnh (thumbnail) từ file video để làm ảnh xem trước typography 9:16.
"""

import json
import logging
import os
import random
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from modules.pixabay_fetcher import VIETNAMESE_TO_ENGLISH_MAP

logger = logging.getLogger("tiktok_tool.video_fetcher")
load_dotenv()

# Danh mục 6 chủ đề video 1 chạm cho video ngắn TikTok
VIDEO_QUICK_THEMES_VI = {
    "🌧️ Mưa Phố Đêm": "night city rain street dark moody",
    "🐺 Sói & Đêm Lạnh": "lone wolf dark moody night winter",
    "🌲 Rừng Sương Mù": "foggy dark forest mist landscape",
    "☕ Cà Phê Trầm Lắng": "dark moody cafe coffee lonely night",
    "🌊 Biển Đêm Tĩnh": "dark calm sea ocean night misty",
    "🛣️ Đường Phố Ánh Đèn": "empty road dark night cinematic",
}

PIXABAY_VIDEOS_ENDPOINT = "https://pixabay.com/api/videos/"

try:
    FFMPEG_EXE = shutil.which("ffmpeg")
    if not FFMPEG_EXE:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"


def translate_vi_to_video_query(text: str) -> str:
    """Chuyển đổi từ khóa tiếng Việt sang từ khóa tìm kiếm video tiếng Anh."""
    clean = text.lower().strip()
    if not clean:
        return "dark night rain moody aesthetic"

    # Kiểm tra chủ đề 1 chạm
    for theme_lbl, kw in VIDEO_QUICK_THEMES_VI.items():
        if clean in theme_lbl.lower() or theme_lbl.lower() in clean:
            return kw

    # Kiểm tra từ điển tiếng Việt
    for vi_kw, en_kw in VIETNAMESE_TO_ENGLISH_MAP.items():
        if vi_kw in clean:
            clean = clean.replace(vi_kw, en_kw)

    # Loại bỏ ký tự đặc biệt
    clean = clean.replace("trời", "").replace("cảnh", "").replace("video", "").strip()
    if not clean:
        return "dark night moody aesthetic"
    return f"{clean} dark moody"


def search_pixabay_videos(
    query: str,
    api_key: Optional[str] = None,
    per_page: int = 4,
    page: int = 1,
) -> List[Dict[str, Any]]:
    """
    Gửi request tìm kiếm video đến Pixabay Video Search API.
    
    Args:
        query: Từ khóa tiếng Việt hoặc tiếng Anh.
        api_key: Pixabay API key (mặc định lấy từ config hoặc env).
        per_page: Số lượng video cần lấy (mặc định 4 để tạo lưới 2x2).
        page: Số trang.
        
    Returns:
        Danh sách dict chứa thông tin chi tiết từng video: id, preview_thumbnail, preview_video, download_url, duration, tags...
    """
    key = api_key or os.getenv("PIXABAY_API_KEY", "")
    if not key:
        cfg_path = Path("config.json")
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    key = cfg.get("pixabay_api_key", "")
            except Exception:
                pass

    if not key:
        logger.warning("Chưa cấu hình Pixabay API Key cho Video Search!")
        return []

    en_query = translate_vi_to_video_query(query)
    params = {
        "key": key,
        "q": en_query,
        "video_type": "film",
        "per_page": min(max(per_page, 3), 20),
        "page": page,
    }

    try:
        logger.info(f"Đang tìm kiếm video Pixabay với từ khóa: '{en_query}' (Trang {page})...")
        resp = requests.get(PIXABAY_VIDEOS_ENDPOINT, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            results = []
            for hit in hits:
                v_dict = hit.get("videos", {})
                # Ưu tiên kích thước medium hoặc large
                best_v = v_dict.get("medium") or v_dict.get("large") or v_dict.get("small") or v_dict.get("tiny")
                if not best_v or not best_v.get("url"):
                    continue

                thumb = (
                    best_v.get("thumbnail")
                    or v_dict.get("medium", {}).get("thumbnail")
                    or v_dict.get("small", {}).get("thumbnail")
                    or v_dict.get("tiny", {}).get("thumbnail")
                    or hit.get("userImageURL")
                )

                preview_mp4 = (
                    v_dict.get("tiny", {}).get("url")
                    or v_dict.get("small", {}).get("url")
                    or best_v.get("url")
                )

                results.append({
                    "id": hit["id"],
                    "page_url": hit.get("pageURL", "https://pixabay.com/"),
                    "duration": hit.get("duration", 0),
                    "tags": hit.get("tags", ""),
                    "views": hit.get("views", 0),
                    "likes": hit.get("likes", 0),
                    "thumbnail": thumb,
                    "preview_mp4": preview_mp4,
                    "download_url": best_v["url"],
                    "width": best_v.get("width", 1080),
                    "height": best_v.get("height", 1920),
                    "size_mb": round(best_v.get("size", 0) / (1024 * 1024), 2),
                })
            return results
        else:
            logger.warning(f"Pixabay API trả về mã lỗi: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Lỗi khi tìm video Pixabay: {e}")

    return []


def download_video_stream(
    url: str,
    output_path: Path | str,
    chunk_size: int = 1024 * 64,
    timeout: int = 60,
) -> Path:
    """
    Tải file video từ URL về đường dẫn chỉ định với cơ chế stream chunk và file tạm .tmp.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = out_file.with_suffix(".tmp")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    logger.info(f"Bắt đầu tải video từ {url[:60]}... về {out_file.name}")
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(temp_file, "wb") as f_out:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f_out.write(chunk)

    if temp_file.exists():
        if out_file.exists():
            out_file.unlink()
        temp_file.rename(out_file)

    logger.info(f"Đã tải thành công video: {out_file} ({out_file.stat().st_size / (1024 * 1024):.2f} MB)")
    return out_file


def fetch_pixabay_video_quick(
    query: str,
    api_key: Optional[str] = None,
    output_path: Optional[Path | str] = None,
) -> Path:
    """
    Tìm kiếm và tải ngay 1 video ngẫu nhiên theo chủ đề từ Pixabay.
    """
    out_p = Path(output_path) if output_path else Path("temp/background_video.mp4")
    out_p.parent.mkdir(parents=True, exist_ok=True)

    videos = search_pixabay_videos(query=query, api_key=api_key, per_page=10, page=1)
    if not videos:
        # Thử lại với từ khóa mặc định
        videos = search_pixabay_videos(query="night rain", api_key=api_key, per_page=10, page=1)

    if not videos:
        # Nếu không có mạng hoặc lỗi, dùng video mẫu trong assets/footages/
        local_samples = get_local_footages()
        if local_samples:
            chosen = random.choice(local_samples)
            shutil.copy2(chosen["path"], out_p)
            return out_p
        raise RuntimeError("Không tìm thấy video nào từ Pixabay và không có video cục bộ dự phòng.")

    chosen_video = random.choice(videos)
    return download_video_stream(chosen_video["download_url"], out_p)


def get_local_footages(footages_dir: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """
    Quét danh sách tất cả các video b-roll có sẵn trong thư mục assets/footages/.
    """
    f_dir = Path(footages_dir) if footages_dir else Path("assets/footages")
    if not f_dir.exists():
        return []

    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    found = []
    for f in f_dir.glob("*.*"):
        if f.suffix.lower() in video_exts and f.stat().st_size > 1000:
            found.append({
                "name": f.stem.replace("_", " ").title(),
                "filename": f.name,
                "path": str(f),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            })
    return sorted(found, key=lambda x: x["name"])


def extract_video_frame(
    video_path: Path | str,
    output_path: Optional[Path | str] = None,
    timestamp_sec: float = 1.0,
) -> Path:
    """
    Dùng FFmpeg trích xuất 1 khung hình từ video để làm ảnh xem trước typography 9:16.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {v_path}")

    out_frame = Path(output_path) if output_path else Path("temp/video_frame_preview.jpg")
    out_frame.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-ss", str(timestamp_sec),
        "-i", str(v_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_frame),
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and out_frame.exists() and out_frame.stat().st_size > 500:
            return out_frame
        
        # Nếu ở 1.0s không lấy được, thử ở 0.0s
        cmd[2] = "0.0"
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and out_frame.exists() and out_frame.stat().st_size > 500:
            return out_frame
    except Exception as e:
        logger.warning(f"Lỗi khi trích xuất frame bằng FFmpeg: {e}")

    # Fallback: Tạo ảnh màu tối giả lập nếu không trích xuất được
    from PIL import Image
    fallback_img = Image.new("RGB", (1080, 1920), (20, 25, 35))
    fallback_img.save(out_frame, format="JPEG", quality=90)
    return out_frame
