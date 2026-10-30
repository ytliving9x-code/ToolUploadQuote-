"""
Module 3: Render Video Từ Ảnh & Chữ (video_renderer.py)
- Lấy ảnh tĩnh background (vd: temp/background.jpg)
- Thiết lập thời lượng cố định chính xác 18 giây (18.0s)
- Ghép chữ quote lên ảnh (hiệu ứng bóng đổ đen mờ mềm mại, căn lề Safe Zone TikTok 100px hai bên)
- Không có bất kỳ track âm thanh nào (No Audio / Mute)
- Xuất file hoàn chỉnh: output/tiktok_18s_ready.mp4 (H.264, 30fps, 1080x1920)
- Tối ưu bằng FFmpeg nhanh gấp 10 lần MoviePy và hoàn toàn ổn định trên Windows.
"""

import gc
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

try:
    FFMPEG_EXE = shutil.which("ffmpeg")
    if not FFMPEG_EXE:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_FONT = Path("assets/fonts/BeVietnamPro-Bold.ttf")


def extract_video_frame(video_path: Path | str, timestamp_sec: float = 1.0) -> Path:
    """
    Trích xuất 1 khung hình (1080x1920) từ video footage làm ảnh xem trước.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {v_path}")

    out_dir = Path("temp")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_frame = out_dir / f"frame_{v_path.stem}_{int(timestamp_sec * 10)}.jpg"

    cmd = [
        FFMPEG_EXE, "-y",
        "-ss", str(timestamp_sec),
        "-i", str(v_path),
        "-vframes", "1",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2",
        "-q:v", "2",
        str(out_frame),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not out_frame.exists():
        logger.error(f"Lỗi trích xuất frame từ video {v_path}: {proc.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError(f"Không thể trích xuất khung hình từ video: {v_path.name}")
    return out_frame


def determine_media_duration(media_path: Path | str) -> float:
    """
    Quy tắc thời lượng video/ảnh:
    - Nếu là hình ảnh (jpg, png, webp, ...): Cố định 10.0 giây
    - Nếu là video (mp4, mov, webm, avi, mkv):
        + Lớn hơn 20 giây (> 20.0s): Tự động cắt về đúng 20.0s
        + Nhỏ hơn hoặc bằng 20 giây (<= 20.0s): Giữ nguyên thời lượng gốc (round 2 chữ số)
        + Fallback khi không probe được: 10.0s
    """
    p = Path(media_path)
    if not p.exists():
        return 10.0

    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    if p.suffix.lower() in video_exts:
        from modules.video_engine import probe_video_metadata
        try:
            meta = probe_video_metadata(p)
            orig_dur = float(meta.get("duration", 0.0))
            if orig_dur > 20.0:
                return 20.0
            elif orig_dur > 0:
                return round(orig_dur, 2)
            return 10.0
        except Exception as e:
            logger.warning(f"Lỗi probe metadata cho {p}: {e}")
            return 10.0
    return 10.0


def get_media_duration_info(media_path: Path | str) -> Dict[str, Any]:
    """
    Trả về thông tin chi tiết về loại media, thời lượng gốc, thời lượng mục tiêu
    và nhãn hiển thị trực quan cho giao diện người dùng.
    """
    p = Path(media_path)
    if not p.exists():
        return {
            "is_video": False,
            "orig_duration": 10.0,
            "target_duration": 10.0,
            "action": "image_fixed",
            "badge_text": "📸 Ảnh nền: 10.0s (Hiệu ứng Ken Burns drift)",
            "btn_suffix": "(10.0S)",
        }

    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    if p.suffix.lower() in video_exts:
        from modules.video_engine import probe_video_metadata
        try:
            meta = probe_video_metadata(p)
            orig_dur = float(meta.get("duration", 0.0))
            if orig_dur > 20.0:
                return {
                    "is_video": True,
                    "orig_duration": orig_dur,
                    "target_duration": 20.0,
                    "action": "video_trimmed",
                    "badge_text": f"🎬 Video nền: Dài {orig_dur:.1f}s ➔ Tự động cắt về 20.0s",
                    "btn_suffix": f"(20.0S - ĐÃ CẮT TỪ {orig_dur:.1f}S)",
                }
            elif orig_dur > 0:
                target = round(orig_dur, 2)
                return {
                    "is_video": True,
                    "orig_duration": orig_dur,
                    "target_duration": target,
                    "action": "video_kept",
                    "badge_text": f"🎬 Video nền: Dài {orig_dur:.1f}s ➔ Giữ nguyên {orig_dur:.1f}s",
                    "btn_suffix": f"({orig_dur:.1f}S - THEO VIDEO GỐC)",
                }
            else:
                return {
                    "is_video": True,
                    "orig_duration": 10.0,
                    "target_duration": 10.0,
                    "action": "video_fallback",
                    "badge_text": "🎬 Video nền: 10.0s (Mặc định)",
                    "btn_suffix": "(10.0S)",
                }
        except Exception:
            return {
                "is_video": True,
                "orig_duration": 10.0,
                "target_duration": 10.0,
                "action": "video_fallback",
                "badge_text": "🎬 Video nền: 10.0s (Mặc định)",
                "btn_suffix": "(10.0S)",
            }
    return {
        "is_video": False,
        "orig_duration": 10.0,
        "target_duration": 10.0,
        "action": "image_fixed",
        "badge_text": "📸 Ảnh nền: 10.0s (Hiệu ứng Ken Burns drift)",
        "btn_suffix": "(10.0S)",
    }


def get_vietnamese_font(font_size: int = 54, font_path: Optional[Path | str] = None) -> ImageFont.FreeTypeFont:
    """Tải font chữ tiếng Việt theo font_path hoặc Be Vietnam Pro / Montserrat dự phòng."""
    target = Path(font_path) if font_path else DEFAULT_FONT
    if target.exists():
        try:
            return ImageFont.truetype(str(target), font_size)
        except Exception as e:
            logger.warning(f"Lỗi load font {target}: {e}")

    if DEFAULT_FONT.exists():
        try:
            return ImageFont.truetype(str(DEFAULT_FONT), font_size)
        except Exception:
            pass

    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        return ImageFont.load_default()


def wrap_quote_to_lines(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int = 880,
    preserve_linebreaks: bool = True,
    **kwargs: Any,
) -> List[str]:
    """
    Tự động ngắt dòng văn bản tiếng Việt an toàn theo chiều rộng màn hình.

    Args:
        text: Nội dung câu trích dẫn.
        font: Font chữ đang dùng để đo kích thước.
        max_width: Chiều rộng tối đa cho phép của vùng chữ (pixels).
        preserve_linebreaks:
            - True: Giữ nguyên các dấu Enter/xuống dòng do người dùng gõ, đồng thời
              vẫn tự động bẻ dòng nếu 1 câu quá dài vượt quá max_width.
            - False (chế độ cũ): Tự động dồn toàn bộ câu thành 1 đoạn văn liên tục
              và dàn đều dòng theo max_width.

    Returns:
        Danh sách các dòng text đã ngắt.
    """
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    def _wrap_single_segment(segment: str) -> List[str]:
        words = segment.strip().split()
        if not words:
            return []
        seg_lines: List[str] = []
        curr = ""
        for word in words:
            test_line = f"{curr} {word}".strip() if curr else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w <= max_width:
                curr = test_line
            else:
                if curr:
                    seg_lines.append(curr)
                curr = word
        if curr:
            seg_lines.append(curr)
        return seg_lines

    if not preserve_linebreaks:
        clean_text = " ".join(text.strip().split())
        return _wrap_single_segment(clean_text)

    # Chế độ giữ nguyên ngắt dòng theo phím Enter
    raw_lines = text.strip().splitlines()
    lines: List[str] = []
    for raw in raw_lines:
        s = raw.strip()
        if not s:
            # Dòng trống phân đoạn (tránh nhiều dòng trống liền nhau)
            if lines and lines[-1] != "":
                lines.append("")
            continue
        wrapped = _wrap_single_segment(s)
        lines.extend(wrapped)

    while lines and lines[-1] == "":
        lines.pop()

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
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 175,
    shadow_blur_radius: float = 5.0,
    stroke_width: int = 1,
    font_path: Optional[Path | str] = None,
    preserve_linebreaks: bool = True,
    text_align: str = "center",  # "center" (mặc định), "right", "left"
    **kwargs: Any,
) -> Image.Image:
    """
    Tạo lớp ảnh chữ trong suốt RGBA (1080x1920) chứa câu quote và chữ ký nhỏ.
    Tích hợp bộ 3 cơ chế chống loá (Anti-Glare / High Contrast):
    - Lớp Bottom Gradient Scrim chuyển mờ êm ái ở đáy.
    - Lớp Soft Blurred Drop Shadow giúp chữ tách khỏi nền phức tạp / nền sáng.
    - Nét viền siêu mảnh (Subtle Micro Stroke) chống tán xạ ánh sáng (anti-halation).
    """
    width, height = canvas_size
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    if text_align == "center":
        safe_margin = max(margin_left, 110)
        max_text_width = canvas_size[0] - 2 * safe_margin
    else:
        max_text_width = canvas_size[0] - margin_left - margin_right

    font = get_vietnamese_font(font_size, font_path=font_path)
    lines = wrap_quote_to_lines(quote, font, max_width=max_text_width, preserve_linebreaks=preserve_linebreaks)

    # Nếu câu dài nhiều dòng, tự động điều chỉnh font size để vừa vặn khung hình
    if len(lines) > 5 and font_size > 34:
        font = get_vietnamese_font(max(32, font_size - 6), font_path=font_path)
        lines = wrap_quote_to_lines(quote, font, max_width=max_text_width, preserve_linebreaks=preserve_linebreaks)
    elif len(lines) > 3 and font_size > 36:
        font = get_vietnamese_font(font_size - 4, font_path=font_path)
        lines = wrap_quote_to_lines(quote, font, max_width=max_text_width, preserve_linebreaks=preserve_linebreaks)

    # Tính toán kích thước từng dòng
    line_metrics = []
    total_text_h = 0
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)

    for line in lines:
        if not line:
            blank_h = int(font.size * 0.4)
            line_metrics.append(("", 0, blank_h))
            total_text_h += blank_h
        else:
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

    # Vị trí Y:
    if text_align == "center":
        # Trung tâm khung hình (cả chiều ngang lẫn chiều dọc chính giữa màn hình)
        start_y = (canvas_size[1] - total_text_h) // 2
    else:
        # Đặt ở góc dưới (cách đáy màn hình khoảng margin_bottom px)
        start_y = canvas_size[1] - margin_bottom - total_text_h

    def get_line_x(w: int) -> int:
        if text_align == "center":
            return (canvas_size[0] - w) // 2
        elif text_align == "right":
            return (canvas_size[0] - margin_right) - w
        else:
            return margin_left

    # 1. Lớp Gradient Scrim chuyển tối êm ái ở khu vực chữ (chống loá nền sáng)
    if enable_gradient_scrim and scrim_max_alpha > 0:
        if text_align == "center":
            # Gradient tối êm dịu tập trung bao quanh khu vực chữ trung tâm khung hình
            scrim_top = max(0, start_y - 180)
            scrim_bottom = min(height, start_y + total_text_h + 180)
            scrim_center_y = start_y + total_text_h // 2
            half_span = max(1.0, (scrim_bottom - scrim_top) / 2.0)
            scrim_draw = ImageDraw.Draw(img)
            for y in range(scrim_top, scrim_bottom):
                dist = abs(y - scrim_center_y) / half_span
                alpha = int(scrim_max_alpha * 0.85 * max(0.0, 1.0 - (dist ** 1.35)))
                if alpha > 0:
                    scrim_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        else:
            # Lớp Bottom Gradient Scrim chuyển tối ở phần đáy màn hình
            scrim_start_y = max(0, start_y - 220)
            scrim_draw = ImageDraw.Draw(img)
            for y in range(scrim_start_y, height):
                progress = (y - scrim_start_y) / (height - scrim_start_y)
                alpha = int(scrim_max_alpha * (progress ** 1.25))
                scrim_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    # Tọa độ X của chữ ký
    sig_x = 0
    if signature and sig_font:
        sig_w = sig_bbox[2] - sig_bbox[0]
        if text_align == "center":
            sig_x = (canvas_size[0] - sig_w) // 2
        elif text_align == "right":
            sig_x = (canvas_size[0] - margin_right) - sig_w
        else:
            sig_x = (canvas_size[0] - margin_right) - sig_w

    # 2. ĐỔ BÓNG KÉP ĐA TẦNG (DUAL-LAYER CINEMA SHADOW)
    # Lớp 2a: Tight Shadow (bóng sát chân chữ tạo độ sắc cạnh, triệt tiêu loá hoàn toàn)
    tight_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(tight_layer)
    curr_y = start_y
    for line, w, h in line_metrics:
        if line:
            lx = get_line_x(w)
            t_draw.text((lx + 2, curr_y + 2), line, font=font, fill=(0, 0, 0, 245))
        curr_y += h + line_spacing

    if signature and sig_font:
        curr_y += (sig_spacing - line_spacing) if lines else 0
        t_draw.text((sig_x + 2, curr_y + 2), signature, font=sig_font, fill=(0, 0, 0, 220))

    blurred_tight = tight_layer.filter(ImageFilter.GaussianBlur(radius=1.2))
    img = Image.alpha_composite(img, blurred_tight)

    # Lớp 2b: Soft Ambient Shadow (bóng mờ lan tỏa tạo chiều sâu điện ảnh)
    if shadow_blur_radius > 0:
        soft_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(soft_layer)
        curr_y = start_y
        for line, w, h in line_metrics:
            if line:
                lx = get_line_x(w)
                s_draw.text((lx + 1, curr_y + 4), line, font=font, fill=(0, 0, 0, 185))
            curr_y += h + line_spacing

        if signature and sig_font:
            curr_y += (sig_spacing - line_spacing) if lines else 0
            s_draw.text((sig_x + 1, curr_y + 4), signature, font=sig_font, fill=(0, 0, 0, 160))

        blurred_soft = soft_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur_radius))
        img = Image.alpha_composite(img, blurred_soft)

    # 3. Vẽ chữ Off-White cao cấp với đường viền sắc nét (Crisp Micro-Stroke)
    draw = ImageDraw.Draw(img)
    curr_y = start_y
    for line, w, h in line_metrics:
        if line:
            lx = get_line_x(w)
            draw.text(
                (lx, curr_y),
                line,
                font=font,
                fill=(248, 250, 252, 255),  # Off-white dịu mắt, chống optical halation
                stroke_width=stroke_width,
                stroke_fill=(8, 12, 20, 215),  # Viền đen đậm nét, sắc sảo
            )
        curr_y += h + line_spacing

    # 4. Vẽ chữ ký nhỏ bên dưới câu quote
    if signature and sig_font:
        curr_y += (sig_spacing - line_spacing) if lines else 0
        draw.text(
            (sig_x, curr_y),
            signature,
            font=sig_font,
            fill=(241, 245, 249, 215),
            stroke_width=max(0, stroke_width - 1),
            stroke_fill=(8, 12, 20, 190),
        )

    return img


def render_18s_video(
    image_path: Path | str,
    quote: str,
    output_path: Path | str = Path("output/tiktok_10s_ready.mp4"),
    duration: float = 10.0,
    overlay_opacity: float = 0.50,
    signature: Optional[str] = "saigonbac",
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 175,
    shadow_blur_radius: float = 5.0,
    stroke_width: int = 1,
    motion_type: str = "cinematic_drift",
    cinematic_vignette: bool = True,
    font_path: Optional[Path | str] = None,
    preserve_linebreaks: bool = True,
    text_align: str = "center",
    font_size: int = 42,
    **kwargs: Any,
) -> Path:
    """
    Render video TikTok chuẩn 10 giây, tỷ lệ 9:16 (1080x1920), không có âm thanh.

    Args:
        image_path: Đường dẫn ảnh nền JPEG/PNG.
        quote: Nội dung câu trích dẫn hiển thị trên video.
        output_path: Đường dẫn file video xuất ra (mặc định output/tiktok_18s_ready.mp4).
        duration: Thời lượng video (cố định 10.0s).
        overlay_opacity: Độ tối lớp phủ đen (mặc định 30% = 0.30).
        signature: Chữ ký thương hiệu nhỏ (mặc định 'saigonbac').
        enable_gradient_scrim: Bật lớp gradient scrim ở đáy chống loá cho nền sáng.
        scrim_max_alpha: Độ sâu tối đa của lớp gradient scrim (0-255).
        shadow_blur_radius: Độ mờ của quầng bóng chữ (Gaussian blur).
        stroke_width: Nét viền siêu mảnh chống loá (1px).
        preserve_linebreaks: True giữ ngắt dòng Enter, False dồn đoạn văn tự động.

    Returns:
        Path dẫn tới video thành phẩm.
    """
    img_file = Path(image_path)
    if not img_file.exists():
        raise FileNotFoundError(f"Không tìm thấy ảnh nền: {img_file}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Tạo ảnh chữ PNG tạm thời kèm chữ ký (áp dụng bộ 3 chống loá)
    overlay_img = create_quote_overlay(
        quote=quote,
        signature=signature,
        enable_gradient_scrim=enable_gradient_scrim,
        scrim_max_alpha=scrim_max_alpha,
        shadow_blur_radius=shadow_blur_radius,
        stroke_width=stroke_width,
        font_path=font_path,
        preserve_linebreaks=preserve_linebreaks,
        text_align=text_align,
        font_size=font_size,
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
        tmp_png_path = Path(tmp_png.name)
    overlay_img.save(tmp_png_path, format="PNG")

    # 2. Xây dựng lệnh FFmpeg biến ảnh tĩnh thành video 10 giây
    # Fade in 1.2s lúc đầu và Fade out 0.8s ở giây 17.2
    fade_out_start = max(1.5, duration - 0.8)

    # Filter ghép ảnh và chữ:
    # - Nếu motion_type là 'cinematic_drift': zoompan siêu chậm Ken Burns 1.0 -> 1.05 tạo thước phim sống động
    # - Chữ trắng fade-in mượt từ giây 0.3 trong 1.0s
    num_frames = max(1, int(duration * 30))
    if motion_type in ["cinematic_drift", "zoom"]:
        zoom_step = 0.06 / num_frames
        motion_filter = f"zoompan=z='min(zoom+{zoom_step:.6f},1.06)':d={num_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
    else:
        motion_filter = "fps=30,"

    vignette_f = "vignette=PI/5.5," if cinematic_vignette else ""
    dark_grading_f = "eq=contrast=1.16:brightness=-0.12:saturation=0.92,colorbalance=rs=-0.03:gs=-0.01:bs=0.04:rh=0.04:gh=0.02:bh=-0.02,"
    dark_box = f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity:.2f}:t=fill," if overlay_opacity > 0 else ""
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,"
        f"{motion_filter}"
        f"{dark_grading_f}"
        f"{vignette_f}"
        f"{dark_box}"
        f"fps=30[bg];"
        f"[1:v]format=rgba[text];"
        f"[bg][text]overlay=0:0:shortest=1[outv]"
    )

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-threads", "2",
        "-loop", "1",
        "-t", str(duration),
        "-i", str(img_file),
        "-loop", "1",
        "-i", str(tmp_png_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",  # Tối ưu cân bằng sắc nét chuẩn TikTok & tốc độ render siêu tốc
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(duration),
        "-an",  # KHÔNG CÓ AUDIO STREAM
        str(out_file),
    ]

    try:
        logger.info(f"Đang render video 10s TikTok -> {out_file.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error(f"Lỗi FFmpeg:\n{proc.stderr}")
            raise RuntimeError(f"Lỗi FFmpeg khi render video: {proc.stderr[:300]}")

    finally:
        if tmp_png_path.exists():
            tmp_png_path.unlink()
        try:
            del overlay_img
        except Exception:
            pass
        gc.collect()

    logger.info(f"Render video 10s thành công: {out_file} ({out_file.stat().st_size} bytes)")
    return out_file


def render_video_from_footage(
    footage_path: Path | str,
    quote: str,
    output_path: Path | str = Path("output/tiktok_video_ready.mp4"),
    duration: Optional[float] = None,
    overlay_opacity: float = 0.50,
    signature: Optional[str] = "saigonbac",
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 175,
    shadow_blur_radius: float = 5.0,
    stroke_width: int = 1,
    font_path: Optional[Path | str] = None,
    preserve_linebreaks: bool = True,
    text_align: str = "center",
    font_size: int = 42,
    **kwargs: Any,
) -> Path:
    """
    Render video TikTok hoàn chỉnh từ footage video và câu quote typography:
    - Scale & Center-Crop về đúng chuẩn dọc 1080x1920 (9:16).
    - Tự động lặp (loop) nếu video ngắn hơn thời lượng xuất (mặc định 10.0s).
    - Phủ lớp tối (overlay_opacity) theo thanh trượt để chữ luôn nổi bật.
    - Ghép typography căn lề (center/right/left) và cỡ chữ tùy chọn.
    - Tắt hoàn toàn audio stream (-an).
    """
    vid_file = Path(footage_path)
    if not vid_file.exists():
        raise FileNotFoundError(f"Không tìm thấy video footage: {vid_file}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    actual_duration = float(duration) if (duration is not None and duration > 0) else determine_media_duration(vid_file)

    # 1. Đo độ dài footage để loop nếu cần
    from modules.video_engine import probe_video_metadata
    meta = probe_video_metadata(vid_file)
    orig_dur = meta.get("duration", 0.0)

    inputs = []
    if orig_dur > 0 and orig_dur < actual_duration:
        loop_count = int(actual_duration // orig_dur) + 2
        inputs.extend(["-stream_loop", str(loop_count), "-i", str(vid_file)])
    else:
        inputs.extend(["-i", str(vid_file)])

    # 2. Tạo ảnh chữ PNG tạm thời kèm chữ ký với đầy đủ typography mới
    overlay_img = create_quote_overlay(
        quote=quote,
        signature=signature,
        enable_gradient_scrim=enable_gradient_scrim,
        scrim_max_alpha=scrim_max_alpha,
        shadow_blur_radius=shadow_blur_radius,
        stroke_width=stroke_width,
        font_path=font_path,
        preserve_linebreaks=preserve_linebreaks,
        text_align=text_align,
        font_size=font_size,
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
        tmp_png_path = Path(tmp_png.name)
    overlay_img.save(tmp_png_path, format="PNG")

    # 3. Filter FFmpeg
    dark_box = f",drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity:.2f}:t=fill" if overlay_opacity > 0 else ""

    filter_complex = (
        f"[0:v]trim=0:{actual_duration},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,fps=30"
        f"{dark_box}[bg];"
        f"[1:v]format=rgba[text];"
        f"[bg][text]overlay=0:0:shortest=1[outv]"
    )

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-threads", "2",
        *inputs,
        "-loop", "1",
        "-i", str(tmp_png_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(actual_duration),
        "-an",
        str(out_file),
    ]

    try:
        logger.info(f"Đang render quote lên video footage -> {out_file.name} ({actual_duration}s)...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error(f"Lỗi FFmpeg:\n{proc.stderr}")
            raise RuntimeError(f"Lỗi FFmpeg khi render video từ footage: {proc.stderr[:300]}")
    finally:
        if tmp_png_path.exists():
            tmp_png_path.unlink()
        try:
            del overlay_img
        except Exception:
            pass
        gc.collect()

    logger.info(f"Render video footage thành công: {out_file} ({out_file.stat().st_size} bytes)")
    return out_file


def render_any_media_quote(
    media_path: Path | str,
    quote: str,
    output_path: Path | str = Path("output/tiktok_ready.mp4"),
    duration: Optional[float] = None,
    overlay_opacity: float = 0.50,
    signature: Optional[str] = "saigonbac",
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 175,
    shadow_blur_radius: float = 5.0,
    stroke_width: int = 1,
    font_path: Optional[Path | str] = None,
    preserve_linebreaks: bool = True,
    text_align: str = "center",
    font_size: int = 42,
    **kwargs: Any,
) -> Path:
    """
    Hàm tự động nhận diện định dạng ảnh tĩnh hay video để gọi hàm render phù hợp.
    """
    p = Path(media_path)
    if duration is None or duration <= 0:
        duration = determine_media_duration(p)
    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    common_args = {
        "quote": quote,
        "output_path": output_path,
        "duration": duration,
        "overlay_opacity": overlay_opacity,
        "signature": signature,
        "enable_gradient_scrim": enable_gradient_scrim,
        "scrim_max_alpha": scrim_max_alpha,
        "shadow_blur_radius": shadow_blur_radius,
        "stroke_width": stroke_width,
        "font_path": font_path,
        "preserve_linebreaks": preserve_linebreaks,
        "text_align": text_align,
        "font_size": font_size,
    }
    if p.suffix.lower() in video_exts:
        return render_video_from_footage(footage_path=p, **common_args, **kwargs)
    return render_18s_video(image_path=p, **common_args, **kwargs)



# Alias cho phiên bản 10 giây
render_10s_video = render_18s_video
