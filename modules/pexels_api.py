"""
Module tích hợp Pexels Video Search API.
Chịu trách nhiệm tìm kiếm video b-roll tông trầm tối, lọc định dạng dọc (portrait),
độ dài >= 8s, chọn chất lượng tối ưu (gần 1080px), tải về thư mục cache và chống dùng lại footage cũ.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from modules.history_db import is_footage_used, mark_footage_used

logger = logging.getLogger("tiktok_tool.pexels_api")

# Tải biến môi trường từ .env
load_dotenv()

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
CACHE_DIR = Path("data/cache")


def get_pexels_api_key(api_key: Optional[str] = None) -> str:
    """Lấy API key của Pexels từ tham số hoặc biến môi trường."""
    key = api_key or os.getenv("PEXELS_API_KEY", "")
    return key.strip()


def select_best_video_file(video_files: List[Dict[str, Any]], target_width: int = 1080) -> Optional[Dict[str, Any]]:
    """
    Chọn file video tối ưu nhất từ danh sách 'video_files' của Pexels:
    1. Ưu tiên định dạng MP4 ('video/mp4').
    2. Chiều dọc (height >= width).
    3. Có chiều rộng gần target_width (1080px) nhất để tiết kiệm băng thông và tránh file 4K quá nặng.

    Args:
        video_files: Danh sách các file video từ Pexels API.
        target_width: Chiều rộng mục tiêu (mặc định 1080).

    Returns:
        Dict của video_file tối ưu, hoặc None nếu không có file phù hợp.
    """
    if not video_files:
        return None

    # Lọc các file MP4 hợp lệ có width và height
    valid_files = []
    for f in video_files:
        if f.get("file_type") == "video/mp4" and f.get("link"):
            w = f.get("width") or 0
            h = f.get("height") or 0
            if w > 0 and h > 0:
                valid_files.append(f)

    if not valid_files:
        # Nếu không có định dạng chuẩn, lấy các file có link bất kỳ
        valid_files = [f for f in video_files if f.get("link")]
        if not valid_files:
            return None

    # Ưu tiên các file có tỷ lệ dọc (portrait)
    portrait_files = [f for f in valid_files if (f.get("height") or 0) >= (f.get("width") or 0)]
    pool = portrait_files if portrait_files else valid_files

    # Sắp xếp theo độ chênh lệch chiều rộng so với target_width
    def sort_key(item: Dict[str, Any]) -> Tuple[int, int]:
        w = item.get("width") or 0
        diff = abs(w - target_width)
        # Nếu chiều rộng bằng hoặc gần 1080 (ví dụ 1080, 720) thì ưu tiên cao hơn 4K (2160)
        is_4k_penalty = 1 if w > 1920 else 0
        return (is_4k_penalty, diff)

    best_file = min(pool, key=sort_key)
    return best_file


def search_pexels_videos(
    query: str,
    api_key: Optional[str] = None,
    orientation: str = "portrait",
    per_page: int = 20,
    page: int = 1,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Gửi request tìm kiếm video đến Pexels Video Search API.
    Có xử lý lỗi mạng và rate limit (HTTP 429).
    """
    key = get_pexels_api_key(api_key)
    if not key or key == "your_pexels_api_key_here":
        raise ValueError(
            "Chưa cấu hình PEXELS_API_KEY trong file .env! Vui lòng đăng ký key miễn phí tại https://www.pexels.com/api/"
        )

    headers = {
        "Authorization": key,
        "User-Agent": "TikTokQuoteGenerator/1.0",
    }
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": per_page,
        "page": page,
    }

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Đang tìm video Pexels với từ khóa: '{query}' (Trang {page}, Lần thử {attempt})...")
            response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                wait_time = int(response.headers.get("Retry-After", 10 * attempt))
                logger.warning(f"Bị chạm giới hạn tốc độ (Rate Limit 429). Đang chờ {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code == 401:
                raise ValueError("PEXELS_API_KEY không hợp lệ hoặc đã hết hạn!")

            response.raise_for_status()

        except requests.exceptions.Timeout:
            logger.warning(f"Quá thời gian kết nối (Timeout) khi tìm kiếm Pexels lần {attempt}...")
            time.sleep(2 * attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi mạng khi gọi Pexels API: {e}")
            if attempt == max_retries:
                raise

    return {"videos": []}


def find_and_select_footage(
    keywords: List[str],
    min_duration: int = 8,
    max_duration: int = 60,
    api_key: Optional[str] = None,
    custom_db_path: Optional[str | Path] = None,
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], str]]:
    """
    Duyệt qua danh sách từ khóa để tìm video Pexels phù hợp tiêu chí:
    - Độ dài: min_duration <= duration <= max_duration (mặc định 8s - 60s).
    - Chưa từng sử dụng trong bảng used_footage của SQLite.
    - Tìm được video file tối ưu gần 1080px.

    Args:
        keywords: Danh sách từ khóa (ví dụ: ["rain night street", "dark subway"]).
        min_duration: Thời lượng tối thiểu (giây).
        max_duration: Thời lượng tối đa (giây).
        api_key: Key tùy chọn.
        custom_db_path: Đường dẫn CSDL tùy chọn.

    Returns:
        (video_item, chosen_file, matched_keyword) hoặc None nếu không tìm thấy.
    """
    # Nếu danh sách từ khóa rỗng, dùng các từ khóa mặc định tông trầm tối
    default_fallbacks = ["night rain street aesthetic", "dark city moody rain", "dark subway train", "calm rainy coffee"]
    search_list = [k for k in keywords if k.strip()] + default_fallbacks

    for kw in search_list:
        try:
            data = search_pexels_videos(query=kw, api_key=api_key)
            videos = data.get("videos", [])
            logger.info(f"Từ khóa '{kw}' trả về {len(videos)} video từ Pexels.")

            for vid in videos:
                vid_id = vid.get("id")
                duration = vid.get("duration", 0)

                # Kiểm tra độ dài video
                if duration < min_duration or (max_duration and duration > max_duration):
                    continue

                # Kiểm tra chống dùng lại footage đã dùng
                if is_footage_used(vid_id, custom_path=custom_db_path):
                    logger.debug(f"Video Pexels ID={vid_id} đã từng sử dụng trước đây, bỏ qua.")
                    continue

                # Chọn video file tối ưu
                video_files = vid.get("video_files", [])
                best_file = select_best_video_file(video_files, target_width=1080)
                if best_file:
                    logger.info(
                        f"Đã chọn được footage Pexels ID={vid_id} (thời lượng: {duration}s, "
                        f"độ phân giải file: {best_file.get('width')}x{best_file.get('height')})."
                    )
                    return vid, best_file, kw

        except Exception as e:
            logger.warning(f"Lỗi khi tìm kiếm với từ khóa '{kw}': {e}")
            continue

    return None


