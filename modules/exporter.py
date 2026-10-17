"""
Module quản lý xuất và lưu trữ video thành phẩm (exporter.py).
Chịu trách nhiệm:
1. Lưu file MP4 và file metadata .txt (caption, hashtag, credit) cùng tên theo timestamp vào output/cho_dang/.
2. Cập nhật trạng thái 'pending' vào cơ sở dữ liệu SQLite.
3. Chuyển video từ 'chờ đăng' (output/cho_dang/) sang 'đã đăng' (output/da_dang/) khi người dùng xác nhận.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.history_db import get_db_path, update_quote_status

logger = logging.getLogger("tiktok_tool.exporter")

DIR_CHO_DANG = Path("output/cho_dang")
DIR_DA_DANG = Path("output/da_dang")


def format_caption_text(quote_data: Dict[str, Any]) -> str:
    """
    Định dạng nội dung file text đi kèm video cho người dùng dễ dàng copy khi đăng TikTok.
    Bao gồm:
    - Caption
    - Hashtags
    - Gợi ý credit Pexels
    - Nội dung quote
    """
    caption = quote_data.get("caption", "").strip()
    hashtags = quote_data.get("hashtags", [])
    if isinstance(hashtags, list):
        hashtags_str = " ".join(hashtags)
    else:
        hashtags_str = str(hashtags)

    quote = quote_data.get("quote", "").strip()
    pexels_url = quote_data.get("pexels_url", "https://www.pexels.com/")

    content = f"""{caption}

{hashtags_str}

---
[Credit Footage Pexels (Tùy chọn ghi vào comment/mô tả)]:
Footage: {pexels_url}

[Nội dung Quote]:
"{quote}"
"""
    return content.strip()


def export_to_pending(
    rendered_video_path: Path | str,
    quote_data: Dict[str, Any],
    output_dir: Optional[Path | str] = None,
    custom_db_path: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """
    Xuất video MP4 và file caption .txt vào thư mục chờ đăng.

    Args:
        rendered_video_path: Đường dẫn video tạm đã dựng.
        quote_data: Dict chứa quote, caption, hashtags, quote_id...
        output_dir: Thư mục đích (mặc định output/cho_dang).
        custom_db_path: Đường dẫn CSDL tùy chọn.

    Returns:
        (mp4_path, txt_path): Cặp file đã lưu vào thư mục chờ đăng.
    """
    src_video = Path(rendered_video_path)
    if not src_video.exists():
        raise FileNotFoundError(f"Không tìm thấy file video nguồn: {src_video}")

    target_dir = Path(output_dir) if output_dir else DIR_CHO_DANG
    target_dir.mkdir(parents=True, exist_ok=True)

    # Đặt tên file theo định dạng timestamp: quote_YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"quote_{timestamp}"
    dest_video_path = target_dir / f"{base_name}.mp4"
    dest_txt_path = target_dir / f"{base_name}.txt"

    # 1. Sao chép/Di chuyển video vào thư mục chờ đăng
    shutil.copy2(src_video, dest_video_path)
    logger.info(f"Đã lưu video vào thư mục chờ đăng: {dest_video_path}")

    # 2. Tạo file text chứa caption và hashtags
    caption_content = format_caption_text(quote_data)
    with open(dest_txt_path, "w", encoding="utf-8") as f:
        f.write(caption_content)
    logger.info(f"Đã lưu file caption tương ứng: {dest_txt_path}")

    # 3. Cập nhật trạng thái 'pending' vào CSDL nếu có quote_id
    quote_id = quote_data.get("quote_id")
    if quote_id:
        update_quote_status(
            quote_id=quote_id,
            status="pending",
            video_path=str(dest_video_path),
            pexels_video_id=quote_data.get("video_id"),
            custom_path=custom_db_path,
        )

    return dest_video_path, dest_txt_path


def mark_as_published(
    video_path: Path | str,
    output_dir_published: Optional[Path | str] = None,
    custom_db_path: Optional[Path | str] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Đánh dấu video đã đăng:
    - Di chuyển cả file .mp4 và .txt từ output/cho_dang sang output/da_dang.
    - Cập nhật trạng thái 'published' trong SQLite.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        logger.warning(f"File video không tồn tại để chuyển: {v_path}")
        return None, None

    dest_dir = Path(output_dir_published) if output_dir_published else DIR_DA_DANG
    dest_dir.mkdir(parents=True, exist_ok=True)

    target_mp4 = dest_dir / v_path.name
    shutil.move(v_path, target_mp4)

    # Di chuyển file txt nếu có
    txt_source = v_path.with_suffix(".txt")
    target_txt = None
    if txt_source.exists():
        target_txt = dest_dir / txt_source.name
        shutil.move(txt_source, target_txt)

    # Cập nhật trong CSDL SQLite
    db_file = get_db_path(custom_db_path)
    import sqlite3

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE quotes_history
            SET status = 'published', published_at = ?, video_path = ?
            WHERE video_path = ? OR video_path = ?
            """,
            (datetime.now().isoformat(), str(target_mp4), str(v_path), str(target_mp4)),
        )
        conn.commit()

    logger.info(f"Đã chuyển video sang thư mục đã đăng: {target_mp4}")
    return target_mp4, target_txt


def list_pending_items(output_dir: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """
    Quét danh sách các video đang chờ đăng trong output/cho_dang.
    Đọc kèm nội dung file .txt và thời gian tạo.
    """
    target_dir = Path(output_dir) if output_dir else DIR_CHO_DANG
    target_dir.mkdir(parents=True, exist_ok=True)

    items = []
    mp4_files = sorted(target_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

    for mp4 in mp4_files:
        txt_path = mp4.with_suffix(".txt")
        caption_text = ""
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                caption_text = f.read()

        stat = mp4.stat()
        items.append({
            "name": mp4.name,
            "video_path": str(mp4),
            "txt_path": str(txt_path) if txt_path.exists() else None,
            "caption": caption_text,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return items
