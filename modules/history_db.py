"""
Module quản lý cơ sở dữ liệu lịch sử (SQLite) cho ứng dụng tạo video TikTok Quote.
Chịu trách nhiệm lưu trữ quote đã tạo, footage Pexels đã dùng và kiểm tra chống trùng lặp.
"""

import difflib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("tiktok_tool.history_db")

DEFAULT_DB_PATH = Path("data/history.db")


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Lấy đường dẫn file SQLite database, tạo thư mục cha nếu chưa có."""
    path = Path(custom_path) if custom_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db(custom_path: Optional[str | Path] = None) -> None:
    """
    Khởi tạo cấu trúc các bảng trong SQLite nếu chưa tồn tại.
    Bao gồm:
      - quotes_history: lưu lịch sử quote, caption, trạng thái (generated, pending, published).
      - used_footage: lưu ID footage Pexels đã được tải/sử dụng để tránh lặp video.
    """
    db_file = get_db_path(custom_path)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT NOT NULL,
                topic TEXT NOT NULL,
                pexels_keywords TEXT,
                caption TEXT,
                hashtags TEXT,
                status TEXT DEFAULT 'generated',
                video_path TEXT,
                pexels_video_id INTEGER,
                created_at TEXT NOT NULL,
                published_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS used_footage (
                pexels_video_id INTEGER PRIMARY KEY,
                query_keyword TEXT,
                pexels_url TEXT,
                width INTEGER,
                height INTEGER,
                duration REAL,
                used_at TEXT NOT NULL
            )
            """
        )

        # Index tối ưu tìm kiếm
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quotes_created ON quotes_history(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes_history(status)")
        conn.commit()
    logger.debug(f"Đã khởi tạo database tại: {db_file}")


def calculate_similarity(text1: str, text2: str) -> float:
    """Tính độ tương đồng giữa hai chuỗi văn bản (từ 0.0 đến 1.0)."""
    s1 = " ".join(text1.lower().strip().split())
    s2 = " ".join(text2.lower().strip().split())
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def is_quote_duplicate(
    new_quote: str,
    threshold: float = 0.70,
    custom_path: Optional[str | Path] = None,
) -> Tuple[bool, float, Optional[str]]:
    """
    Kiểm tra xem quote mới có bị trùng hoặc quá giống các quote đã lưu trong lịch sử không.
    
    Args:
        new_quote: Câu quote mới cần kiểm tra.
        threshold: Ngưỡng tương đồng (0.0 - 1.0), mặc định 0.70.
        custom_path: Đường dẫn CSDL tùy chọn.

    Returns:
        (is_dup, max_ratio, matched_quote):
        - is_dup: True nếu độ tương đồng >= threshold hoặc trùng hoàn toàn.
        - max_ratio: Tỷ lệ tương đồng cao nhất tìm thấy.
        - matched_quote: Nội dung quote trong DB bị trùng (nếu có).
    """
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT quote FROM quotes_history ORDER BY id DESC LIMIT 500")
        rows = cursor.fetchall()

    if not rows:
        return False, 0.0, None

    max_ratio = 0.0
    matched_quote: Optional[str] = None

    for (existing_quote,) in rows:
        ratio = calculate_similarity(new_quote, existing_quote)
        if ratio > max_ratio:
            max_ratio = ratio
            matched_quote = existing_quote
        if ratio >= threshold:
            logger.warning(
                f"Phát hiện quote trùng lặp (độ giống {ratio:.1%}):\n"
                f"Mới: '{new_quote}'\nCũ: '{existing_quote}'"
            )
            return True, ratio, existing_quote

    return False, max_ratio, matched_quote


def save_quote(
    quote_data: Dict[str, Any],
    topic: str,
    status: str = "generated",
    custom_path: Optional[str | Path] = None,
) -> int:
    """
    Lưu quote mới vào bảng quotes_history.

    Args:
        quote_data: Dict chứa các trường 'quote', 'pexels_keywords', 'caption', 'hashtags'.
        topic: Chủ đề (nỗ lực, tiền bạc, điềm tĩnh, chữa lành...).
        status: Trạng thái ban đầu ('generated', 'pending', 'published').
        custom_path: Đường dẫn CSDL tùy chọn.

    Returns:
        ID của bản ghi vừa chèn.
    """
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    quote = quote_data.get("quote", "").strip()
    keywords = quote_data.get("pexels_keywords", [])
    if isinstance(keywords, list):
        keywords_str = json.dumps(keywords, ensure_ascii=False)
    else:
        keywords_str = str(keywords)

    caption = quote_data.get("caption", "").strip()
    hashtags = quote_data.get("hashtags", [])
    if isinstance(hashtags, list):
        hashtags_str = json.dumps(hashtags, ensure_ascii=False)
    else:
        hashtags_str = str(hashtags)

    created_at = datetime.now().isoformat()

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quotes_history (quote, topic, pexels_keywords, caption, hashtags, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (quote, topic, keywords_str, caption, hashtags_str, status, created_at),
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"Đã lưu quote ID={record_id} vào database.")
        return record_id or 0


def is_footage_used(pexels_video_id: int, custom_path: Optional[str | Path] = None) -> bool:
    """Kiểm tra xem footage Pexels đã từng được dùng hay chưa."""
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM used_footage WHERE pexels_video_id = ? LIMIT 1", (pexels_video_id,))
        return cursor.fetchone() is not None


def mark_footage_used(
    pexels_video_id: int,
    query_keyword: str = "",
    pexels_url: str = "",
    width: int = 0,
    height: int = 0,
    duration: float = 0.0,
    custom_path: Optional[str | Path] = None,
) -> None:
    """Ghi nhận footage Pexels đã được tải/sử dụng vào DB."""
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    used_at = datetime.now().isoformat()
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO used_footage (pexels_video_id, query_keyword, pexels_url, width, height, duration, used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pexels_video_id, query_keyword, pexels_url, width, height, duration, used_at),
        )
        conn.commit()
    logger.info(f"Đã đánh dấu footage ID={pexels_video_id} là đã sử dụng.")


