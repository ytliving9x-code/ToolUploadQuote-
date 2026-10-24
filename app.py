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
from PIL import Image, ImageEnhance, ImageOps

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
# ULTRA-PREMIUM AESTHETIC CSS (MOBILE-FIRST OPTIMIZED & GLASSMORPHISM)
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

    /* Container chung tối ưu cho Desktop */
    .block-container {
        padding-top: 1.6rem !important;
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
        padding: 5px 13px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
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
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.7px;
        background: linear-gradient(135deg, #FFFFFF 20%, #7DD3FC 60%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        line-height: 1.2;
    }

    .main-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        line-height: 1.5;
        max-width: 850px;
    }

    /* Feature tags ngang */
    .feature-tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 1.5rem;
    }
    .feature-tag-pill {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 0.8rem;
        color: #CBD5E1;
        font-weight: 500;
    }

    /* Step Card Glassmorphism */
    .glass-card {
        background: rgba(15, 23, 42, 0.68);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 18px;
        padding: 1.3rem 1.4rem;
        margin-bottom: 1.2rem;
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
        gap: 10px;
        margin-bottom: 0.8rem;
    }
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        background: linear-gradient(135deg, #0284C7 0%, #38BDF8 100%);
        color: #FFFFFF;
        font-size: 0.85rem;
        font-weight: 800;
        border-radius: 9px;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
    }
    .step-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F8FAFC;
        letter-spacing: -0.2px;
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
        font-size: 1.12rem !important;
        font-weight: 800 !important;
        min-height: 56px !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px -4px rgba(37, 99, 235, 0.55) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        letter-spacing: 0.3px !important;
    }
    .btn-render-hero button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 14px 40px -4px rgba(56, 189, 248, 0.75) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }
    .btn-render-hero button:active {
        transform: scale(0.98) !important;
    }

    /* Phone Mockup Frame cho Live Preview & Video */
    .phone-mockup-wrapper {
        background: #000000;
        border: 2.5px solid rgba(255, 255, 255, 0.12);
        border-radius: 26px;
        padding: 10px;
        box-shadow: 
            0 0 0 1px rgba(0, 0, 0, 0.8),
            0 25px 60px -15px rgba(0, 0, 0, 0.9),
            0 0 35px -5px rgba(56, 189, 248, 0.2);
        position: relative;
        max-width: 440px;
        margin: 0 auto;
    }
    .phone-notch {
        width: 90px;
        height: 16px;
        background: #0F172A;
        border-radius: 0 0 12px 12px;
        margin: 0 auto 8px auto;
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
        width: 30px;
        height: 4px;
        background: #334155;
        border-radius: 4px;
    }

    /* Style media bên trong */
    .phone-mockup-wrapper video,
    .phone-mockup-wrapper .stImage img {
        border-radius: 18px !important;
        max-height: 520px !important;
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
    .stTextArea textarea, .stTextInput input, .stSelectbox [data-baseweb="select"] {
        background-color: rgba(15, 23, 42, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #F8FAFC !important;
        border-radius: 12px !important;
        font-size: 16px !important; /* Ngăn iOS Safari tự zoom in */
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.3) !important;
    }

    /* ========================================================================= */
    /* MOBILE-FIRST RESPONSIVE OPTIMIZATION (ĐIỆN THOẠI DI ĐỘNG & TABLET)        */
    /* ========================================================================= */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2.2rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }
        .hero-top-badge {
            font-size: 0.7rem !important;
            padding: 4px 10px !important;
            margin-bottom: 0.4rem !important;
        }
        .main-title {
            font-size: 1.65rem !important;
            line-height: 1.25 !important;
            letter-spacing: -0.4px !important;
        }
        .main-subtitle {
            font-size: 0.86rem !important;
            line-height: 1.45 !important;
            margin-bottom: 1rem !important;
        }
        .feature-tags-row {
            gap: 6px !important;
            margin-bottom: 1.2rem !important;
        }
        .feature-tag-pill {
            font-size: 0.72rem !important;
            padding: 3px 8px !important;
            border-radius: 6px !important;
        }
        .glass-card {
            padding: 1.05rem 1.1rem !important;
            border-radius: 15px !important;
            margin-bottom: 1rem !important;
        }
        .step-number {
            width: 26px !important;
            height: 26px !important;
            font-size: 0.78rem !important;
            border-radius: 7px !important;
        }
        .step-title {
            font-size: 1rem !important;
        }
        .btn-render-hero button {
            min-height: 52px !important;
            font-size: 1.02rem !important;
            border-radius: 14px !important;
        }
        .phone-mockup-wrapper {
            border-width: 1.5px !important;
            border-radius: 20px !important;
            padding: 7px !important;
            max-width: 100% !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
        }
        .phone-notch {
            width: 75px !important;
            height: 12px !important;
            margin-bottom: 6px !important;
        }
        .phone-mockup-wrapper video,
        .phone-mockup-wrapper .stImage img {
            max-height: 480px !important;
            border-radius: 14px !important;
        }
        .meta-dashboard {
            padding: 0.55rem 0.4rem !important;
            margin-top: 0.6rem !important;
            margin-bottom: 0.8rem !important;
        }
        .meta-item-val {
            font-size: 0.82rem !important;
        }
        .meta-item-lbl {
            font-size: 0.65rem !important;
        }
        .btn-download button {
            min-height: 48px !important;
            font-size: 0.96rem !important;
        }
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
# BỘ CẤU HÌNH MỨC ĐỘ CHỐNG LOÁ QUANG HỌC
# ==============================================================================
ANTIGLARE_PRESETS = {
    "✨ Chuẩn Điện Ảnh (Khuyên dùng)": {
        "scrim": 175,
        "stroke": 1,
        "blur": 5.0,
        "desc": "Cân bằng hoàn hảo giữa độ trong trẻo của ảnh và độ nét của chữ.",
    },
    "🛡️ Siêu Chống Loá (Nền Sáng / Rất Chói)": {
        "scrim": 225,
        "stroke": 2,
        "blur": 6.0,
        "desc": "Tăng cường bóng đổ và gradient đáy, đặc trị ảnh ban ngày, trời nắng hoặc quán cafe nhiều đèn.",
    },
    "🌿 Tự Nhiên (Nền Tối / Ban Đêm)": {
        "scrim": 115,
        "stroke": 1,
        "blur": 3.5,
        "desc": "Lớp phủ mỏng nhẹ, giữ nguyên độ nguyên bản cho ảnh phố đêm, tranh tối.",
    },
}

