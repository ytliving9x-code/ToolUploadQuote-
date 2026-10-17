"""
Công cụ dòng lệnh CLI sản xuất video tự động không cần giao diện (cli.py).
Dùng cho lập lịch chạy định kỳ (Windows Task Scheduler hoặc cron lúc 11:30 và 21:30).

Cách dùng:
    python cli.py --count 2
    python cli.py --count 1 --topic "điềm tĩnh"
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TikTokCLI")

from modules.exporter import export_to_pending
from modules.history_db import init_db
from modules.pexels_api import get_footage
from modules.quote_gen import generate_quote
from modules.video_engine import build_video, validate_video


def run_pipeline(count: int = 1, topic: str = "random", config_path: str = "config.json") -> None:
    """
    Quy trình tự động sản xuất N video và lưu vào output/cho_dang/.
    """
    init_db()

    # Nạp cấu hình
    cfg_file = Path(config_path)
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    topics_list = config.get("topics", ["điềm tĩnh", "nỗ lực", "tiền bạc", "chữa lành"])

    logger.info(f"=== BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG SẢN XUẤT {count} VIDEO ===")
    success_count = 0

    for idx in range(1, count + 1):
        chosen_topic = random.choice(topics_list) if topic == "random" else topic
        logger.info(f"\n[Video #{idx}/{count}] Bắt đầu sản xuất cho chủ đề: '{chosen_topic}'")

        try:
            # 1. Sinh Quote
            logger.info("-> 1. Đang sinh nội dung quote...")
            quote_data = generate_quote(topic=chosen_topic, config=config)
            logger.info(f"Quote: \"{quote_data['quote']}\"")

            # 2. Lấy Footage Pexels
            logger.info("-> 2. Đang tìm kiếm và tải footage b-roll...")
            keywords = quote_data.get("pexels_keywords", ["night rain street aesthetic"])
            footage_data = get_footage(keywords=keywords, min_duration=8)
            quote_data["pexels_url"] = footage_data.get("pexels_url", "https://www.pexels.com/")
            quote_data["video_id"] = footage_data.get("video_id")

            # 3. Dựng Video
            logger.info("-> 3. Đang render typography và phủ overlay...")
            temp_output = Path(f"data/cache/temp_cli_render_{idx}.mp4")
            build_video(
                footage_path=footage_data["local_path"],
                quote=quote_data["quote"],
                out_path=temp_output,
                config=config,
            )

            # Kiểm định video
            is_valid, msg, meta = validate_video(temp_output)
            if not is_valid:
                logger.warning(f"Video #{idx} có cảnh báo: {msg}")

            # 4. Xuất vào thư mục chờ đăng
            logger.info("-> 4. Đang xuất MP4 và file caption.txt vào output/cho_dang/...")
            dest_mp4, dest_txt = export_to_pending(
                rendered_video_path=temp_output,
                quote_data=quote_data,
            )

            # Xóa file render tạm
            if temp_output.exists():
                temp_output.unlink()

            success_count += 1
            logger.info(f"✅ Thành công Video #{idx}: {dest_mp4.name} ({meta['duration']}s, {meta['fps']}fps)")

        except Exception as e:
            logger.error(f"❌ Thất bại khi tạo Video #{idx}: {e}", exc_info=True)

    logger.info(f"\n=== HOÀN TẤT: Đã tạo thành công {success_count}/{count} video vào output/cho_dang/ ===")


def main():
    parser = argparse.ArgumentParser(description="Tool tự động sản xuất video TikTok Aesthetic Quote.")
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Số lượng video cần sản xuất (mặc định: 1)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="random",
        help="Chủ đề quote ('điềm tĩnh', 'nỗ lực', 'tiền bạc', 'chữa lành', hoặc 'random')",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Đường dẫn file cấu hình (mặc định: config.json)",
    )

    args = parser.parse_args()
    run_pipeline(count=args.count, topic=args.topic, config_path=args.config)


if __name__ == "__main__":
    main()
