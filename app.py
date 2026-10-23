from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

# Đảm bảo thư mục gốc dự án luôn nằm đầu sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
try:
    os.chdir(project_root)
except Exception:
    pass

import streamlit as st
from PIL import Image, ImageOps

from modules.video_engine import probe_video_metadata
from modules.video_renderer import create_quote_overlay, render_18s_video

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="TikTok Quote Studio - 18s Video",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuoteStudio")

# Custom CSS giao diện tối giản, hiện đại và sang trọng
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #38BDF8 60%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    
    .sub-header {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    .step-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.25);
    }

    .step-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8;
        font-weight: 700;
        font-size: 0.8rem;
        padding: 0.25rem 0.65rem;
        border-radius: 20px;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(56, 189, 248, 0.35);
    }

    .btn-create button {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        min-height: 56px !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 25px -4px rgba(2, 132, 199, 0.5) !important;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .btn-create button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px -4px rgba(2, 132, 199, 0.7) !important;
    }

    video, .stImage img {
        max-height: 520px !important;
        width: auto !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
        border-radius: 16px !important;
        box-shadow: 0 14px 35px -5px rgba(0, 0, 0, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .badge-meta {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
        font-size: 0.85rem;
        text-align: center;
        color: #38BDF8;
        margin-top: 0.6rem;
        margin-bottom: 0.8rem;
    }

    .word-badge-ok {
        color: #10B981;
        font-weight: 700;
        font-size: 0.86rem;
    }
    .word-badge-warn {
        color: #F59E0B;
        font-weight: 700;
        font-size: 0.86rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_config() -> Dict[str, Any]:
    """Nạp cấu hình từ file config.json."""
    cfg_path = Path("config.json")
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def crop_image_to_tiktok_portrait(image_path: Path, target_size=(1080, 1920)) -> Path:
    """Cắt và căn giữa (Center-Crop) ảnh chính xác về khổ dọc 1080x1920 (9:16)."""
    with Image.open(image_path) as img:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        img = img.convert("RGB")
        target_w, target_h = target_size
        img_w, img_h = img.size

        target_ratio = target_w / target_h
        current_ratio = img_w / img_h

        if current_ratio > target_ratio:
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            top = 0
            img = img.crop((left, top, left + new_w, img_h))
        else:
            new_h = int(img_w / target_ratio)
            left = 0
            top = (img_h - new_h) // 2
            img = img.crop((left, top, img_w, top + new_h))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.save(image_path, format="JPEG", quality=95)

    return image_path


# ==============================================================================
# KHỞI TẠO STATE
# ==============================================================================
config = load_config()

default_sample_bg = Path("assets/samples/curated_saigonbac/cafe_night.jpg")
if not default_sample_bg.exists():
    samples_dir = Path("assets/samples/curated_saigonbac")
    if samples_dir.exists():
        found = list(samples_dir.glob("*.jpg"))
        if found:
            default_sample_bg = found[0]

if "quote_text" not in st.session_state:
    st.session_state.quote_text = "Thành phố này rộng lớn đến mức, chỉ cần quay lưng lại một cái là cả đời chẳng còn gặp lại nhau."
if "bg_image" not in st.session_state:
    st.session_state.bg_image = str(default_sample_bg) if default_sample_bg.exists() else None
if "last_uploaded_bg_name" not in st.session_state:
    st.session_state.last_uploaded_bg_name = None
if "rendered_video" not in st.session_state:
    st.session_state.rendered_video = None
if "signature" not in st.session_state:
    st.session_state.signature = config.get("branding", {}).get("signature", "saigonbac")
if "enable_antiglare" not in st.session_state:
    st.session_state.enable_antiglare = True


# ==============================================================================
# GIAO DIỆN CHÍNH
# ==============================================================================
st.markdown('<div class="main-header">🎬 TIKTOK QUOTE STUDIO</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Tạo video tĩnh 18s TikTok Aesthetic: Tự nhập quote + Tải ảnh nền từ máy tính + Xuất video 1080x1920 chuẩn nét.</div>',
    unsafe_allow_html=True,
)

col_input, col_preview = st.columns([1.3, 1.0], gap="large")

# ==============================================================================
# CỘT TRÁI: NHẬP QUOTE & CHỌN ẢNH NỀN
# ==============================================================================
with col_input:
    # --- BƯỚC 1: NHẬP CÂU QUOTE ---
    with st.container():
        st.markdown('<div class="step-badge">BƯỚC 1</div>', unsafe_allow_html=True)
        st.subheader("Nhập Nội Dung Câu Quote")

        input_quote = st.text_area(
            "Nội dung câu quote hiển thị trên video:",
            value=st.session_state.quote_text,
            placeholder="Gõ hoặc dán câu quote của bạn vào đây...",
            height=110,
            key="txt_quote_input",
        )
        if input_quote != st.session_state.quote_text:
            st.session_state.quote_text = input_quote
            st.session_state.rendered_video = None

        if input_quote.strip():
            words = input_quote.strip().split()
            word_count = len(words)
            if 15 <= word_count <= 26:
                st.markdown(
                    f'<span class="word-badge-ok">✓ Độ dài lý tưởng: <b>{word_count} từ</b> (chuẩn 15 - 26 từ cho video 18s).</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="word-badge-warn">ℹ️ Hiện tại: <b>{word_count} từ</b>. Khuyên dùng 15 - 26 từ để người xem kịp đọc trọn vẹn và bố cục đẹp nhất.</span>',
                    unsafe_allow_html=True,
                )

    st.write("")

    # --- BƯỚC 2: TẢI ẢNH NỀN TỪ MÁY TÍNH ---
    with st.container():
        st.markdown('<div class="step-badge">BƯỚC 2</div>', unsafe_allow_html=True)
        st.subheader("Tải Ảnh Nền Từ Máy Tính")
        st.caption("Tải file ảnh (.jpg, .png, .webp). Hệ thống sẽ tự động crop căn giữa về chuẩn dọc 9:16 (1080x1920).")

        up_file = st.file_uploader(
            "Chọn file ảnh từ máy của bạn:",
            type=["jpg", "jpeg", "png", "webp", "jfif", "bmp"],
            key="file_bg_uploader",
        )
        if up_file is not None:
            if up_file.name != st.session_state.get("last_uploaded_bg_name"):
                try:
                    temp_dir = Path("temp")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    file_ext = Path(up_file.name).suffix or ".jpg"
                    unique_bg_path = temp_dir / f"bg_{int(time.time() * 1000)}{file_ext}"
                    with open(unique_bg_path, "wb") as f_out:
                        f_out.write(up_file.getbuffer())

                    crop_path = crop_image_to_tiktok_portrait(unique_bg_path)
                    st.session_state.bg_image = str(crop_path)
                    st.session_state.last_uploaded_bg_name = up_file.name
                    st.session_state.rendered_video = None
                    st.toast(f"Đã nạp ảnh mới: {up_file.name}", icon="📸")
                except Exception as e:
                    st.error(f"Lỗi khi xử lý ảnh: {e}")
        else:
            if st.session_state.get("last_uploaded_bg_name") is not None:
                st.session_state.last_uploaded_bg_name = None
                st.session_state.bg_image = str(default_sample_bg) if default_sample_bg.exists() else None
                st.session_state.rendered_video = None

        if st.session_state.get("last_uploaded_bg_name"):
            col_cur, col_del = st.columns([3, 1])
            with col_cur:
                st.caption(f"✅ Đang dùng ảnh bạn tải lên: **{st.session_state.last_uploaded_bg_name}**")
            with col_del:
                if st.button("🗑️ Đổi ảnh khác", key="btn_del_bg"):
                    st.session_state.last_uploaded_bg_name = None
                    st.session_state.bg_image = str(default_sample_bg) if default_sample_bg.exists() else None
                    st.session_state.rendered_video = None
                    st.rerun()

        elif default_sample_bg.exists():
            st.caption(f"ℹ️ Đang dùng ảnh mẫu mặc định: `{default_sample_bg.name}`")

    st.write("")

    # --- TUỲ CHỌN BỔ SUNG (CHỮ KÝ & CHỐNG LOÁ) ---
    with st.expander("⚙️ Tuỳ chọn chữ ký & hiển thị", expanded=False):
        sig_input = st.text_input(
            "Chữ ký video (Signature):",
            value=st.session_state.signature,
            key="txt_sig_input",
            help="Chữ ký nhỏ xuất hiện bên dưới quote (ví dụ: saigonbac, @yourchannel...)",
        )
        if sig_input != st.session_state.signature:
            st.session_state.signature = sig_input
            st.session_state.rendered_video = None

        st.session_state.enable_antiglare = st.checkbox(
            "Bật bộ lọc chống loá chữ (Gradient Scrim & Drop Shadow)",
            value=st.session_state.enable_antiglare,
            help="Tạo lớp phủ dốc mềm ở đáy giúp chữ luôn dễ đọc trên mọi bức ảnh sáng hay tối.",
        )

    st.write("")
    st.divider()

    # --- NÚT HÀNH ĐỘNG RENDER VIDEO ---
    st.markdown('<div class="btn-create">', unsafe_allow_html=True)
    btn_generate = st.button("🚀 TẠO VIDEO 18S TIKTOK", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if btn_generate:
        bg_target = st.session_state.bg_image
        if not bg_target or not Path(bg_target).exists():
            st.error("Chưa có ảnh nền! Vui lòng tải một file ảnh từ máy tính ở Bước 2.")
        elif not st.session_state.quote_text.strip():
            st.error("Câu quote đang trống! Vui lòng nhập quote ở Bước 1.")
        else:
            out_folder = Path("output/saigonbac")
            out_folder.mkdir(parents=True, exist_ok=True)
            out_vid = out_folder / f"tiktok_video_{int(time.time())}.mp4"

            with st.spinner("Đang ghép typography và render video 18.0s chuẩn TikTok (Ken Burns chuyển động)..."):
                try:
                    render_18s_video(
                        image_path=bg_target,
                        quote=st.session_state.quote_text,
                        output_path=out_vid,
                        duration=18.0,
                        signature=st.session_state.signature or "saigonbac",
                        enable_gradient_scrim=st.session_state.enable_antiglare,
                    )
                    st.session_state.rendered_video = str(out_vid)
                    st.toast("Tạo video 18s hoàn tất thành công!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi render video: {e}")


# ==============================================================================
# CỘT PHẢI: XEM TRƯỚC (LIVE PREVIEW) & XUẤT VIDEO
# ==============================================================================
with col_preview:
    st.markdown('<div class="step-badge">BƯỚC 3</div>', unsafe_allow_html=True)
    st.subheader("Xem Trước & Video Thành Phẩm")

    rendered_vid = st.session_state.rendered_video
    bg_img = st.session_state.bg_image
    quote_ready = bool(st.session_state.quote_text.strip())

    # 1. ẢNH XEM TRƯỚC CÓ CHỮ (LIVE TYPOGRAPHY PREVIEW)
    if bg_img and Path(bg_img).exists():
        if quote_ready:
            st.caption("👁️ **Ảnh xem trước có chữ (Live Typography 9:16):**")
            try:
                # Ghép chữ trực tiếp lên ảnh bằng Pillow cho tốc độ tức thì
                with Image.open(bg_img) as raw_bg:
                    bg_rgba = raw_bg.convert("RGBA")
                    # Đảm bảo đúng kích thước 1080x1920
                    if bg_rgba.size != (1080, 1920):
                        bg_rgba = bg_rgba.resize((1080, 1920), Image.Resampling.LANCZOS)

                    # Tạo lớp phủ chữ với đúng cài đặt chữ ký và chống loá
                    text_overlay = create_quote_overlay(
                        quote=st.session_state.quote_text,
                        signature=st.session_state.signature or "saigonbac",
                        enable_gradient_scrim=st.session_state.enable_antiglare,
                    )
                    preview_composite = Image.alpha_composite(bg_rgba, text_overlay)
                    st.image(preview_composite.convert("RGB"), use_container_width=True)
            except Exception as ex:
                logger.warning(f"Lỗi tạo live preview: {ex}")
                with Image.open(bg_img) as _bimg:
                    st.image(_bimg.convert("RGB"), use_container_width=True)
        else:
            with Image.open(bg_img) as _bimg:
                st.image(_bimg.convert("RGB"), use_container_width=True)
            st.caption("🖼️ Ảnh nền đã sẵn sàng. Hãy nhập câu quote ở Bước 1 để hiển thị chữ trên ảnh.")
    else:
        st.markdown(
            """
            <div style="border: 2px dashed #475569; border-radius: 14px; height: 380px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                <div>
                    <div style="font-size: 2.5rem; margin-bottom: 0.6rem;">📱</div>
                    <b>Khung Xem Trước</b><br>
                    <span style="font-size: 0.88rem; color: #64748B;">Hãy tải lên một bức ảnh ở Bước 2 để hiển thị chữ trên ảnh.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. VIDEO THÀNH PHẨM (SAU KHI BẤM RENDER)
    if rendered_vid and Path(rendered_vid).exists():
        st.divider()
        st.markdown("🎬 **Video 18s Đã Tạo:**")
        meta = probe_video_metadata(rendered_vid)
        st.video(str(rendered_vid))
        st.markdown(
            f"""
            <div class="badge-meta">
                📏 <b>1080x1920 (9:16)</b> &nbsp;|&nbsp; ⏱️ <b>{meta.get('duration', 18.0)}s</b> &nbsp;|&nbsp; 🎞️ <b>30fps</b> &nbsp;|&nbsp; 🔇 <b>No Audio</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with open(rendered_vid, "rb") as vf:
            st.download_button(
                label="⬇️ TẢI VIDEO XUỐNG (.MP4)",
                data=vf.read(),
                file_name=f"tiktok_quote_{int(time.time())}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True,
                key="btn_download_video",
            )
        st.caption(f"File lưu tại: `{rendered_vid}`")