# ==============================================================================
# BỘ CẤU HÌNH PHÔNG CHỮ NỔI BẬT TRÊN HÌNH
# ==============================================================================
FONT_PRESETS = {
    "☕ Be Vietnam Pro Bold (Mặc Định - Thanh Lịch Sài Gòn)": {
        "path": "assets/fonts/BeVietnamPro-Bold.ttf",
        "desc": "Phông chữ mặc định của kênh, nét thanh lịch, khoảng cách thoáng đãng, sâu lắng.",
    },
    "🔥 Montserrat Black (Siêu Đậm Nổi Bật)": {
        "path": "assets/fonts/Montserrat-Black.ttf",
        "desc": "Nét dày bản to, chữ cực kỳ bắt mắt và nổi bật trên mọi bức ảnh (chuẩn phong cách TikTok viral).",
    },
    "⚡ Montserrat Bold (Hiện Đại & Sắc Nét)": {
        "path": "assets/fonts/Montserrat-Bold.ttf",
        "desc": "Nét dày vừa vặn, hình khối hiện đại, thanh thoát và dễ đọc.",
    },
    "🎞️ Playfair Display Bold (Điện Ảnh Hoài Niệm)": {
        "path": "assets/fonts/PlayfairDisplay-Bold.ttf",
        "desc": "Font Serif có chân cổ điển, lãng mạn, rất hợp cho quote thơ, triết lý, hoài niệm.",
    },
    "🍃 Itim (Viết Tay Dễ Thương / Nhẹ Nhàng)": {
        "path": "assets/fonts/Itim-Regular.ttf",
        "desc": "Nét chữ bo tròn thân thiện, tự nhiên như trang nhật ký tâm sự.",
    },
}

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
if "antiglare_preset" not in st.session_state:
    st.session_state.antiglare_preset = "✨ Chuẩn Điện Ảnh (Khuyên dùng)"
