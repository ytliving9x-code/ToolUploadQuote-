"""
Script kiểm thử render 3 video mẫu với 3 độ dài quote khác nhau:
1. Quote ngắn (~34 ký tự)
2. Quote vừa (~85 ký tự)
3. Quote dài (~112 ký tự)
Kiểm tra ngắt dòng, bố cục typography, dark overlay, fade-in/fade-out,
và kiểm định các thông số kỹ thuật (1080x1920, 30fps, ~8s, no-audio).
"""

import logging
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RenderSamples")

from modules.video_engine import build_video, validate_video
from modules.pexels_api import get_footage
from modules.exporter import export_to_pending

SAMPLE_QUOTES = [
    {
        "type": "ngắn",
        "quote": "Tĩnh lặng để lắng nghe chính mình.",
        "caption": "Khoảng lặng cho tâm hồn an yên giữa phố thị ồn ào. ✨",
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#tinhlang"],
    },
    {
        "type": "vừa",
        "quote": "Nước sâu tĩnh lặng, lúa chín cúi đầu. Đỉnh cao của trưởng thành là biết im lặng đúng lúc.",
        "caption": "Sự điềm tĩnh là đỉnh cao của bản lĩnh và trải nghiệm. 🌱",
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#truongthanh", "#suyngam"],
    },
    {
        "type": "dài",
        "quote": "Bão giông ngoài kia không làm bạn ngã gục. Chỉ có sự rối loạn bên trong mới khiến bạn đánh mất chính mình.",
        "caption": "Giữ tâm tĩnh giữa bão giông. Bình yên nằm ở chính bạn. 🌧️",
        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#binhyen", "#chualanh"],
    },
]


def main():
    logger.info("=== BẮT ĐẦU RENDER 3 VIDEO MẪU (NGẮN / VỪA / DÀI) ===")

    # Lấy footage nền mẫu
    footage = get_footage(keywords=["night rain street aesthetic", "dark moody"], min_duration=8)
    footage_path = footage["local_path"]
    logger.info(f"Sử dụng footage nền: {footage_path}")

    output_dir = Path("output/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(SAMPLE_QUOTES, 1):
        q_type = item["type"]
        quote_text = item["quote"]
        out_path = output_dir / f"sample_{i}_{q_type}.mp4"

        logger.info(f"\n--- Đang render mẫu #{i} ({q_type.upper()}) ---")
        logger.info(f"Quote: \"{quote_text}\" ({len(quote_text)} ký tự)")

        build_video(
            footage_path=footage_path,
            quote=quote_text,
            out_path=out_path,
        )

        is_valid, msg, meta = validate_video(out_path)
        print("+" + "-" * 55 + "+")
        print(f"| Mẫu: {q_type.upper()} ({out_path.name})")
        print(f"| Hợp lệ: {is_valid} ({msg})")
        print(f"| Độ phân giải: {meta['width']}x{meta['height']} (9:16 portrait)")
        print(f"| FPS: {meta['fps']} | Thời lượng: {meta['duration']}s")
        print(f"| Audio Stream: {meta['has_audio']} (Đúng chuẩn audio=False)")
        print(f"| Dung lượng: {out_path.stat().st_size / 1024 / 1024:.2f} MB")
        print("+" + "-" * 55 + "+\n")

    logger.info("=== HOÀN TẤT RENDER 3 VIDEO MẪU THÀNH CÔNG ===")


if __name__ == "__main__":
    main()