def update_quote_status(
    quote_id: int,
    status: str,
    video_path: Optional[str] = None,
    pexels_video_id: Optional[int] = None,
    custom_path: Optional[str | Path] = None,
) -> None:
    """Cập nhật trạng thái và thông tin video cho quote."""
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        query = "UPDATE quotes_history SET status = ?"
        params: List[Any] = [status]

        if video_path is not None:
            query += ", video_path = ?"
            params.append(video_path)
        if pexels_video_id is not None:
            query += ", pexels_video_id = ?"
            params.append(pexels_video_id)
        if status == "published":
            query += ", published_at = ?"
            params.append(datetime.now().isoformat())

        query += " WHERE id = ?"
        params.append(quote_id)
        cursor.execute(query, tuple(params))
        conn.commit()
    logger.info(f"Đã cập nhật quote ID={quote_id} -> status={status}")


def get_history(limit: int = 100, custom_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách lịch sử tạo video, sắp xếp theo thời gian mới nhất."""
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, quote, topic, pexels_keywords, caption, hashtags,
                   status, video_path, pexels_video_id, created_at, published_at
            FROM quotes_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

    results = []
    for r in rows:
        row_dict = dict(r)
        # Parse JSON nếu có thể
        try:
            row_dict["pexels_keywords"] = json.loads(row_dict["pexels_keywords"])
        except Exception:
            pass
        try:
            row_dict["hashtags"] = json.loads(row_dict["hashtags"])
        except Exception:
            pass
        results.append(row_dict)
    return results


def get_pending_videos(custom_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách các video đang ở trạng thái 'pending' (chờ đăng)."""
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, quote, topic, caption, hashtags, video_path, created_at
            FROM quotes_history
            WHERE status = 'pending'
            ORDER BY id DESC
            """
        )
        return [dict(r) for r in cursor.fetchall()]