if "font_preset" not in st.session_state:
    st.session_state.font_preset = "☕ Be Vietnam Pro Bold (Mặc Định - Thanh Lịch Sài Gòn)"
if "overlay_darkness" not in st.session_state:
    st.session_state.overlay_darkness = 50
if "preserve_linebreaks" not in st.session_state:
    st.session_state.preserve_linebreaks = True


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
        Tạo video tĩnh 18s TikTok chuẩn điện ảnh: Tự nhập câu quote, tự tải ảnh nền từ điện thoại/máy tính và xuất video 1080x1920 sắc nét không loá.
    </div>
    <div class="feature-tags-row">
        <div class="feature-tag-pill">📐 Khổ dọc 1080x1920 (9:16)</div>
        <div class="feature-tag-pill">⏱️ Thời lượng 18.0s TikTok</div>
        <div class="feature-tag-pill">🛡️ Chống Loá Đa Tầng (Anti-Glare)</div>
        <div class="feature-tag-pill">🎬 Ken Burns Cinematic Drift</div>
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
                    <span class="word-badge-ok">✓ Độ dài lý tưởng ({count} từ)</span>
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

        st.markdown("<b style='color: #38BDF8; font-size: 0.9rem; margin-top: 0.5rem; display: block;'>📐 Kiểu xuống dòng / ngắt đoạn:</b>", unsafe_allow_html=True)
        wrap_options = [
            "↵ Giữ ngắt dòng theo phím Enter (Mặc định - đúng từng câu/đoạn bạn gõ)",
            "🔄 Tự động nối liền & dàn đều (Chế độ cũ - dồn câu tự động)",
        ]
        chosen_wrap = st.radio(
            "Kiểu ngắt dòng chữ:",
            options=wrap_options,
            index=0 if st.session_state.preserve_linebreaks else 1,
            key="rb_wrap_mode",
            label_visibility="collapsed",
            help="Giữ nguyên dấu Enter xuống dòng của bạn, hoặc tự động nối liền thành một đoạn văn như trước.",
        )
        new_preserve = (chosen_wrap == wrap_options[0])
        if new_preserve != st.session_state.preserve_linebreaks:
            st.session_state.preserve_linebreaks = new_preserve
            st.session_state.rendered_video = None
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- BƯỚC 2: ẢNH NỀN ----------------
    with st.container():
        st.markdown(
            """
            <div class="glass-card">
                <div class="step-header">
                    <div class="step-number">02</div>
                    <div class="step-title">Tải Ảnh Nền Từ Điện Thoại / Máy Tính</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        up_file = st.file_uploader(
            "Chọn file ảnh từ thư viện (.jpg, .png, .webp):",
            type=["jpg", "jpeg", "png", "webp", "jfif", "bmp"],
            key="file_bg_uploader",
            help="Hệ thống tự động canh giữa và crop chuẩn dọc 9:16 (1080x1920).",
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

    # ---------------- TUỲ CHỌN HIỂN THỊ, ĐỘ TỐI NỀN, PHÔNG CHỮ & CHỐNG LOÁ ----------------
    with st.expander("⚙️ Độ tối nền, Phông chữ & Chữ ký video", expanded=True):
        st.markdown("<b style='color: #38BDF8; font-size: 0.92rem;'>🌙 Độ tối hình nền (Dark Overlay):</b>", unsafe_allow_html=True)
        overlay_val = st.slider(
            "Mức độ phủ tối hình nền:",
            min_value=0,
            max_value=90,
            value=st.session_state.overlay_darkness,
            step=5,
            format="%d%%",
            key="slider_dark_overlay",
            help="Dìm tối hình nền để câu quote màu trắng nổi bật rõ nét và có chiều sâu.",
        )
        if overlay_val != st.session_state.overlay_darkness:
            st.session_state.overlay_darkness = overlay_val
            st.session_state.rendered_video = None
        st.caption(f"💡 Đang phủ tối: **{st.session_state.overlay_darkness}%** (Mặc định 50% giúp chữ trắng nổi bật tối đa).")

        st.markdown("<b style='color: #38BDF8; font-size: 0.9rem;'>🔤 Phông chữ hiển thị:</b>", unsafe_allow_html=True)
        font_names = list(FONT_PRESETS.keys())
        default_font_idx = font_names.index(st.session_state.font_preset) if st.session_state.font_preset in font_names else 0
        selected_font = st.selectbox(
            "Chọn phông chữ:",
            options=font_names,
            index=default_font_idx,
            key="sb_font_select",
            label_visibility="collapsed",
        )
        if selected_font != st.session_state.font_preset:
            st.session_state.font_preset = selected_font
            st.session_state.rendered_video = None

        st.caption(f"ℹ️ {FONT_PRESETS[selected_font]['desc']}")

        st.markdown("<b style='color: #38BDF8; font-size: 0.9rem;'>🛡️ Chế độ chống loá chữ:</b>", unsafe_allow_html=True)
        preset_names = list(ANTIGLARE_PRESETS.keys())
        default_idx = preset_names.index(st.session_state.antiglare_preset) if st.session_state.antiglare_preset in preset_names else 0
        selected_preset = st.selectbox(
            "Chọn mức độ chống loá chữ:",
            options=preset_names,
            index=default_idx,
            key="sb_antiglare_select",
            label_visibility="collapsed",
        )
        if selected_preset != st.session_state.antiglare_preset:
            st.session_state.antiglare_preset = selected_preset
            st.session_state.rendered_video = None

        st.caption(f"ℹ️ {ANTIGLARE_PRESETS[selected_preset]['desc']}")

        col_opt1, col_opt2 = st.columns([1.3, 1.0])
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
                "Bật Scrim chống loá",
                value=st.session_state.enable_antiglare,
                help="Bật lớp gradient chuyển tối ở chân chữ để luôn nổi bật trên nền.",
            )

    st.write("")

    # Lấy thông số chống loá và font chữ hiện tại
    active_cfg = ANTIGLARE_PRESETS.get(
        st.session_state.antiglare_preset,
        ANTIGLARE_PRESETS["✨ Chuẩn Điện Ảnh (Khuyên dùng)"],
    )
    active_font = FONT_PRESETS.get(
        st.session_state.font_preset,
        FONT_PRESETS["☕ Be Vietnam Pro Bold (Mặc Định - Thanh Lịch Sài Gòn)"],
    )

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
            timestamp = int(time.time())
            out_vid = out_folder / f"tiktok_video_{timestamp}.mp4"
            out_txt = out_folder / f"tiktok_video_{timestamp}.txt"

            # Tự động lưu kèm file .txt chứa câu quote trên video & hashtag viral
            sig_tag = (st.session_state.signature or "saigonbac").replace("@", "").strip()
            trending_hashtags = f"#{sig_tag} #tamtrang #suyngam #trietlycuocsong #cuocsong #xuhuong #fyp #viral #quotesvn #chill"
            full_caption = f"{st.session_state.quote_text.strip()}\n\n{trending_hashtags}"
            try:
                with open(out_txt, "w", encoding="utf-8") as f_txt:
                    f_txt.write(full_caption)
            except Exception as txt_err:
                logger.warning(f"Lỗi ghi file txt caption: {txt_err}")

            with st.spinner("Đang ghép typography chống loá và render video 18.0s chuẩn TikTok..."):
                try:
                    render_18s_video(
                        image_path=bg_target,
                        quote=st.session_state.quote_text,
                        output_path=out_vid,
                        duration=18.0,
                        overlay_opacity=st.session_state.overlay_darkness / 100.0,
                        signature=st.session_state.signature or "saigonbac",
                        enable_gradient_scrim=st.session_state.enable_antiglare,
                        scrim_max_alpha=active_cfg["scrim"],
                        shadow_blur_radius=active_cfg["blur"],
                        stroke_width=active_cfg["stroke"],
                        font_path=active_font["path"],
                        preserve_linebreaks=st.session_state.preserve_linebreaks,
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
            <div class="step-title" style="font-size: 1.1rem;">Khung Xem Trước Trực Quan</div>
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

                    # Làm dịu nền nhẹ tương đương FFmpeg để ảnh trên live preview không bị chói
                    bg_rgb = bg_rgba.convert("RGB")
                    enhancer_b = ImageEnhance.Brightness(bg_rgb)
                    bg_graded = enhancer_b.enhance(0.90)
                    enhancer_c = ImageEnhance.Contrast(bg_graded)
                    bg_base = enhancer_c.enhance(1.08).convert("RGBA")

                    # Phủ lớp tối theo đúng thanh trượt (mặc định 50%)
                    dark_alpha = int(255 * (st.session_state.overlay_darkness / 100.0))
                    if dark_alpha > 0:
                        dark_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, dark_alpha))
                        bg_ready = Image.alpha_composite(bg_base, dark_layer)
                    else:
                        bg_ready = bg_base

                    active_cfg = ANTIGLARE_PRESETS.get(
                        st.session_state.antiglare_preset,
                        ANTIGLARE_PRESETS["✨ Chuẩn Điện Ảnh (Khuyên dùng)"],
                    )
                    active_font = FONT_PRESETS.get(
                        st.session_state.font_preset,
                        FONT_PRESETS["☕ Be Vietnam Pro Bold (Mặc Định - Thanh Lịch Sài Gòn)"],
                    )

                    text_overlay = create_quote_overlay(
                        quote=st.session_state.quote_text,
                        signature=st.session_state.signature or "saigonbac",
                        enable_gradient_scrim=st.session_state.enable_antiglare,
                        scrim_max_alpha=active_cfg["scrim"],
                        shadow_blur_radius=active_cfg["blur"],
                        stroke_width=active_cfg["stroke"],
                        font_path=active_font["path"],
                        preserve_linebreaks=st.session_state.preserve_linebreaks,
                    )
                    preview_composite = Image.alpha_composite(bg_ready, text_overlay)
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
            <div style="height: 440px; display: flex; align-items: center; justify-content: center; color: #64748B; text-align: center; padding: 1.5rem;">
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
        st.caption(f"📁 Video: `{rendered_vid}`")

        # ---------------- KHUNG 1-CLICK COPY CAPTION & HASHTAGS ĐĂNG TIKTOK ----------------
        sig_tag = (st.session_state.signature or "saigonbac").replace("@", "").strip()
        trending_hashtags = f"#{sig_tag} #tamtrang #suyngam #trietlycuocsong #cuocsong #xuhuong #fyp #viral #quotesvn #chill"
        full_caption = f"{st.session_state.quote_text.strip()}\n\n{trending_hashtags}"

        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.88); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 14px; padding: 14px 16px; margin-top: 14px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.5);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: #38BDF8; font-weight: 700; font-size: 0.95rem;">📋 Caption & Hashtags Đăng TikTok</span>
                    <span style="font-size: 0.76rem; color: #7DD3FC; background: rgba(56, 189, 248, 0.15); padding: 3px 8px; border-radius: 6px; font-weight: 600;">1-Click Copy 📋</span>
                </div>
                <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 8px;">
                    Đã tạo sẵn câu quote ở trên và bộ hashtag viral ở dưới. Bấm biểu tượng copy ở góc trên bên phải khung dưới để dán ngay lên TikTok:
                </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(full_caption, language="")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div style="text-align: center; color: #64748B; font-size: 0.82rem; margin-top: 0.8rem;">
                💡 Chữ trên khung preview được cập nhật theo thời gian thực (Realtime Live Preview).
            </div>
            """,
            unsafe_allow_html=True,
        )
        if quote_ready:
            with st.expander("📋 Xem trước Caption & Hashtags sẽ đăng", expanded=False):
                sig_tag = (st.session_state.signature or "saigonbac").replace("@", "").strip()
                trending_hashtags = f"#{sig_tag} #tamtrang #suyngam #trietlycuocsong #cuocsong #xuhuong #fyp #viral #quotesvn #chill"
                full_caption = f"{st.session_state.quote_text.strip()}\n\n{trending_hashtags}"
                st.code(full_caption, language="")
