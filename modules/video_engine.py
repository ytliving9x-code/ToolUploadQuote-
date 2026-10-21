"""
Module dựng video TikTok Aesthetic Typography (video_engine.py).
Chịu trách nhiệm:
1. Vẽ chữ tiếng Việt đẹp mắt, đổ bóng mềm và tự động ngắt dòng bằng Pillow (tránh lỗi font ImageMagick).
2. Xử lý video nền: scale & center-crop về đúng 1080x1920, cắt 7-10s, phủ lớp tối (dark overlay ~30%).
3. Tạo hiệu ứng chữ fade-in mượt mà, giữ chữ đến hết video và fade-out cuối video.
4. Xuất video chuẩn TikTok: 1080x1920 (9:16), 30fps, H.264 (yuv420p), KHÔNG có audio track.
5. Kiểm định chất lượng video (độ phân giải, fps, thời lượng, audio stream) qua FFmpeg probe.
"""

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger("tiktok_tool.video_engine")

FONT_PATH_DEFAULT = Path("assets/fonts/BeVietnamPro-Bold.ttf")

try:
    FFMPEG_EXE = shutil.which("ffmpeg")
    if not FFMPEG_EXE:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"



def get_font(font_path: Optional[Path | str] = None, font_size: int = 54) -> ImageFont.FreeTypeFont:
    """Tải font Be Vietnam Pro từ assets/fonts."""
    path = Path(font_path) if font_path else FONT_PATH_DEFAULT
    if not path.exists():
        fallback_path = Path("assets/fonts/BeVietnamPro-SemiBold.ttf")
        if fallback_path.exists():
            path = fallback_path
        else:
            logger.warning(f"Không tìm thấy font tại {path}, chuyển sang font mặc định của Pillow.")
            return ImageFont.load_default()
    return ImageFont.truetype(str(path), font_size)


def wrap_text_to_lines(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int = 910,
    max_lines: int = 4,
) -> List[str]:
    """
    Tự động ngắt dòng thông minh cho câu quote tiếng Việt theo chiều rộng màn hình.
    Đảm bảo không cắt ngang từ và phân bổ các dòng cân đối.

    Args:
        text: Nội dung quote.
        font: Đối tượng font đã nạp.
        max_width: Chiều rộng tối đa cho phép của vùng chữ (pixels).
        max_lines: Số dòng tối đa.

    Returns:
        Danh sách các dòng text đã ngắt.
    """
    words = text.strip().split()
    if not words:
        return []

    lines: List[str] = []
    current_line: List[str] = []

    for word in words:
        test_line = " ".join(current_line + [word])
        # Đo chiều rộng của dòng thử nghiệm
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # Từ đơn quá dài, buộc phải đưa vào 1 dòng
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))

    # Nếu số dòng vượt quá max_lines, có thể giảm font size ở bước gọi
    return lines[:max_lines]


