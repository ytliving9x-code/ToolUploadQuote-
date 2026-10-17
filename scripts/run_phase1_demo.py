"""
Script kiểm thử luồng thực thi hoàn chỉnh của GIAI ĐOẠN 1:
1. Sinh 1 quote theo chủ đề (tự động kiểm tra chống trùng lặp trong SQLite).
2. Tìm kiếm và tải 1 footage b-roll (chuẩn portrait 9:16, độ dài >= 8s, chiều rộng gần 1080px).
3. Đánh dấu footage đã sử dụng và cập nhật cơ sở dữ liệu.
"""

import json
import logging
import sys
from pathlib import Path

# Đảm bảo import được các module từ thư mục gốc dự án
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Cấu hình logging hiển thị đẹp trên console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Phase1_Demo")

from modules.history_db import get_history, init_db
from modules.pexels_api import get_footage
from modules.quote_gen import generate_quote


def main():
    logger.info("=== BẮT ĐẦU KIỂM THỬ GIAI ĐOẠN 1 ===")

    # 1. Khởi tạo DB
    init_db()

    # 2. Sinh 1 quote (chủ đề: 'điềm tĩnh')
    topic = "điềm tĩnh"
    logger.info(f"-> Bước 1: Đang sinh quote cho chủ đề '{topic}'...")
    quote_data = generate_quote(topic=topic)

    print("\n" + "=" * 60)
    print("NỘI DUNG QUOTE ĐÃ SINH:")
    print(f"Quote (Tiếng Việt): {quote_data.get('quote')}")
    print(f"Pexels Keywords:   {quote_data.get('pexels_keywords')}")
    print(f"Caption:           {quote_data.get('caption')}")
    print(f"Hashtags:          {' '.join(quote_data.get('hashtags', []))}")
    print(f"Quote ID trong DB: {quote_data.get('quote_id')}")
    print("=" * 60 + "\n")

    # 3. Tải 1 footage
    logger.info("-> Bước 2: Đang tìm kiếm và tải footage b-roll...")
    keywords = quote_data.get("pexels_keywords", ["night rain street aesthetic"])
    footage_data = get_footage(keywords=keywords, min_duration=8)

    print("\n" + "=" * 60)
    print("THÔNG TIN FOOTAGE ĐÃ TẢI:")
    print(f"Video ID:        {footage_data.get('video_id')}")
    print(f"Đường dẫn local: {footage_data.get('local_path')}")
    print(f"Độ phân giải:    {footage_data.get('width')}x{footage_data.get('height')}")
    print(f"Thời lượng:      {footage_data.get('duration')}s")
    print(f"Từ khóa khớp:    {footage_data.get('keyword')}")
    file_size_mb = Path(footage_data['local_path']).stat().st_size / 1024 / 1024
    print(f"Dung lượng file: {file_size_mb:.2f} MB")
    print("=" * 60 + "\n")

    # 4. Kiểm tra CSDL
    history = get_history(limit=5)
    logger.info(f"Tổng số bản ghi trong quotes_history: {len(history)}")
    logger.info("=== HOÀN TẤT KIỂM THỬ GIAI ĐOẠN 1 THÀNH CÔNG ===")


if __name__ == "__main__":
    main()
