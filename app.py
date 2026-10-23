from __future__ import annotations

import json
import logging
import os
import sys
import time
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
    page_title="TikTok 18s Quote Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuoteStudio")

# ==============================================================================
# ULTRA-PREMIUM AESTHETIC CSS (GLASSMORPHISM & CYBER-CHIC DARK THEME)
# ==============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #070B12 !important;
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 90% 20%, rgba(129, 140, 248, 0.09) 0%, transparent 45%),
            radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.06) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #F1F5F9;
    }

    /* Container chung */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1360px !important;
    }

    /* Header & Branding */
    .hero-top-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(14, 165, 233, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #38BDF8;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
        box-shadow: 0 0 20px -3px rgba(56, 189, 248, 0.3);
    }
    .hero-dot {
        width: 8px;
        height: 8px;
        background-color: #38BDF8;
        border-radius: 50%;
        box-shadow: 0 0 10px #38BDF8;
        animation: pulse-dot 2s infinite ease-in-out;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    .main-title {
        font-size: 2.35rem;
        font-weight: 900;
        letter-spacing: -0.8px;
        background: linear-gradient(135deg, #FFFFFF 20%, #7DD3FC 60%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        line-height: 1.2;
    }

    .main-subtitle {
        color: #94A3B8;
        font-size: 0.98rem;
        margin-bottom: 1.8rem;
        line-height: 1.6;
        max-width: 850px;
    }

    /* Feature tags ngang */
    .feature-tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 1.6rem;
    }
    .feature-tag-pill {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 5px 12px;
        font-size: 0.82rem;
        color: #CBD5E1;
        font-weight: 500;
    }

    /* Step Card Glassmorphism */
    .glass-card {
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 18px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.45);
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 12px 35px -5px rgba(14, 165, 233, 0.12);
    }

    /* Step Badge */
    .step-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.9rem;
    }
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #0284C7 0%, #38BDF8 100%);
        color: #FFFFFF;
        font-size: 0.88rem;
        font-weight: 800;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
    }
    .step-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F8FAFC;
        letter-spacing: -0.2px;
    }

    /* Quick quote suggestions chips */
    .chip-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 6px;
    }

    /* Word Counter Badge */
    .word-counter-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 6px;
        padding: 6px 10px;
        border-radius: 8px;
        background: rgba(30, 41, 59, 0.5);
        font-size: 0.82rem;
    }
    .word-badge-ok {
        color: #34D399;
        font-weight: 700;
    }
    .word-badge-warn {
        color: #FBBF24;
        font-weight: 600;
    }

    /* Hero Action Button */
    .btn-render-hero button {
        background: linear-gradient(135deg, #0284C7 0%, #2563EB 50%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        min-height: 58px !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px -4px rgba(37, 99, 235, 0.55) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        letter-spacing: 0.3px !important;
    }
    .btn-render-hero button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 14px 40px -4px rgba(56, 189, 248, 0.75) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }

    /* Phone Mockup Frame cho Live Preview & Video */
    .phone-mockup-wrapper {
        background: #000000;
        border: 3px solid rgba(255, 255, 255, 0.12);
        border-radius: 28px;
        padding: 10px;
        box-shadow: 
            0 0 0 1px rgba(0, 0, 0, 0.8),
            0 25px 60px -15px rgba(0, 0, 0, 0.9),
            0 0 35px -5px rgba(56, 189, 248, 0.25);
        position: relative;
        max-width: 440px;
        margin: 0 auto;
    }
    .phone-notch {
        width: 100px;
        height: 18px;
        background: #0F172A;
        border-radius: 0 0 12px 12px;
        margin: 0 auto 10px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }
    .phone-lens {
        width: 7px;
        height: 7px;
        background: #1E293B;
        border-radius: 50%;
        box-shadow: inset 0 0 2px #38BDF8;
    }
    .phone-speaker {
        width: 32px;
        height: 4px;
        background: #334155;
        border-radius: 4px;
    }

    /* Style media bên trong */
    .phone-mockup-wrapper video,
    .phone-mockup-wrapper .stImage img {
        border-radius: 18px !important;
        max-height: 540px !important;
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
        object-fit: cover !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6) !important;
    }

    /* Status badge trên preview */
    .preview-pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #38BDF8;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.7rem;
    }

    /* Dashboard thông số */
    .meta-dashboard {
        display: flex;
        justify-content: space-around;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.75rem;
        margin-top: 0.8rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .meta-item-val {
        font-size: 0.95rem;
        font-weight: 800;
        color: #38BDF8;
        font-family: 'JetBrains Mono', monospace;
    }
    .meta-item-lbl {
        font-size: 0.72rem;
        color: #94A3B8;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* Download button */
    .btn-download button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        min-height: 52px !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 25px -4px rgba(16, 185, 129, 0.45) !important;
        transition: transform 0.2s !important;
    }
    .btn-download button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 30px -4px rgba(16, 185, 129, 0.65) !important;
    }

    /* Tinh chỉnh input form streamlit */
    .stTextArea textarea, .stTextInput input {
        background-color: rgba(15, 23, 42, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #F8FAFC !important;
        border-radius: 12px !important;
        font-size: 0.95rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.3) !important;
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
# KHỞI TẠO STATE & CẤU HÌNH MẶC ĐỊNH
# ==============================================================================
config = load_config()

if "quote_text" not in st.session_state:
    st.session_state.quote_text = ""
if "bg_image" not in st.session_state:
    st.session_state.bg_image = None
if "last_uploaded_bg_name" not in st.session_state:
    st.session_state.last_uploaded_bg_name = None
if "rendered_video" not in st.session_state:
    st.session_state.rendered_video = None
if "signature" not in st.session_state:
    st.session_state.signature = config.get("branding", {}).get("signature", "saigonbac")
if "enable_antiglare" not in st.session_state:
    st.session_state.enable_antiglare = True


# ==============================================================================
# HEADER & HERO SECTION
# ==============================================================================
st.markdown(
    """
    <div class="hero-top-badge">
        <span class="hero-dot"></span>
        TIKTOK 18S STUDIO • HIGH DEFINITION ENGINE
    </div>
    <div class="main-title">AESTHETIC QUOTE VIDEO CREATOR</div>
    <div class="main-subtitle">
        Tạo video tĩnh 18s TikTok chuẩn điện ảnh: Tự nhập câu quote, tự tải ảnh nền từ máy tính và xuất video 1080x1920 sắc nét.
    </div>
    <div class="feature-tags-row">
        <div class="feature-tag-pill">📐 Khổ dọc 1080x1920 (9:16)</div>
        <div class="feature-tag-pill">⏱️ Thời lượng 18.0s TikTok</div>
        <div class="feature-tag-pill">🎬 Ken Burns Cinematic Drift</div>
        <div class="feature-tag-pill">✨ Typography Anti-Glare Scrim</div>
        <div class="feature-tag-pill">⚡ FFmpeg H.264 Lossless CRF 16</div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_input, col_preview = st.columns([1.25, 1.0], gap="large")

# ==============================================================================
# CỘT TRÁI: WORKSPACE NHẬP QUOTE & TẢI ẢNH NỀN
# ==============================================================================
with col_input:
    # ---------------- BƯỚC 1: CÂU QUOTE ----------------
    with st.container():
        st.markdown(
            """
            <div class="glass-card">
                <div class="step-header">
                    <div class="step-number">01</div>
                    <div class="step-title">Nội Dung Câu Quote</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        input_quote = st.text_area(
            "Nhập câu quote của bạn:",
            value=st.session_state.quote_text,
            placeholder="Gõ hoặc dán câu quote của bạn tại đây...",
            height=120,
            key="txt_quote_input",
            label_visibility="collapsed",
        )
        if input_quote != st.session_state.quote_text:
            st.session_state.quote_text = input_quote
            st.session_state.rendered_video = None

        # Đếm từ trực quan
        current_words = input_quote.strip().split() if input_quote.strip() else []
        count = len(current_words)
        if 15 <= count <= 26:
            st.markdown(
                f"""
                <div class="word-counter-box">
                    <span class="word-badge-ok">✓ Độ dài hoàn hảo ({count} từ)</span>
                    <span style="color: #94A3B8;">Chuẩn 15 - 26 từ cho nhịp đọc 18 giây TikTok</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif count > 0:
            st.markdown(
                f"""
                <div class="word-counter-box">
                    <span class="word-badge-warn">ℹ️ {count} từ</span>
                    <span style="color: #94A3B8;">Khuyên dùng 15 - 26 từ để bố cục thoáng đẹp nhất</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- BƯỚC 2: ẢNH NỀN ----------------
    with st.container():
        st.markdown(
            """
            <div class="glass-card">
                <div class="step-header">
                    <div class="step-number">02</div>
                    <div class="step-title">Tải Ảnh Nền Từ Máy Tính</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        up_file = st.file_uploader(
            "Kéo thả hoặc duyệt file ảnh (.jpg, .png, .webp):",
            type=["jpg", "jpeg", "png", "webp", "jfif", "bmp"],
            key="file_bg_uploader",
            help="Hệ thống tự động canh giữa và crop chuẩn 9:16 (1080x1920).",
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
                    st.toast(f"Đã nạp và chuẩn hóa ảnh: {up_file.name}", icon="📸")
                except Exception as e:
                    st.error(f"Lỗi khi xử lý ảnh tải lên: {e}")
        else:
            if st.session_state.get("last_uploaded_bg_name") is not None:
                st.session_state.last_uploaded_bg_name = None
                st.session_state.bg_image = None
                st.session_state.rendered_video = None

        if st.session_state.get("last_uploaded_bg_name"):
            col_cur, col_del = st.columns([3, 1])
            with col_cur:
                st.markdown(f"<span style='color: #38BDF8; font-size: 0.88rem;'>📸 Đang dùng: <b>{st.session_state.last_uploaded_bg_name}</b></span>", unsafe_allow_html=True)
            with col_del:
                if st.button("🗑️ Đổi ảnh", key="btn_del_bg", use_container_width=True):
                    st.session_state.last_uploaded_bg_name = None
                    st.session_state.bg_image = None
                    st.session_state.rendered_video = None
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TUỲ CHỌN HIỂN THỊ (EXPANDER) ----------------
    with st.expander("⚙️ Tuỳ chỉnh chữ ký & bộ lọc chống loá", expanded=False):
        col_opt1, col_opt2 = st.columns([1.2, 1.0])
        with col_opt1:
            sig_input = st.text_input(
                "Chữ ký video (Signature):",
                value=st.session_state.signature,
                key="txt_sig_input",
                placeholder="saigonbac, @channel...",
            )
            if sig_input != st.session_state.signature:
                st.session_state.signature = sig_input
                st.session_state.rendered_video = None

        with col_opt2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.session_state.enable_antiglare = st.checkbox(
                "Bật Scrim & Drop Shadow chống loá",
                value=st.session_state.enable_antiglare,
                help="Thêm lớp dốc mờ và bóng đen để chữ luôn sắc nét trên mọi bức ảnh.",
            )

    st.write("")

    # ---------------- NÚT HÀNH ĐỘNG HERO ----------------
    st.markdown('<div class="btn-render-hero">', unsafe_allow_html=True)
    btn_generate = st.button("✨ XUẤT VIDEO TIKTOK 18S CHUẨN HD", type="primary", use_container_width=True)
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

            with st.spinner("Đang ghép typography và render video 18.0s chuẩn TikTok (Ken Burns chuyển động chậm)..."):
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
                    st.toast("Tạo video 18s hoàn tất thành công 100%!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi render video: {e}")


# ==============================================================================
# CỘT PHẢI: PHONE MOCKUP XEM TRƯỚC (LIVE PREVIEW) & VIDEO THÀNH PHẨM
# ==============================================================================
with col_preview:
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <div class="step-title" style="font-size: 1.15rem;">Khung Xem Trước Trực Quan</div>
            <div class="preview-pill-badge">
                <span style="display:inline-block; width:6px; height:6px; background:#38BDF8; border-radius:50%;"></span>
                LIVE 9:16
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rendered_vid = st.session_state.rendered_video
    bg_img = st.session_state.bg_image
    quote_ready = bool(st.session_state.quote_text.strip())

    # Khung Phone Mockup
    st.markdown(
        """
        <div class="phone-mockup-wrapper">
            <div class="phone-notch">
                <div class="phone-speaker"></div>
                <div class="phone-lens"></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. LIVE TYPOGRAPHY PREVIEW HOẶC VIDEO ĐÃ XUẤT
    if rendered_vid and Path(rendered_vid).exists():
        st.video(str(rendered_vid))
    elif bg_img and Path(bg_img).exists():
        if quote_ready:
            try:
                with Image.open(bg_img) as raw_bg:
                    bg_rgba = raw_bg.convert("RGBA")
                    if bg_rgba.size != (1080, 1920):
                        bg_rgba = bg_rgba.resize((1080, 1920), Image.Resampling.LANCZOS)

                    text_overlay = create_quote_overlay(
                        quote=st.session_state.quote_text,
                        signature=st.session_state.signature or "saigonbac",
                        enable_gradient_scrim=st.session_state.enable_antiglare,
                    )
                    preview_composite = Image.alpha_composite(bg_rgba, text_overlay)
                    st.image(preview_composite.convert("RGB"), use_container_width=True)
            except Exception as ex:
                logger.warning(f"Lỗi live preview: {ex}")
                with Image.open(bg_img) as _bimg:
                    st.image(_bimg.convert("RGB"), use_container_width=True)
        else:
            with Image.open(bg_img) as _bimg:
                st.image(_bimg.convert("RGB"), use_container_width=True)
    else:
        st.markdown(
            """
            <div style="height: 480px; display: flex; align-items: center; justify-content: center; color: #64748B; text-align: center; padding: 2rem;">
                <div>
                    <div style="font-size: 2.8rem; margin-bottom: 0.8rem;">📱</div>
                    <b style="color: #94A3B8;">Chưa có ảnh nền</b><br>
                    <span style="font-size: 0.85rem;">Tải ảnh ở Bước 2 để hiển thị chữ trực tiếp trên khung.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # Kết thúc phone mockup

    # 2. DASHBOARD THÔNG SỐ & NÚT TẢI XUỐNG
    if rendered_vid and Path(rendered_vid).exists():
        meta = probe_video_metadata(rendered_vid)
        st.markdown(
            f"""
            <div class="meta-dashboard">
                <div>
                    <div class="meta-item-val">1080×1920</div>
                    <div class="meta-item-lbl">Độ phân giải</div>
                </div>
                <div>
                    <div class="meta-item-val">{meta.get('duration', 18.0)}s</div>
                    <div class="meta-item-lbl">Thời lượng</div>
                </div>
                <div>
                    <div class="meta-item-val">30 FPS</div>
                    <div class="meta-item-lbl">Tốc độ khung</div>
                </div>
                <div>
                    <div class="meta-item-val">H.264</div>
                    <div class="meta-item-lbl">Định dạng</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with open(rendered_vid, "rb") as vf:
            st.markdown('<div class="btn-download">', unsafe_allow_html=True)
            st.download_button(
                label="⬇️ TẢI VIDEO XUỐNG (.MP4)",
                data=vf.read(),
                file_name=f"tiktok_quote_{int(time.time())}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True,
                key="btn_download_video",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        st.caption(f"📁 Lưu tại: `{rendered_vid}`")
    else:
        st.markdown(
            """
            <div style="text-align: center; color: #64748B; font-size: 0.82rem; margin-top: 1rem;">
                💡 Chữ trên khung preview được cập nhật theo thời gian thực (Realtime Live Preview).
            </div>
            """,
            unsafe_allow_html=True,
        )
