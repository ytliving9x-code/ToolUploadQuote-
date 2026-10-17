"""
Script kiểm thử toàn diện End-to-End từ A đến Z:
1. Kết nối Google Gemini AI thật để sinh câu quote mới.
2. Lấy video b-roll từ thư viện assets/footages.
3. Dùng Pillow render typography tiếng Việt chuẩn Be Vietnam Pro (đổ bóng mềm, ngắt dòng).
4. Dùng FFmpeg dựng video hoàn chỉnh: 1080x1920, 30fps, 8s, H.264, audio=False, dark overlay 30%, fade-in/out.
5. Kiểm định các thông số kỹ thuật bằng FFmpeg probe.
6. Xuất video thành phẩm + file .txt (caption, hashtags) vào output/cho_dang/.
7. Kiểm tra ghi nhận lịch sử vào SQLite (data/history.db).
8. Báo cáo chi tiết kết quả.
"""

import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FullSystemTest")

from modules.exporter import export_to_pending, list_pending_items
from modules.history_db import get_history, init_db
from modules.pexels_api import get_footage
from modules.quote_gen import generate_quote
from modules.video_engine import build_video, validate_video


def main():
    logger.info("==================================================")
    logger.info("   BẮT ĐẦU KIỂM THỬ TOÀN DIỆN HỆ THỐNG (E2E TEST)   ")
    logger.info("==================================================")

    init_db()

    # Bước 1: Gọi Gemini AI thật
    topic = "điềm tĩnh"
    logger.info(f"\n[BƯỚC 1/6] Đang gọi Google Gemini AI sinh quote cho chủ đề '{topic}'...")
    quote_data = generate_quote(topic=topic)
    logger.info("-> Kết quả từ Gemini:")
    logger.info(f"   Quote: \"{quote_data['quote']}\"")
    logger.info(f"   Keywords: {quote_data['pexels_keywords']}")
    logger.info(f"   Caption: {quote_data['caption']}")
    logger.info(f"   Hashtags: {' '.join(quote_data['hashtags'])}")

    # Bước 2: Lấy Footage
    logger.info("\n[BƯỚC 2/6] Đang lấy video b-roll từ thư viện footages...")
    footage_data = get_footage(keywords=quote_data["pexels_keywords"], min_duration=8)
    logger.info(f"-> Footage đã chọn: {footage_data['local_path']}")
    logger.info(f"   Kích thước: {footage_data['width']}x{footage_data['height']}, Thời lượng: {footage_data['duration']}s")

    # Bước 3: Dựng Video
    logger.info("\n[BƯỚC 3/6] Đang render typography Be Vietnam Pro & ghép video bằng FFmpeg...")
    temp_render_path = Path("data/cache/test_e2e_video.mp4")
    build_video(
        footage_path=footage_data["local_path"],
        quote=quote_data["quote"],
        out_path=temp_render_path,
    )

    # Bước 4: Kiểm định chất lượng
    logger.info("\n[BƯỚC 4/6] Đang kiểm định đặc tả video bằng FFmpeg probe...")
    is_valid, msg, meta = validate_video(temp_render_path)
    logger.info(f"-> Kết quả kiểm định: Hợp lệ={is_valid} ({msg})")
    logger.info(f"   Độ phân giải: {meta['width']}x{meta['height']} (chuẩn 9:16 portrait)")
    logger.info(f"   Tốc độ khung hình: {meta['fps']} fps")
    logger.info(f"   Thời lượng: {meta['duration']} giây")
    logger.info(f"   Audio stream: {meta['has_audio']} (đúng chuẩn audio=False)")
    assert is_valid, f"Video không hợp lệ: {msg}"

    # Bước 5: Xuất vào thư mục chờ đăng
    logger.info("\n[BƯỚC 5/6] Đang xuất video và caption.txt vào output/cho_dang/...")
    dest_mp4, dest_txt = export_to_pending(
        rendered_video_path=temp_render_path,
        quote_data=quote_data,
    )
    logger.info(f"-> File video: {dest_mp4}")
    logger.info(f"-> File caption: {dest_txt}")
    assert dest_mp4.exists()
    assert dest_txt.exists()

    # Bước 6: Kiểm tra CSDL
    logger.info("\n[BƯỚC 6/6] Kiểm tra bản ghi trong SQLite database...")
    history = get_history(limit=5)
    latest_record = history[0]
    logger.info(f"-> Bản ghi mới nhất: ID={latest_record['id']}, Trạng thái={latest_record['status']}")
    assert latest_record["status"] == "pending"

    logger.info("\n==================================================")
    logger.info("   TẤT CẢ CÁC BƯỚC ĐÃ KIỂM THỬ THÀNH CÔNG 100%!   ")
    logger.info("==================================================")


if __name__ == "__main__":
    main()