def download_video_file(
    file_url: str,
    output_path: Path,
    expected_size: Optional[int] = None,
    chunk_size: int = 1024 * 64,
) -> Path:
    """
    Tải file video từ URL về đường dẫn chỉ định với cơ chế stream chunk.

    Args:
        file_url: Đường dẫn tải file MP4 trực tiếp.
        output_path: Nơi lưu file trên máy tính.
        expected_size: Kích thước file dự kiến (nếu có).
        chunk_size: Kích thước từng khối khi tải.

    Returns:
        Đường dẫn file sau khi tải thành công.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".tmp")

    headers = {
        "User-Agent": "TikTokQuoteGenerator/1.0",
    }

    logger.info(f"Bắt đầu tải video từ {file_url[:60]}... về {output_path.name}")
    with requests.get(file_url, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

    # Đổi tên từ .tmp sang file hoàn chỉnh
    if temp_path.exists():
        if output_path.exists():
            output_path.unlink()
        temp_path.rename(output_path)

    logger.info(f"Đã tải xong video: {output_path} (Kích thước: {output_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return output_path


def get_footage(
    keywords: List[str],
    min_duration: int = 8,
    api_key: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    custom_db_path: Optional[str | Path] = None,
    mark_used: bool = True,
) -> Dict[str, Any]:
    """
    Tìm và tải footage phù hợp về thư mục cache, đồng thời ghi nhận vào cơ sở dữ liệu.

    Args:
        keywords: Danh sách từ khóa tìm kiếm.
        min_duration: Độ dài tối thiểu.
        api_key: Pexels API key.
        cache_dir: Thư mục cache (mặc định data/cache).
        custom_db_path: Đường dẫn CSDL tùy chọn.
        mark_used: Có đánh dấu video là đã dùng trong DB hay không.

    Returns:
        Dict chứa:
        - 'video_id': ID của video Pexels.
        - 'local_path': Đường dẫn file cục bộ trong cache.
        - 'pexels_url': Link video trên Pexels.
        - 'duration': Thời lượng video gốc.
        - 'width': Chiều rộng file gốc.
        - 'height': Chiều cao file gốc.
        - 'keyword': Từ khóa tìm thấy.
    """
def generate_sample_broll_footage(
    output_path: Path,
    duration: int = 9,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Path:
    """
    Tạo video b-roll mẫu tông trầm tối thẩm mỹ (dark moody gradient & bokeh)
    dùng cho kiểm thử hoặc dự phòng khi chưa cấu hình PEXELS_API_KEY.
    """
    import imageio
    import numpy as np

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 10000:
        return output_path

    total_frames = int(duration * fps)
    writer = imageio.get_writer(
        str(output_path),
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=None,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )

    # Tạo gradient nền tông xanh đêm trầm tối
    y = np.linspace(15, 40, height)[:, None]
    x = np.linspace(10, 30, width)[None, :]
    base_r = (y * 0.4 + x * 0.3).astype(np.float32)
    base_g = (y * 0.6 + x * 0.5).astype(np.float32)
    base_b = (y * 1.1 + x * 0.9).astype(np.float32)

    # Tạo các điểm đốm sáng mờ (bokeh) chuyển động nhẹ
    num_particles = 18
    np.random.seed(42)
    px = np.random.uniform(100, width - 100, num_particles)
    py = np.random.uniform(100, height - 100, num_particles)
    pr = np.random.uniform(40, 120, num_particles)
    pspeed = np.random.uniform(0.3, 1.2, num_particles)

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Hiệu ứng thở nhẹ theo thời gian
        t_factor = 1.0 + 0.08 * np.sin(2 * np.pi * i / (fps * 4))
        frame[:, :, 0] = np.clip(base_r * t_factor, 0, 255).astype(np.uint8)
        frame[:, :, 1] = np.clip(base_g * t_factor, 0, 255).astype(np.uint8)
        frame[:, :, 2] = np.clip(base_b * t_factor, 0, 255).astype(np.uint8)

        writer.append_data(frame)

    writer.close()
    logger.info(f"Đã tạo video mẫu fallback aesthetic tại: {output_path}")
    return output_path


def get_footage(
    keywords: List[str],
    min_duration: int = 8,
    api_key: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    custom_db_path: Optional[str | Path] = None,
    mark_used: bool = True,
) -> Dict[str, Any]:
    """
    Tìm và tải footage phù hợp về thư mục cache, đồng thời ghi nhận vào cơ sở dữ liệu.

    Args:
        keywords: Danh sách từ khóa tìm kiếm.
        min_duration: Độ dài tối thiểu.
        api_key: Pexels API key.
        cache_dir: Thư mục cache (mặc định data/cache).
        custom_db_path: Đường dẫn CSDL tùy chọn.
        mark_used: Có đánh dấu video là đã dùng trong DB hay không.

    Returns:
        Dict chứa thông tin video đã tải.
    """
    c_dir = Path(cache_dir) if cache_dir else CACHE_DIR
    c_dir.mkdir(parents=True, exist_ok=True)

def search_pixabay_videos(
    query: str,
    api_key: Optional[str] = None,
    per_page: int = 15,
) -> Dict[str, Any]:
    """Tìm kiếm video b-roll trên Pixabay API (miễn phí, không bị pause cấp key)."""
    key = api_key or os.getenv("PIXABAY_API_KEY", "")
    if not key:
        return {"hits": []}

    url = "https://pixabay.com/api/videos/"
    params = {
        "key": key,
        "q": query,
        "video_type": "film",
        "per_page": per_page,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"Lỗi khi tìm kiếm Pixabay: {e}")
    return {"hits": []}


def get_local_footage() -> Optional[Path]:
    """Lấy ngẫu nhiên một file video b-roll từ thư mục assets/footages/ nếu có."""
    import random
    local_dir = Path("assets/footages")
    if local_dir.exists():
        video_files = list(local_dir.glob("*.mp4"))
        if video_files:
            return random.choice(video_files)
    return None


def get_footage(
    keywords: List[str],
    min_duration: int = 8,
    api_key: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    custom_db_path: Optional[str | Path] = None,
    mark_used: bool = True,
) -> Dict[str, Any]:
    """
    Tìm và lấy footage b-roll phù hợp:
    1. Ưu tiên Pexels API nếu có PEXELS_API_KEY hợp lệ.
    2. Nếu Pexels không có key (do Pexels tạm dừng cấp mới), tự động tìm qua Pixabay API nếu có PIXABAY_API_KEY.
    3. Tự động lấy từ kho video cục bộ assets/footages/ (người dùng có thể thả file video vào đây).
    4. Dự phòng bằng video mẫu b-roll aesthetic tự tạo sẵn trong cache.
    """
    c_dir = Path(cache_dir) if cache_dir else CACHE_DIR
    c_dir.mkdir(parents=True, exist_ok=True)

    key = get_pexels_api_key(api_key)

    # 1. Nếu có Pexels Key, gọi Pexels API
    if key and key != "your_pexels_api_key_here":
        try:
            result = find_and_select_footage(
                keywords=keywords,
                min_duration=min_duration,
                api_key=api_key,
                custom_db_path=custom_db_path,
            )
            if result:
                vid, chosen_file, matched_kw = result
                vid_id = vid["id"]
                file_id = chosen_file.get("id", "def")
                file_url = chosen_file["link"]
                width = chosen_file.get("width", 0)
                height = chosen_file.get("height", 0)
                duration = vid.get("duration", 0)
                pexels_url = vid.get("url", "")

                target_filename = f"pexels_{vid_id}_{file_id}.mp4"
                local_file = c_dir / target_filename
                if not (local_file.exists() and local_file.stat().st_size > 10000):
                    download_video_file(file_url, local_file)

                if mark_used:
                    mark_footage_used(
                        pexels_video_id=vid_id,
                        query_keyword=matched_kw,
                        pexels_url=pexels_url,
                        width=width,
                        height=height,
                        duration=duration,
                        custom_path=custom_db_path,
                    )

                return {
                    "video_id": vid_id,
                    "local_path": str(local_file),
                    "pexels_url": pexels_url,
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "keyword": matched_kw,
                }
        except Exception as e:
            logger.warning(f"Không thể tải từ Pexels API: {e}")

    # 2. Thử qua Pixabay API nếu có cấu hình PIXABAY_API_KEY
    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if pixabay_key:
        for kw in keywords:
            data = search_pixabay_videos(query=kw, api_key=pixabay_key)
            hits = data.get("hits", [])
            for hit in hits:
                v_id = hit["id"]
                dur = hit.get("duration", 0)
                if dur < min_duration:
                    continue
                videos = hit.get("videos", {})
                v_choice = videos.get("medium") or videos.get("large") or videos.get("small")
                if v_choice and v_choice.get("url"):
                    local_pb = c_dir / f"pixabay_{v_id}.mp4"
                    if not local_pb.exists():
                        download_video_file(v_choice["url"], local_pb)
                    return {
                        "video_id": v_id,
                        "local_path": str(local_pb),
                        "pexels_url": hit.get("pageURL", "https://pixabay.com/"),
                        "duration": dur,
                        "width": v_choice.get("width", 1080),
                        "height": v_choice.get("height", 1920),
                        "keyword": kw,
                    }

    # 3. Lấy từ thư viện video local assets/footages/
    local_vid = get_local_footage()
    if local_vid and local_vid.exists():
        logger.info(f"Sử dụng video b-roll từ thư viện assets/footages/: {local_vid.name}")
        return {
            "video_id": 888888,
            "local_path": str(local_vid),
            "pexels_url": f"Local Footage ({local_vid.name})",
            "duration": 9.0,
            "width": 1080,
            "height": 1920,
            "keyword": local_vid.stem.replace("_", " "),
        }

    # 4. Dự phòng tạo video aesthetic
    sample_path = c_dir / "sample_aesthetic_broll_1080x1920.mp4"
    generate_sample_broll_footage(sample_path, duration=9, width=1080, height=1920)
    return {
        "video_id": 999999,
        "local_path": str(sample_path),
        "pexels_url": "https://www.pexels.com/ (Sample B-roll)",
        "duration": 9.0,
        "width": 1080,
        "height": 1920,
        "keyword": keywords[0] if keywords else "dark aesthetic moody",
    }

    vid, chosen_file, matched_kw = result
    vid_id = vid["id"]
    file_id = chosen_file.get("id", "def")
    file_url = chosen_file["link"]
    width = chosen_file.get("width", 0)
    height = chosen_file.get("height", 0)
    duration = vid.get("duration", 0)
    pexels_url = vid.get("url", "")

    # Đặt tên file cache
    target_filename = f"pexels_{vid_id}_{file_id}.mp4"
    local_file = c_dir / target_filename

    # Nếu file đã tải trong cache rồi thì không cần tải lại
    if not (local_file.exists() and local_file.stat().st_size > 10000):
        download_video_file(file_url, local_file)

    # Đánh dấu đã dùng vào SQLite
    if mark_used:
        mark_footage_used(
            pexels_video_id=vid_id,
            query_keyword=matched_kw,
            pexels_url=pexels_url,
            width=width,
            height=height,
            duration=duration,
            custom_path=custom_db_path,
        )

    return {
        "video_id": vid_id,
        "local_path": str(local_file),
        "pexels_url": pexels_url,
        "duration": duration,
        "width": width,
        "height": height,
        "keyword": matched_kw,
    }


# ==============================================================================
# PEXELS PHOTO SEARCH & DOWNLOAD (HÌNH NỀN 1080x1920 DỌC CHO VIDEO TIKTOK)
# ==============================================================================
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"


def fetch_pexels_photo(
    query: str,
    api_key: Optional[str] = None,
    output_path: Optional[Path] = None,
    target_size: Tuple[int, int] = (1080, 1920),
) -> Path:
    """
    Tìm kiếm và tải 1 ảnh chất lượng cao khổ dọc (portrait) từ Pexels.
    Tự động crop chuẩn 1080x1920 bằng hàm resize_and_crop_to_tiktok.
    Nếu chưa có key hoặc lỗi, tự động fallback sang Pixabay hoặc ảnh AI.
    """
    out_file = Path(output_path) if output_path else Path("temp/background.jpg")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    key = api_key or os.getenv("PEXELS_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            if "PEXELS_API_KEY" in st.secrets:
                key = st.secrets["PEXELS_API_KEY"]
        except Exception:
            pass

    clean_query = query.strip() if query else "dark aesthetic moody"

    if not key:
        logger.warning("Chưa cấu hình PEXELS_API_KEY, fallback sang Pixabay...")
        from modules.pixabay_fetcher import fetch_pixabay_image
        return fetch_pixabay_image(query=clean_query, output_path=out_file)

    headers = {
        "Authorization": key,
        "User-Agent": "TikTokQuoteGenerator/1.0",
    }
    params = {
        "query": clean_query,
        "orientation": "portrait",
        "per_page": 25,
    }

    try:
        logger.info(f"Đang tìm ảnh Pexels với từ khóa: '{clean_query}'...")
        resp = requests.get(PEXELS_PHOTO_SEARCH_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        photos = data.get("photos", [])

        if not photos:
            # Thử lại với từ khóa rộng hơn
            params["query"] = "dark street night"
            resp_fallback = requests.get(PEXELS_PHOTO_SEARCH_URL, headers=headers, params=params, timeout=15)
            if resp_fallback.status_code == 200:
                photos = resp_fallback.json().get("photos", [])

        if photos:
            import random
            selected_photo = random.choice(photos)
            src_dict = selected_photo.get("src", {})
            img_url = src_dict.get("large2x") or src_dict.get("original") or src_dict.get("large")

            if img_url:
                logger.info(f"Đang tải ảnh Pexels ID={selected_photo.get('id')} từ: {img_url[:60]}...")
                img_resp = requests.get(img_url, timeout=20)
                img_resp.raise_for_status()
                with open(out_file, "wb") as f_out:
                    f_out.write(img_resp.content)

                from modules.pixabay_fetcher import resize_and_crop_to_tiktok
                return resize_and_crop_to_tiktok(out_file, target_size=target_size)

        raise ValueError(f"Không tìm thấy ảnh phù hợp trên Pexels cho '{clean_query}'.")

    except Exception as e:
        logger.warning(f"Lỗi khi tìm ảnh Pexels: {e}. Đang fallback sang Pixabay...")
        from modules.pixabay_fetcher import fetch_pixabay_image
        return fetch_pixabay_image(query=clean_query, output_path=out_file)