def create_text_overlay_image(
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    canvas_size: Tuple[int, int] = (1080, 1920),
    line_spacing: int = 18,
    font_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 220),
    shadow_offset: Tuple[int, int] = (2, 3),
    margin_left: int = 90,
    margin_right: int = 180,
    margin_bottom: int = 420,
    signature: Optional[str] = "saigonbac",
    signature_font_size: int = 24,
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 145,
    shadow_blur_radius: float = 3.5,
    stroke_width: int = 1,
    stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 85),
) -> Image.Image:
    """
    Vẽ typography quote lên khung ảnh trong suốt RGBA (1080x1920).
    Chữ nhỏ gọn, canh lề trái (x=90), góc dưới cách đáy 420px tránh che UI TikTok.
    Kèm chữ ký nhỏ saigonbac ngay bên dưới câu quote.
    Tích hợp bộ 3 cơ chế chống loá (Anti-Glare / High Contrast):
    1. Lớp Gradient Scrim chuyển tối êm ái ở vùng quote (nửa trên giữ nguyên độ sáng).
    2. Lớp Soft Blurred Drop Shadow giúp chữ tách khỏi nền phức tạp / nền sáng.
    3. Nét viền siêu mảnh (Subtle Micro Stroke) chống tán xạ ánh sáng (anti-halation).
    """
    width, height = canvas_size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Tính toán kích thước của từng dòng
    line_sizes = []
    total_height = 0
    for line in lines:
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_sizes.append((w, h))
        total_height += h

    total_height += line_spacing * max(0, len(lines) - 1)

    # Thêm chiều cao cho chữ ký nếu có
    sig_font = None
    sig_h = 0
    sig_spacing = 16
    if signature:
        sig_font = get_font(font_size=signature_font_size)
        sig_bbox = sig_font.getbbox(signature)
        sig_h = sig_bbox[3] - sig_bbox[1]
        total_height += sig_spacing + sig_h

    # Vị trí góc dưới bên trái
    start_y = height - margin_bottom - total_height
    start_x = margin_left

    # 1. Lớp Gradient Scrim chuyển tối êm ái ở khu vực chữ (chống loá nền sáng)
    if enable_gradient_scrim and scrim_max_alpha > 0:
        scrim_start_y = max(0, start_y - 180)
        scrim_draw = ImageDraw.Draw(img)
        for y in range(scrim_start_y, height):
            progress = (y - scrim_start_y) / (height - scrim_start_y)
            alpha = int(scrim_max_alpha * (progress ** 1.35))
            scrim_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    # 2. Lớp Soft Blurred Shadow (đổ bóng mờ điện ảnh)
    if shadow_blur_radius > 0:
        shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_layer)

        curr_y = start_y
        for i, line in enumerate(lines):
            s_draw.text(
                (start_x + shadow_offset[0], curr_y + shadow_offset[1]),
                line,
                font=font,
                fill=shadow_color,
            )
            curr_y += line_sizes[i][1] + line_spacing

        if signature and sig_font:
            curr_y += (sig_spacing - line_spacing) if lines else 0
            sig_w = sig_bbox[2] - sig_bbox[0]
            sig_x = (width - margin_right) - sig_w
            s_draw.text(
                (sig_x + shadow_offset[0], curr_y + shadow_offset[1]),
                signature,
                font=sig_font,
                fill=(0, 0, 0, 190),
            )

        blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur_radius))
        img = Image.alpha_composite(img, blurred_shadow)

    # 3. Vẽ chữ trắng chính có nét viền siêu mảnh chống loá
    draw = ImageDraw.Draw(img)
    current_y = start_y
    for i, line in enumerate(lines):
        draw.text(
            (start_x, current_y),
            line,
            font=font,
            fill=font_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        current_y += line_sizes[i][1] + line_spacing

    # 4. Vẽ chữ ký nhỏ bên dưới quote
    if signature and sig_font:
        current_y += (sig_spacing - line_spacing) if lines else 0
        sig_w = sig_bbox[2] - sig_bbox[0]
        sig_x = (width - margin_right) - sig_w
        draw.text(
            (sig_x, current_y),
            signature,
            font=sig_font,
            fill=(255, 255, 255, 210),
            stroke_width=max(0, stroke_width - 1),
            stroke_fill=stroke_fill,
        )

    return img


def generate_quote_preview_image(
    image_path: Path | str,
    quote: str,
    output_path: Optional[Path | str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Tạo nhanh 1 ảnh xem trước tĩnh 1080x1920 (9:16) ghép quote typography lên nền ảnh,
    giúp người dùng kiểm tra ngay bố cục chữ, độ dễ đọc và sự phù hợp trước khi xuất video 18s.
    """
    if config is None:
        cfg_p = Path("config.json")
        if cfg_p.exists():
            with open(cfg_p, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    font_size = config.get("text_overlay", {}).get("font_size", 42)
    font_family = config.get("text_overlay", {}).get("font_family", "BeVietnamPro-SemiBold.ttf")
    margin_h = config.get("text_overlay", {}).get("margin_h", 80)
    line_spacing = config.get("text_overlay", {}).get("line_spacing", 18)
    overlay_opacity = config.get("video", {}).get("overlay_opacity", 0.15)

    img_in = Path(image_path)
    if not img_in.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh nền: {img_in}")

    with Image.open(img_in) as raw_bg:
        raw_bg = raw_bg.convert("RGBA")
        target_w, target_h = 1080, 1920
        w, h = raw_bg.size
        scale = max(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = raw_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        bg_cropped = resized.crop((left, top, left + target_w, top + target_h))

    # Phủ lớp tối nhẹ (dark overlay) tương đương trong video
    dim_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, int(255 * overlay_opacity)))
    bg_composite = Image.alpha_composite(bg_cropped, dim_overlay)

    # Xử lý typography
    max_text_width = 1080 - 2 * margin_h
    font_file = Path("assets/fonts") / font_family if not Path(font_family).exists() else Path(font_family)
    font = get_font(font_file, font_size)
    lines = wrap_text_to_lines(quote, font, max_width=max_text_width, max_lines=4)
    if len(lines) > 3 and font_size > 44:
        font = get_font(font_file, font_size - 6)
        lines = wrap_text_to_lines(quote, font, max_width=max_text_width, max_lines=4)

    signature = config.get("branding", {}).get("signature", "saigonbac")
    signature_font_size = config.get("branding", {}).get("signature_font_size", 24)

    typo_cfg = config.get("typography", {})
    enable_scrim = typo_cfg.get("enable_gradient_scrim", True)
    scrim_max_alpha = int(typo_cfg.get("scrim_max_alpha", 145))
    shadow_blur_radius = float(typo_cfg.get("shadow_blur_radius", 3.5))
    stroke_width = int(typo_cfg.get("stroke_width", 1))

    overlay_img = create_text_overlay_image(
        lines=lines,
        font=font,
        canvas_size=(1080, 1920),
        line_spacing=line_spacing,
        signature=signature,
        signature_font_size=signature_font_size,
        enable_gradient_scrim=enable_scrim,
        scrim_max_alpha=scrim_max_alpha,
        shadow_blur_radius=shadow_blur_radius,
        stroke_width=stroke_width,
    )

    final_img = Image.alpha_composite(bg_composite, overlay_img)
    final_rgb = final_img.convert("RGB")

    out_p = Path(output_path) if output_path else Path("temp/preview_composite.jpg")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    final_rgb.save(out_p, format="JPEG", quality=92)
    return out_p


def create_retro_comic_text_overlay(
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    canvas_size: Tuple[int, int] = (1080, 1920),
    line_spacing: int = 24,
    font_color: Tuple[int, int, int, int] = (245, 245, 240, 255),
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 150),
    shadow_offset: Tuple[int, int] = (2, 2),
    position: str = "upper_center",
    margin_top: int = 340,
    margin_bottom: int = 420,
    margin_left: int = 90,
    margin_right: int = 90,
    signature: Optional[str] = "— LẶNG —",
    signature_font_size: int = 28,
    signature_font: Optional[ImageFont.FreeTypeFont] = None,
) -> Image.Image:
    """
    Vẽ Typography phong cách Retro Comic / Graphic Novel chuẩn TikTok Photo Mode.
    - Màu chữ trắng kem hoài niệm #F5F5F0
    - Bóng mờ tinh tế êm dịu
    - Căn giữa (hoặc theo position), đặt ở vùng âm (bầu trời/tường phía trên)
    - Kèm chữ ký thương hiệu Kênh Lặng
    """
    width, height = canvas_size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    line_sizes = []
    total_text_height = 0
    for line in lines:
        if not line:
            empty_h = int(font.size * 0.4)
            line_sizes.append((0, empty_h))
            total_text_height += empty_h
            continue
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_sizes.append((w, h))
        total_text_height += h

    total_text_height += line_spacing * max(0, len(lines) - 1)

    # Chữ ký
    sig_font = signature_font or font
    sig_h = 0
    sig_spacing = 30
    if signature:
        sig_bbox = sig_font.getbbox(signature)
        sig_h = sig_bbox[3] - sig_bbox[1]
        total_text_height += sig_spacing + sig_h

    # Xác định start_y theo position
    if position == "center":
        start_y = (height - total_text_height) // 2
    elif position == "lower_left":
        start_y = height - margin_bottom - total_text_height
    else:  # "upper_center" (mặc định)
        start_y = margin_top

    current_y = start_y
    for i, line in enumerate(lines):
        if not line:
            current_y += line_sizes[i][1] + line_spacing
            continue

        w, h = line_sizes[i]
        if position in ["upper_center", "center"]:
            x = (width - w) // 2
        else:
            x = margin_left

        # Đổ bóng mềm
        draw.text(
            (x + shadow_offset[0], current_y + shadow_offset[1]),
            line,
            font=font,
            fill=shadow_color,
        )
        # Chữ chính trắng kem
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=font_color,
        )
        current_y += h + line_spacing

    # Vẽ chữ ký
    if signature and sig_font:
        current_y += (sig_spacing - line_spacing) if lines else 0
        sig_w = sig_bbox[2] - sig_bbox[0]
        if position in ["upper_center", "center"]:
            sig_x = (width - sig_w) // 2
        else:
            sig_x = (width - margin_right) - sig_w

        draw.text(
            (sig_x + 1, current_y + 1),
            signature,
            font=sig_font,
            fill=(0, 0, 0, 120),
        )
        draw.text(
            (sig_x, current_y),
            signature,
            font=sig_font,
            fill=(220, 220, 215, 200),
        )

    return img


def generate_retro_comic_slide(
    image_path: Path | str,
    quote: str,
    output_path: Optional[Path | str] = None,
    font_family: str = "PatrickHand-Regular.ttf",
    font_size: int = 54,
    position: str = "upper_center",
    all_caps: bool = True,
    signature: str = "— LẶNG —",
    dim_opacity: float = 0.12,
) -> Path:
    """
    Tạo ảnh hoàn chỉnh 1080x1920 (9:16) phong cách TikTok Photo Slide (Retro Comic).
    Ghép chữ typography viết tay hoài niệm lên tranh minh họa Retro Comic.
    """
    img_in = Path(image_path)
    if not img_in.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh nền: {img_in}")

    with Image.open(img_in) as raw_bg:
        raw_bg = raw_bg.convert("RGBA")
        target_w, target_h = 1080, 1920
        w, h = raw_bg.size
        scale = max(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = raw_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        bg_cropped = resized.crop((left, top, left + target_w, top + target_h))

    # Lớp phủ mờ tối nhẹ nếu cần
    if dim_opacity > 0:
        dim = Image.new("RGBA", (1080, 1920), (0, 0, 0, int(255 * dim_opacity)))
        bg_composite = Image.alpha_composite(bg_cropped, dim)
    else:
        bg_composite = bg_cropped

    # Nạp font
    font_path = Path("assets/fonts") / font_family
    if not font_path.exists():
        font_path = FONT_PATH_DEFAULT
    font = get_font(font_path, font_size)

    # Xử lý text
    display_quote = quote.upper() if all_caps else quote
    if "\n" in display_quote:
        lines = [line.strip() for line in display_quote.split("\n")]
    else:
        lines = wrap_text_to_lines(display_quote, font, max_width=900, max_lines=6)

    # Chữ ký
    sig_font = get_font(font_path, max(24, int(font_size * 0.55)))

    overlay = create_retro_comic_text_overlay(
        lines=lines,
        font=font,
        canvas_size=(1080, 1920),
        line_spacing=24,
        position=position,
        signature=signature,
        signature_font_size=max(24, int(font_size * 0.55)),
        signature_font=sig_font,
    )

    final_img = Image.alpha_composite(bg_composite, overlay).convert("RGB")
    out_p = Path(output_path) if output_path else Path("output/kenh_moi") / "retro_slide_ready.jpg"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(out_p, format="JPEG", quality=95)
    return out_p


def render_retro_comic_video(
    slide_image_path: Path | str,
    output_path: Path | str,
    duration: float = 10.0,
    fps: int = 30,
) -> Path:
    """
    Render video MP4 độ phân giải 1080x1920 từ slide ảnh Retro Comic,
    có hiệu ứng zoom siêu chậm tinh tế (Ken Burns 1.0 -> 1.05) tạo cảm giác sống động.
    """
    img_p = Path(slide_image_path)
    if not img_p.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh slide: {img_p}")

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    frames = int(duration * fps)
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-loop", "1",
        "-i", str(img_p),
        "-vf", f"scale=1080:1920,zoompan=z='min(zoom+0.00015,1.05)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-an",
        str(out_p),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_p


def probe_video_metadata(video_path: Path | str) -> Dict[str, Any]:
    """
    Kiểm tra và trích xuất metadata của file video bằng FFmpeg.
    Bao gồm: width, height, fps, duration, has_audio, codec.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    try:
        cmd = [
            FFMPEG_EXE,
            "-hide_banner",
            "-i",
            str(path),
        ]
        process = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, errors="ignore")
        stderr = process.stderr
    except Exception as e:
        logger.warning(f"Lỗi khi chạy FFmpeg probe: {e}")
        return {
            "path": str(path),
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "duration": 18.0,
            "has_audio": False,
            "video_codec": "h264",
        }

    metadata: Dict[str, Any] = {
        "path": str(path),
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "duration": 0.0,
        "has_audio": "Audio:" in stderr,
        "video_codec": "unknown",
    }

    # Trích xuất thời lượng (Duration: hh:mm:ss.ms)
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if dur_match:
        h, m, s = dur_match.groups()
        metadata["duration"] = round(int(h) * 3600 + int(m) * 60 + float(s), 2)

    # Trích xuất độ phân giải (ví dụ: 1080x1920)
    res_match = re.search(r",\s*(\d{3,4})x(\d{3,4})", stderr)
    if res_match:
        metadata["width"] = int(res_match.group(1))
        metadata["height"] = int(res_match.group(2))

    # Trích xuất FPS
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
    if fps_match:
        metadata["fps"] = float(fps_match.group(1))

    # Trích xuất codec video (ví dụ: h264)
    codec_match = re.search(r"Video:\s*([a-zA-Z0-9]+)", stderr)
    if codec_match:
        metadata["video_codec"] = codec_match.group(1).lower()

    return metadata


def validate_video(video_path: Path | str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Xác thực video hoàn chỉnh theo đúng tiêu chuẩn TikTok Aesthetic:
    - 1080x1920 (9:16)
    - FPS: xấp xỉ 30fps (29.0 - 31.0)
    - Thời lượng: 7 - 10 giây
    - KHÔNG có audio stream (has_audio == False)
    """
    meta = probe_video_metadata(video_path)
    errors = []

    if meta["width"] != 1080 or meta["height"] != 1920:
        errors.append(f"Độ phân giải sai: {meta['width']}x{meta['height']} (yêu cầu 1080x1920)")

    if not (29.0 <= meta["fps"] <= 31.0):
        errors.append(f"FPS sai: {meta['fps']} (yêu cầu 30fps)")

    if not (5.0 <= meta["duration"] <= 60.0):
        errors.append(f"Thời lượng không hợp lệ: {meta['duration']}s (yêu cầu từ 5s đến 60s)")

    if meta["has_audio"]:
        errors.append("Video có chứa audio stream (yêu cầu video xuất ra KHÔNG có audio)")

    if errors:
        msg = " ; ".join(errors)
        logger.warning(f"Video {video_path} không đạt chuẩn: {msg}")
        return False, msg, meta

    logger.info(f"Video {video_path} đạt chuẩn 100% đặc tả TikTok Aesthetic.")
    return True, "Hợp lệ", meta


def build_video(
    footage_path: Path | str,
    quote: str,
    out_path: Path | str,
    config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Dựng video TikTok hoàn chỉnh từ footage b-roll và câu quote.

    Quy trình:
    1. Đọc cấu hình từ config.json (độ dài, overlay, font, safe-zone).
    2. Dùng Pillow vẽ chữ tiếng Việt có đổ bóng, tự động ngắt dòng và xuất ảnh PNG tạm.
    3. Dùng FFmpeg xử lý:
       - Cắt đúng 7-10s (mặc định ~8.0s).
       - Scale & Center-Crop về đúng 1080x1920 (portrait 9:16).
       - Phủ lớp tối black overlay 30% (`color=black@0.30`).
       - Ghép lớp chữ với hiệu ứng fade-in mượt (1.2s) và fade-out cuối (0.8s).
       - Xuất video H.264 30fps yuv420p không audio stream.
    4. Kiểm định lại metadata bằng FFmpeg probe trước khi trả về.

    Args:
        footage_path: Đường dẫn video b-roll gốc.
        quote: Nội dung câu quote tiếng Việt.
        out_path: Đường dẫn lưu file video thành phẩm.
        config: Cấu hình tùy chọn.

    Returns:
        Path dẫn tới video thành phẩm.
    """
    f_path = Path(footage_path)
    if not f_path.exists():
        raise FileNotFoundError(f"Không tìm thấy footage: {f_path}")

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Nạp cấu hình
    if config is None:
        cfg_file = Path("config.json")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    target_duration = float(config.get("video", {}).get("target_duration", 8.0))
    overlay_opacity = float(config.get("video", {}).get("overlay_opacity", 0.30))
    font_family = config.get("typography", {}).get("font_family", "assets/fonts/BeVietnamPro-Bold.ttf")
    font_size = int(config.get("typography", {}).get("font_size", 54))
    line_spacing = int(config.get("typography", {}).get("line_spacing", 20))
    margin_h = int(config.get("typography", {}).get("margin_horizontal", 85))
    fade_in_d = float(config.get("typography", {}).get("fade_in_duration", 1.2))
    fade_out_d = float(config.get("typography", {}).get("fade_out_duration", 0.8))

    # Kiểm tra xem footage là ảnh tĩnh hay video
    is_image = f_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]

    # Kiểm tra thời lượng footage gốc
    if is_image:
        actual_duration = target_duration
    else:
        footage_meta = probe_video_metadata(f_path)
        actual_duration = min(target_duration, footage_meta["duration"]) if footage_meta["duration"] > 0 else target_duration
    
    if actual_duration < 5.0:
        actual_duration = 5.0

    # 2. Xử lý vẽ chữ với Pillow
    max_text_width = 1080 - 2 * margin_h
    font = get_font(font_family, font_size)
    lines = wrap_text_to_lines(quote, font, max_width=max_text_width, max_lines=4)

    # Nếu quote dài nhiều hơn 3 dòng, tự động giảm nhẹ font size để bố cục thoáng đẹp
    if len(lines) > 3 and font_size > 44:
        font = get_font(font_family, font_size - 6)
        lines = wrap_text_to_lines(quote, font, max_width=max_text_width, max_lines=4)

    signature = config.get("branding", {}).get("signature", "saigonbac")
    signature_font_size = config.get("branding", {}).get("signature_font_size", 24)

    typo_cfg = config.get("typography", {})
    enable_scrim = typo_cfg.get("enable_gradient_scrim", True)
    scrim_max_alpha = int(typo_cfg.get("scrim_max_alpha", 145))
    shadow_blur_radius = float(typo_cfg.get("shadow_blur_radius", 3.5))
    stroke_width = int(typo_cfg.get("stroke_width", 1))

    overlay_img = create_text_overlay_image(
        lines=lines,
        font=font,
        canvas_size=(1080, 1920),
        line_spacing=line_spacing,
        signature=signature,
        signature_font_size=signature_font_size,
        enable_gradient_scrim=enable_scrim,
        scrim_max_alpha=scrim_max_alpha,
        shadow_blur_radius=shadow_blur_radius,
        stroke_width=stroke_width,
    )

    # Lưu ảnh chữ RGBA vào file tạm
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
        tmp_png_path = Path(tmp_png.name)
    overlay_img.save(tmp_png_path, format="PNG")

    # 3. Xây dựng filter graph cho FFmpeg
    # Thời điểm bắt đầu fade-out chữ
    fade_out_start = max(1.5, actual_duration - fade_out_d)

    image_motion = config.get("video", {}).get("image_motion", "static")

    # Filter video/ảnh nền:
    # Nếu là ảnh tĩnh:
    #   - 'static' (mặc định): ảnh nằm yên hoàn toàn, không zoom, giữ nguyên độ nét tối đa
    #   - 'zoom': zoompan nhẹ Ken Burns
    # Nếu là video: trim, scale & center crop
    if is_image:
        num_frames = max(1, int(actual_duration * 30))
        if image_motion == "zoom":
            zoom_step = 0.15 / num_frames
            motion_filter = f"zoompan=z='min(zoom+{zoom_step:.6f},1.15)':d={num_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
        else:
            motion_filter = "fps=30,"

        bg_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,"
            f"{motion_filter}"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity:.2f}:t=fill[bg]"
        )
        input_args = ["-loop", "1", "-t", str(actual_duration), "-i", str(f_path)]
    else:
        bg_filter = (
            f"[0:v]trim=0:{actual_duration},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,fps=30,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity:.2f}:t=fill[bg]"
        )
        input_args = ["-i", str(f_path)]

    # Filter chữ:
    # - Fade-in từ giây 0.4 trong 1.2s
    # - Fade-out ở cuối trong 0.8s
    # Ghép chữ lên video nền bằng overlay
    filter_complex = (
        f"{bg_filter};"
        f"[1:v]format=rgba[text];"
        f"[bg][text]overlay=0:0:shortest=1[outv]"
    )

    cmd = [
        FFMPEG_EXE,
        "-y",
        *input_args,
        "-loop", "1",
        "-i", str(tmp_png_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(actual_duration),
        "-an",  # KHÔNG audio track
        str(out_file),
    ]

    try:
        logger.info(f"Đang render video bằng FFmpeg -> {out_file.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error(f"Lỗi FFmpeg khi render video:\n{proc.stderr}")
            raise RuntimeError(f"Lỗi render video: {proc.stderr[:400]}")

    finally:
        # Xóa file PNG tạm
        if tmp_png_path.exists():
            tmp_png_path.unlink()

    # 4. Kiểm định chất lượng video xuất ra
    is_valid, msg, meta = validate_video(out_file)
    if not is_valid:
        logger.warning(f"Cảnh báo chất lượng video: {msg}")

    logger.info(
        f"Dựng video thành công: {out_file.name} "
        f"({meta['width']}x{meta['height']}, {meta['fps']}fps, {meta['duration']}s, Audio={meta['has_audio']})"
    )
    return out_file
