from __future__ import annotations

import gc
import json
import logging
import os
import shutil
import sys
import threading
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

import importlib
import inspect

import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import modules.video_renderer
try:
    importlib.reload(modules.video_renderer)
except Exception:
    pass

from modules.video_engine import probe_video_metadata
from modules.video_renderer import create_quote_overlay, render_18s_video, render_any_media_quote, extract_video_frame, determine_media_duration, get_media_duration_info

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="TikTok 10s Quote Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuoteStudio")


@st.cache_resource
def get_render_lock() -> threading.Lock:
    """Lock toàn cục ngăn ngừa chạy đồng thời nhiều tiến trình FFmpeg làm tràn RAM server."""
    return threading.Lock()


RENDER_LOCK = get_render_lock()

# ==============================================================================
# ULTRA-PREMIUM AESTHETIC CSS (MOBILE-FIRST OPTIMIZED & GLASSMORPHISM)
# ==============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #09090B !important;
        background-image: 
            radial-gradient(circle at 12% 10%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 88% 18%, rgba(14, 165, 233, 0.07) 0%, transparent 45%),
            radial-gradient(circle at 50% 90%, rgba(99, 102, 241, 0.05) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #F4F4F5;
    }

    /* Đảm bảo thanh điều hướng Streamlit không che khuất Header */
    header[data-testid="stHeader"] {
        background: rgba(9, 9, 11, 0.75) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
    }

    /* Container chuẩn không gian, tránh bị che bởi thanh điều hướng Streamlit */
    .block-container {
        padding-top: 4.2rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1360px !important;
    }

    /* Studio Header Pro Bar */
    .studio-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.1rem;
        background: rgba(18, 18, 23, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
    }
    .studio-brand {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .studio-title {
        font-size: 1.12rem;
        font-weight: 800;
        letter-spacing: -0.3px;
        color: #FFFFFF;
    }
    .studio-badge-pro {
        font-size: 0.65rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
        color: #FFFFFF;
        padding: 2px 7px;
        border-radius: 6px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        vertical-align: middle;
    }
    .studio-status {
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: 0.78rem;
        color: #A1A1AA;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
        animation: pulse-dot 2.2s infinite ease-in-out;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Cards cấu trúc Studio Pro */
    .glass-card {
        background: rgba(18, 18, 23, 0.75);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.15rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.35);
        box-shadow: 0 6px 25px -3px rgba(99, 102, 241, 0.1);
    }

    /* Step Badge Metallic */
    .step-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.65rem;
    }
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        background: #27272A;
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #F4F4F5;
        font-size: 0.76rem;
        font-weight: 800;
        border-radius: 7px;
    }
    .step-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #F4F4F5;
        letter-spacing: -0.2px;
    }

    /* Word Counter Badge */
    .word-counter-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 6px;
        padding: 5px 10px;
        border-radius: 8px;
        background: #18181B;
        border: 1px solid rgba(255, 255, 255, 0.06);
        font-size: 0.8rem;
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
        background: linear-gradient(135deg, #4F46E5 0%, #4338CA 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        font-size: 1.08rem !important;
        font-weight: 800 !important;
        min-height: 54px !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 18px rgba(79, 70, 229, 0.4) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        letter-spacing: 0.2px !important;
    }
    .btn-render-hero button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.6) !important;
        border-color: rgba(255, 255, 255, 0.35) !important;
    }
    .btn-render-hero button:active {
        transform: scale(0.98) !important;
    }

    /* Phone Mockup Frame cho Live Preview & Video */
    .phone-mockup-wrapper {
        background: #000000;
        border: 1.5px solid rgba(255, 255, 255, 0.12);
        border-radius: 22px;
        padding: 8px;
        box-shadow: 0 15px 45px -10px rgba(0, 0, 0, 0.85);
        position: relative;
        max-width: 440px;
        margin: 0 auto;
    }
    .phone-notch {
        width: 80px;
        height: 14px;
        background: #18181B;
        border-radius: 0 0 10px 10px;
        margin: 0 auto 6px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
    }
    .phone-lens {
        width: 6px;
        height: 6px;
        background: #27272A;
        border-radius: 50%;
    }
    .phone-speaker {
        width: 25px;
        height: 3px;
        background: #3F3F46;
        border-radius: 3px;
    }

    .phone-mockup-wrapper video,
    .phone-mockup-wrapper .stImage img {
        border-radius: 14px !important;
        max-height: 520px !important;
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
        object-fit: cover !important;
    }

    /* Dashboard thông số */
    .meta-dashboard {
        display: flex;
        justify-content: space-around;
        background: #121217;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 0.65rem;
        margin-top: 0.7rem;
        margin-bottom: 0.85rem;
        text-align: center;
    }
    .meta-item-val {
        font-size: 0.9rem;
        font-weight: 800;
        color: #818CF8;
        font-family: 'JetBrains Mono', monospace;
    }
    .meta-item-lbl {
        font-size: 0.7rem;
        color: #A1A1AA;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* Download button */
    .btn-download button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.02rem !important;
        min-height: 50px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 18px rgba(5, 150, 105, 0.4) !important;
        transition: transform 0.2s !important;
    }
    .btn-download button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.55) !important;
    }

    /* Inputs tinh chỉnh */
    .stTextArea textarea, .stTextInput input, .stSelectbox [data-baseweb="select"] {
        background-color: #121217 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #F4F4F5 !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        transition: border-color 0.2s !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #6366F1 !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.25) !important;
    }

    /* ========================================================================= */
    /* RESPONSIVE MOBILE TỐI ƯU                                                  */
    /* ========================================================================= */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 3.2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
        }
        .studio-header {
            padding: 0.6rem 0.85rem !important;
            margin-bottom: 0.75rem !important;
        }
        .studio-title {
            font-size: 0.98rem !important;
        }
        .studio-status {
            font-size: 0.7rem !important;
        }
        .glass-card {
            padding: 0.85rem 0.9rem !important;
            border-radius: 12px !important;
            margin-bottom: 0.75rem !important;
        }
        .step-header {
            margin-bottom: 0.45rem !important;
        }
        .step-number {
            width: 24px !important;
            height: 24px !important;
            font-size: 0.72rem !important;
        }
        .step-title {
            font-size: 0.95rem !important;
        }
        .btn-render-hero button {
            min-height: 50px !important;
            font-size: 1rem !important;
            border-radius: 12px !important;
        }
        .phone-mockup-wrapper {
            border-width: 1px !important;
            border-radius: 16px !important;
            padding: 4px !important;
            max-width: 100% !important;
        }
        .phone-notch {
            display: none !important;
        }
        .phone-mockup-wrapper video,
        .phone-mockup-wrapper .stImage img {
            max-height: 460px !important;
            border-radius: 12px !important;
            width: 100% !important;
        }
        .meta-dashboard {
            padding: 0.45rem 0.3rem !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.65rem !important;
        }
        .meta-item-val {
            font-size: 0.78rem !important;
        }
        .meta-item-lbl {
            font-size: 0.6rem !important;
        }
        .btn-download button {
            min-height: 48px !important;
            font-size: 0.95rem !important;
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



def get_tiktok_safe_zone_overlay(size=(1080, 1920)) -> Image.Image:
    """
    Tạo lớp phủ bán trong suốt mô phỏng giao diện chuẩn của TikTok:
    - Vùng Safe-Zone an toàn tuyệt đối (không bị các nút TikTok che khuất)
    - Mô phỏng các nút: Avatar, Tim, Bình luận, Bookmark, Chia sẻ, Đĩa nhạc và Caption đáy.
    """
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Khung Safe Zone (vùng an toàn 100% cho Typography)
    box_l, box_r, box_t, box_b = 85, 930, 240, 1560

    # Corner brackets (Góc căn lề chuyên nghiệp)
    c_len = 40
    c_color = (99, 102, 241, 180)  # Indigo
    # Top-Left
    draw.line([(box_l, box_t), (box_l + c_len, box_t)], fill=c_color, width=3)
    draw.line([(box_l, box_t), (box_l, box_t + c_len)], fill=c_color, width=3)
    # Top-Right
    draw.line([(box_r, box_t), (box_r - c_len, box_t)], fill=c_color, width=3)
    draw.line([(box_r, box_t), (box_r, box_t + c_len)], fill=c_color, width=3)
    # Bottom-Left
    draw.line([(box_l, box_b), (box_l + c_len, box_b)], fill=c_color, width=3)
    draw.line([(box_l, box_b), (box_l, box_b - c_len)], fill=c_color, width=3)
    # Bottom-Right
    draw.line([(box_r, box_b), (box_r - c_len, box_b)], fill=c_color, width=3)
    draw.line([(box_r, box_b), (box_r, box_b - c_len)], fill=c_color, width=3)

    # Đường viền Safe-Zone mờ
    border_color = (99, 102, 241, 55)
    draw.rectangle([box_l, box_t, box_r, box_b], outline=border_color, width=1)

    # 2. Mô phỏng icon TikTok cột phải (Semi-transparent white)
    ui_color = (255, 255, 255, 110)
    # Avatar
    draw.ellipse([950, 780, 1020, 850], outline=ui_color, width=2)
    draw.ellipse([975, 840, 995, 860], fill=(239, 68, 68, 180))  # Nút follow đỏ
    # Heart
    draw.ellipse([960, 920, 1010, 970], outline=ui_color, width=2)
    # Comment
    draw.ellipse([960, 1050, 1010, 1100], outline=ui_color, width=2)
    # Bookmark
    draw.ellipse([960, 1180, 1010, 1230], outline=ui_color, width=2)
    # Share
    draw.ellipse([960, 1310, 1010, 1360], outline=ui_color, width=2)
    # Music disc
    draw.ellipse([960, 1450, 1010, 1500], outline=ui_color, width=2)
    draw.ellipse([980, 1470, 990, 1480], fill=ui_color)

    # 3. Mô phỏng Bottom Caption & Username
    draw.rectangle([85, 1620, 340, 1642], fill=(255, 255, 255, 85))   # Username @saigonbac
    draw.rectangle([85, 1660, 680, 1678], fill=(255, 255, 255, 60))   # Caption line 1
    draw.rectangle([85, 1695, 480, 1710], fill=(255, 255, 255, 50))   # Sound track name

    # Top Tabs: Đang Follow | Dành cho bạn
    draw.rectangle([450, 115, 630, 132], fill=(255, 255, 255, 85))

    return overlay

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
if "text_align" not in st.session_state:
    st.session_state.text_align = "center"
if "quote_font_size" not in st.session_state:
    st.session_state.quote_font_size = 42
if "show_safe_zone" not in st.session_state:
    st.session_state.show_safe_zone = False


# ==============================================================================
# HEADER & HERO SECTION
# ==============================================================================
st.markdown(
    """
    <div class="studio-header">
        <div class="studio-brand">
            <span style="font-size: 1.25rem;">🎬</span>
            <span class="studio-title">QUOTE STUDIO <span class="studio-badge-pro">PRO</span></span>
        </div>
        <div class="studio-status">
            <span class="status-dot"></span> 9:16 DYNAMIC ENGINE
        </div>
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
            height=85,
            key="txt_quote_input",
            label_visibility="collapsed",
        )
        if input_quote != st.session_state.quote_text:
            st.session_state.quote_text = input_quote
            st.session_state.rendered_video = None

        # Đếm từ trực quan tinh gọn
        current_words = input_quote.strip().split() if input_quote.strip() else []
        count = len(current_words)
        if 15 <= count <= 26:
            st.markdown(
                f"""
                <div class="word-counter-box">
                    <span class="word-badge-ok">✓ Lý tưởng ({count} từ)</span>
                    <span style="color: #94A3B8; font-size: 0.78rem;">Chuẩn nhịp đọc TikTok</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif count > 0:
            st.markdown(
                f"""
                <div class="word-counter-box">
                    <span class="word-badge-warn">ℹ️ {count} từ</span>
                    <span style="color: #94A3B8; font-size: 0.78rem;">Khuyên dùng 15 - 26 từ</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        new_preserve = st.checkbox(
            "↵ Giữ ngắt dòng theo phím Enter (Gõ gì hiện nấy)",
            value=st.session_state.preserve_linebreaks,
            key="chk_preserve_linebreaks",
            help="Bật: Giữ nguyên các dấu Enter xuống dòng bạn gõ. Tắt: Tự động dồn câu liên tục.",
        )
        if new_preserve != st.session_state.preserve_linebreaks:
            st.session_state.preserve_linebreaks = new_preserve
            st.session_state.rendered_video = None
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- BƯỚC 2: ẢNH HOẶC VIDEO NỀN ----------------
    with st.container():
        st.markdown(
            """
            <div class="glass-card">
                <div class="step-header">
                    <div class="step-number">02</div>
                    <div class="step-title">Tải Ảnh Hoặc Video Nền Từ Thiết Bị</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        up_file = st.file_uploader(
            "Chọn file ảnh hoặc video từ máy tính (.jpg, .png, .mp4, .mov...):",
            type=["jpg", "jpeg", "png", "webp", "jfif", "bmp", "mp4", "mov", "webm", "avi", "mkv"],
            key="file_bg_uploader",
            help="Hệ thống tự động canh giữa và crop chuẩn dọc 9:16 (1080x1920), video tự động khớp 10 giây.",
        )

        if up_file is not None:
            if up_file.name != st.session_state.get("last_uploaded_bg_name"):
                try:
                    temp_dir = Path("temp")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    file_ext = Path(up_file.name).suffix.lower() or ".jpg"
                    unique_bg_path = temp_dir / f"bg_{int(time.time() * 1000)}{file_ext}"
                    with open(unique_bg_path, "wb") as f_out:
                        shutil.copyfileobj(up_file, f_out)
                    gc.collect()

                    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
                    if file_ext in video_exts:
                        st.session_state.bg_image = str(unique_bg_path)
                        st.session_state.last_uploaded_bg_name = up_file.name
                        st.session_state.rendered_video = None
                        st.toast(f"Đã nạp video nền: {up_file.name}", icon="🎬")
                    else:
                        crop_path = crop_image_to_tiktok_portrait(unique_bg_path)
                        st.session_state.bg_image = str(crop_path)
                        st.session_state.last_uploaded_bg_name = up_file.name
                        st.session_state.rendered_video = None
                        st.toast(f"Đã nạp và chuẩn hóa ảnh: {up_file.name}", icon="📸")
                except Exception as e:
                    st.error(f"Lỗi khi xử lý file tải lên: {e}")
        else:
            if st.session_state.get("last_uploaded_bg_name") is not None:
                st.session_state.last_uploaded_bg_name = None
                st.session_state.bg_image = None
                st.session_state.rendered_video = None

        if st.session_state.get("last_uploaded_bg_name"):
            col_cur, col_del = st.columns([3, 1])
            is_vid = Path(st.session_state.get("last_uploaded_bg_name", "")).suffix.lower() in [".mp4", ".mov", ".webm", ".avi", ".mkv"]
            icon_badge = "🎬 Video:" if is_vid else "📸 Ảnh:"
            with col_cur:
                st.markdown(f"<span style='color: #38BDF8; font-size: 0.88rem;'>{icon_badge} <b>{st.session_state.last_uploaded_bg_name}</b></span>", unsafe_allow_html=True)
            with col_del:
                if st.button("🗑️ Đổi file", key="btn_del_bg", use_container_width=True):
                    st.session_state.last_uploaded_bg_name = None
                    st.session_state.bg_image = None
                    st.session_state.rendered_video = None
                    st.rerun()

            # Hiển thị thông tin nhận diện thời lượng động
            if st.session_state.get("bg_image") and Path(st.session_state.bg_image).exists():
                dur_info_b2 = get_media_duration_info(st.session_state.bg_image)
                badge_bg = "rgba(56, 189, 248, 0.12)" if not dur_info_b2["is_video"] else "rgba(168, 85, 247, 0.15)"
                badge_border = "#38BDF8" if not dur_info_b2["is_video"] else "#C084FC"
                badge_text_color = "#7DD3FC" if not dur_info_b2["is_video"] else "#E9D5FF"
                st.markdown(
                    f"<div style='margin-top: 8px; padding: 7px 12px; background: {badge_bg}; border-left: 3px solid {badge_border}; border-radius: 6px; font-size: 0.85rem; color: {badge_text_color}; font-weight: 500;'>"
                    f"{dur_info_b2['badge_text']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # Lấy thông số chống loá và font chữ hiện tại
    active_cfg = ANTIGLARE_PRESETS.get(
        st.session_state.antiglare_preset,
        ANTIGLARE_PRESETS["✨ Chuẩn Điện Ảnh (Khuyên dùng)"],
    )
    active_font = FONT_PRESETS.get(
        st.session_state.font_preset,
        FONT_PRESETS["☕ Be Vietnam Pro Bold (Mặc Định - Thanh Lịch Sài Gòn)"],
    )


    # ---------------- NÚT HÀNH ĐỘNG HERO (ĐẶT NGAY DƯỚI BƯỚC 2 - TỐI ƯU MOBILE-FIRST) ----------------
    if st.session_state.get("bg_image") and Path(st.session_state.bg_image).exists():
        media_dur_info = get_media_duration_info(st.session_state.bg_image)
        btn_label = f"✨ XUẤT VIDEO TIKTOK {media_dur_info['btn_suffix']} CHUẨN HD"
        target_video_duration = media_dur_info["target_duration"]
    else:
        btn_label = "✨ XUẤT VIDEO TIKTOK (10.0S) CHUẨN HD"
        target_video_duration = 10.0

    st.markdown('<div class="btn-render-hero">', unsafe_allow_html=True)
    btn_generate = st.button(btn_label, type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Thông báo trạng thái nhanh sau khi render trên Mobile
    if st.session_state.get("rendered_video") and Path(st.session_state.rendered_video).exists():
        st.markdown(
            """
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.5); border-radius: 10px; padding: 8px 12px; margin-top: 6px; margin-bottom: 10px; text-align: center; color: #6EE7B7; font-size: 0.88rem; font-weight: 700;">
                🎉 Video đã tạo xong! Xem & tải xuống ngay bên dưới ⬇️
            </div>
            """,
            unsafe_allow_html=True,
        )

    if btn_generate:
        bg_target = st.session_state.bg_image
        if not bg_target or not Path(bg_target).exists():
            st.error("Chưa có ảnh nền! Vui lòng tải một file ảnh hoặc video từ máy tính ở Bước 2.")
        elif not st.session_state.quote_text.strip():
            st.error("Câu quote đang trống! Vui lòng nhập quote ở Bước 1.")
        elif not RENDER_LOCK.acquire(blocking=False):
            st.warning("⚠️ Máy chủ đang xử lý render một video khác! Vui lòng chờ 15-20 giây để hoàn tất, tránh bấm liên tục gây quá tải bộ nhớ.", icon="⏳")
        else:
            try:
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

                with st.spinner(f"Đang ghép typography chống loá và render video {target_video_duration:.1f}s chuẩn TikTok..."):
                    try:
                        render_args = {
                            "media_path": bg_target,
                            "quote": st.session_state.quote_text,
                            "output_path": out_vid,
                            "duration": target_video_duration,
                            "overlay_opacity": st.session_state.overlay_darkness / 100.0,
                            "signature": st.session_state.signature or "saigonbac",
                            "enable_gradient_scrim": st.session_state.enable_antiglare,
                            "scrim_max_alpha": active_cfg["scrim"],
                            "shadow_blur_radius": active_cfg["blur"],
                            "stroke_width": active_cfg["stroke"],
                            "font_path": active_font["path"],
                            "text_align": st.session_state.text_align,
                            "font_size": st.session_state.quote_font_size,
                            "preserve_linebreaks": st.session_state.preserve_linebreaks,
                        }

                        render_any_media_quote(**render_args)
                        st.session_state.rendered_video = str(out_vid)
                        st.toast(f"Tạo video {target_video_duration:.1f}s hoàn tất thành công 100%!", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi render video: {e}")
            finally:
                RENDER_LOCK.release()
                gc.collect()

    # ---------------- TUỲ CHỌN NÂNG CAO (MẶC ĐỊNH THU GỌN EXPANDED=FALSE ĐỂ TIẾT KIỆM KHÔNG GIAN MOBILE) ----------------
    with st.expander("⚙️ Tùy Chỉnh Nâng Cao (Cỡ chữ, Font, Độ tối nền, Chống loá)", expanded=False):
        col_align, col_size = st.columns([1.1, 1.0])
        with col_align:
            st.markdown("<b style='color: #38BDF8; font-size: 0.9rem;'>🎯 Căn lề chữ (Alignment):</b>", unsafe_allow_html=True)
            align_map = {
                "🎯 Trung tâm khung hình (Mặc định)": "center",
                "➡️ Sang phải (Phía dưới)": "right",
                "⬅️ Sang trái (Phía dưới)": "left",
            }
            align_labels = list(align_map.keys())
            cur_label = next((k for k, v in align_map.items() if v == st.session_state.text_align), align_labels[0])
            sel_label = st.selectbox(
                "Chọn vị trí căn lề:",
                options=align_labels,
                index=align_labels.index(cur_label),
                key="sb_align_select",
                label_visibility="collapsed",
            )
            chosen_align = align_map[sel_label]
            if chosen_align != st.session_state.text_align:
                st.session_state.text_align = chosen_align
                st.session_state.rendered_video = None

        with col_size:
            st.markdown("<b style='color: #38BDF8; font-size: 0.9rem;'>📏 Cỡ chữ (Font size):</b>", unsafe_allow_html=True)
            sel_font_size = st.slider(
                "Cỡ chữ câu quote:",
                min_value=28,
                max_value=72,
                value=int(st.session_state.quote_font_size),
                step=2,
                format="%d px",
                key="slider_quote_font_size",
                label_visibility="collapsed",
                help="Cỡ chữ hiển thị của câu quote. Mặc định là 42px.",
            )
            if sel_font_size != st.session_state.quote_font_size:
                st.session_state.quote_font_size = sel_font_size
                st.session_state.rendered_video = None

        st.caption(f"💡 Đang chọn: Căn **{sel_label}**, cỡ chữ **{st.session_state.quote_font_size}px**")

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


# ==============================================================================
# CỘT PHẢI: PHONE MOCKUP XEM TRƯỚC (LIVE PREVIEW) & VIDEO THÀNH PHẨM
# ==============================================================================
with col_preview:
    col_prev_t, col_prev_safe = st.columns([1.2, 1.0])
    with col_prev_t:
        st.markdown('<div class="step-title" style="font-size: 1.02rem; padding-top: 4px;">Khung Xem Trước 9:16</div>', unsafe_allow_html=True)
    with col_prev_safe:
        st.session_state.show_safe_zone = st.toggle(
            "📐 TikTok Safe-Zone",
            value=st.session_state.show_safe_zone,
            help="Bật/Tắt lưới mô phỏng các icon TikTok (Like, Comment, Caption) để đảm bảo chữ không bị che.",
            key="tg_safe_zone",
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
        def _get_safe_bg_preview(path_target: Path | str) -> Image.Image:
            p_obj = Path(path_target)
            v_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
            if p_obj.suffix.lower() in v_exts:
                f_path = extract_video_frame(p_obj, timestamp_sec=1.0)
                return Image.open(f_path).convert("RGBA")
            return Image.open(p_obj).convert("RGBA")

        if quote_ready:
            try:
                raw_bg = _get_safe_bg_preview(bg_img)
                bg_rgba = raw_bg
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

                overlay_args = {
                    "quote": st.session_state.quote_text,
                    "signature": st.session_state.signature or "saigonbac",
                    "enable_gradient_scrim": st.session_state.enable_antiglare,
                    "scrim_max_alpha": active_cfg["scrim"],
                    "shadow_blur_radius": active_cfg["blur"],
                    "stroke_width": active_cfg["stroke"],
                    "font_path": active_font["path"],
                    "text_align": st.session_state.text_align,
                    "font_size": st.session_state.quote_font_size,
                    "preserve_linebreaks": st.session_state.preserve_linebreaks,
                }

                text_overlay = create_quote_overlay(**overlay_args)
                preview_composite = Image.alpha_composite(bg_ready, text_overlay)
                if st.session_state.get("show_safe_zone", False):
                    sz_ov = get_tiktok_safe_zone_overlay((1080, 1920))
                    preview_composite = Image.alpha_composite(preview_composite, sz_ov)
                st.image(preview_composite.convert("RGB"), use_container_width=True)
            except Exception as ex:
                logger.warning(f"Lỗi live preview: {ex}")
                try:
                    fb_img = _get_safe_bg_preview(bg_img)
                    st.image(fb_img.convert("RGB"), use_container_width=True)
                except Exception:
                    pass
        else:
            try:
                fb_img = _get_safe_bg_preview(bg_img)
                if st.session_state.get("show_safe_zone", False):
                    fb_img = fb_img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    sz_ov = get_tiktok_safe_zone_overlay((1080, 1920))
                    fb_img = Image.alpha_composite(fb_img, sz_ov)
                st.image(fb_img.convert("RGB"), use_container_width=True)
            except Exception:
                pass
    else:
        st.markdown(
            """
            <div style="height: 440px; display: flex; align-items: center; justify-content: center; color: #64748B; text-align: center; padding: 1.5rem;">
                <div>
                    <div style="font-size: 2.8rem; margin-bottom: 0.8rem;">📱</div>
                    <b style="color: #94A3B8;">Chưa có ảnh nền</b><br>
                    <span style="font-size: 0.85rem;">Tải ảnh hoặc video ở Bước 2 để hiển thị chữ trực tiếp trên khung.</span>
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
                    <div class="meta-item-val">{meta.get('duration', 10.0)}s</div>
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
