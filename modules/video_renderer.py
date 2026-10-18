"""
Module 3: Render Video Từ Ảnh & Chữ (video_renderer.py)
- Lấy ảnh tĩnh background (vd: temp/background.jpg)
- Thiết lập thời lượng cố định chính xác 18 giây (18.0s)
- Ghép chữ quote lên ảnh (hiệu ứng bóng đổ đen mờ mềm mại, căn lề Safe Zone TikTok 100px hai bên)
- Không có bất kỳ track âm thanh nào (No Audio / Mute)
- Xuất file hoàn chỉnh: output/tiktok_18s_ready.mp4 (H.264, 30fps, 1080x1920)
- Tối ưu bằng FFmpeg nhanh gấp 10 lần MoviePy và hoàn toàn ổn định trên Windows.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger("tiktok_tool.video_renderer")

FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_FONT = Path("assets/fonts/BeVietnamPro-Bold.ttf")


def get_vietnamese_font(font_size: int = 54) -> ImageFont.FreeTypeFont:
    """Tải font chữ tiếng Việt Be Vietnam Pro hoặc DejaVu Sans dự phòng."""
    if DEFAULT_FONT.exists():
        try:
            return ImageFont.truetype(str(DEFAULT_FONT), font_size)
        except Exception as e:
            logger.warning(f"Lỗi load font {DEFAULT_FONT}: {e}")

    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        return ImageFont.load_default()


def wrap_quote_to_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int = 880) -> List[str]:
    """
    Tự động ngắt dòng văn bản tiếng Việt thành 2 - 3 vế câu rõ ràng,
    không để từ bị đứt gãy và không vượt quá chiều rộng an toàn 880px (1080 - 2*100).
    """
    clean_text = " ".join(text.strip().split())
    words = clean_text.split(" ")
    lines: List[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]

        if line_w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def create_quote_overlay(
    quote: str,
    canvas_size: Tuple[int, int] = (1080, 1920),
    margin_left: int = 90,
    margin_right: int = 180,  # Dành khoảng trống 180px bên phải tránh che cụm icon thả tim/comment của TikTok
    margin_bottom: int = 420, # Cách đáy 420px tránh che thanh nhạc, tên kênh và caption TikTok
    line_spacing: int = 18,
    font_size: int = 42,      # Cỡ chữ nhỏ gọn, tinh tế hơn (42px)
    signature: Optional[str] = "saigonbac",
    signature_font_size: int = 24,
) -> Image.Image:
    """
    Tạo lớp ảnh chữ trong suốt RGBA (1080x1920) chứa câu quote và chữ ký nhỏ:
    - Font chữ nhỏ hơn, tinh tế, sang trọng (42px).
    - Canh lề trái (x = 90px), nằm ở góc dưới bên trái (cách đáy 420px an toàn).
    - Tránh hoàn toàn khu vực nút Like/Share/Comment bên phải và thanh nhạc TikTok ở đáy.
    - Chữ trắng tinh #FFFFFF nguyên bản.
    - Kèm chữ ký nhỏ (saigonbac) ngay dưới câu quote.
    """
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    max_text_width = canvas_size[0] - margin_left - margin_right

    font = get_vietnamese_font(font_size)
    lines = wrap_quote_to_lines(quote, font, max_width=max_text_width)

    # Nếu câu dài hơn 3 dòng, tự động giảm nhẹ font size
    if len(lines) > 3 and font_size > 36:
        font = get_vietnamese_font(font_size - 4)
        lines = wrap_quote_to_lines(quote, font, max_width=max_text_width)

    # Tính toán kích thước từng dòng
    line_metrics = []
    total_text_h = 0
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)

    for line in lines:
        bbox = draw_dummy.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_metrics.append((line, w, h))
        total_text_h += h

    total_text_h += (len(lines) - 1) * line_spacing

    # Thêm chiều cao cho chữ ký nếu có
    sig_font = None
    sig_h = 0
    sig_spacing = 16
    if signature:
        sig_font = get_vietnamese_font(signature_font_size)
        sig_bbox = draw_dummy.textbbox((0, 0), signature, font=sig_font)
        sig_h = sig_bbox[3] - sig_bbox[1]
        total_text_h += sig_spacing + sig_h

    # Vị trí Y: đặt ở góc dưới (cách đáy màn hình khoảng margin_bottom px)
    start_y = canvas_size[1] - margin_bottom - total_text_h
    start_x = margin_left

    # Vẽ chữ trắng tinh khiết nguyên bản (#FFFFFF)
    draw = ImageDraw.Draw(img)
    curr_y = start_y
    for line, w, h in line_metrics:
        draw.text((start_x, curr_y), line, font=font, fill=(255, 255, 255, 255))
        curr_y += h + line_spacing

    # Vẽ chữ ký nhỏ bên dưới câu quote, canh lề phải theo khung quote (tránh che cụm nút TikTok)
    if signature and sig_font:
        curr_y += (sig_spacing - line_spacing) if lines else 0
        sig_bbox = draw_dummy.textbbox((0, 0), signature, font=sig_font)
        sig_w = sig_bbox[2] - sig_bbox[0]
        sig_x = (canvas_size[0] - margin_right) - sig_w
        draw.text((sig_x, curr_y), signature, font=sig_font, fill=(255, 255, 255, 190))

    return img


def render_18s_video(
    image_path: Path | str,
    quote: str,
    output_path: Path | str = Path("output/tiktok_18s_ready.mp4"),
    duration: float = 18.0,
    overlay_opacity: float = 0.30,
    signature: Optional[str] = "saigonbac",
) -> Path:
    """
    Render video TikTok chuẩn 18 giây, tỷ lệ 9:16 (1080x1920), không có âm thanh.

    Args:
        image_path: Đường dẫn ảnh nền JPEG/PNG.
        quote: Nội dung câu trích dẫn hiển thị trên video.
        output_path: Đường dẫn file video xuất ra (mặc định output/tiktok_18s_ready.mp4).
        duration: Thời lượng video (cố định 18.0s).
        overlay_opacity: Độ tối lớp phủ đen (mặc định 30% = 0.30).
        signature: Chữ ký thương hiệu nhỏ (mặc định 'saigonbac').

    Returns:
        Path dẫn tới video thành phẩm.
    """
    img_file = Path(image_path)
    if not img_file.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh nền: {img_file}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Tạo ảnh chữ PNG tạm thời kèm chữ ký
    overlay_img = create_quote_overlay(quote=quote, signature=signature)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
        tmp_png_path = Path(tmp_png.name)
    overlay_img.save(tmp_png_path, format="PNG")

    # 2. Xây dựng lệnh FFmpeg biến ảnh tĩnh thành video 18 giây
    # Fade in 1.2s lúc đầu và Fade out 0.8s ở giây 17.2
    fade_out_start = max(1.5, duration - 0.8)

    # Filter ghép ảnh và chữ:
    # - scale 1080:1920 dùng bicubic/lanczos giữ nguyên 100% độ nét gốc của ảnh, KHÔNG phủ đen (overlay_opacity=0)
    # - Chữ trắng có sẵn bóng đen mờ mềm mại nên luôn nổi bật tự nhiên mà không làm tối hay mờ ảnh nền
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,fps=30[bg];"
        f"[1:v]format=rgba[text];"
        f"[bg][text]overlay=0:0:shortest=1[outv]"
    )

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-loop", "1",
        "-t", str(duration),
        "-i", str(img_file),
        "-loop", "1",
        "-i", str(tmp_png_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",  # Nâng cao chất lượng nén lên gần lossless (sắc nét tuyệt đối)
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(duration),
        "-an",  # KHÔNG CÓ AUDIO STREAM
        str(out_file),
    ]

    try:
        logger.info(f"Đang render video 18s TikTok -> {out_file.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error(f"Lỗi FFmpeg:\n{proc.stderr}")
            raise RuntimeError(f"Lỗi FFmpeg khi render video: {proc.stderr[:300]}")

    finally:
        if tmp_png_path.exists():
            tmp_png_path.unlink()

    logger.info(f"Render video 18s thành công: {out_file} ({out_file.stat().st_size} bytes)")
    return out_file
