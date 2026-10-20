from __future__ import annotations

"""
Ứng dụng Web Streamlit: TikTok Multi-Channel Studio (app.py)
Phân tách độc lập 2 kênh TikTok:
1. Kênh 1 (saigonbac): Video tĩnh 18s từ Ảnh Aesthetic + Typography tâm sự đêm "buồn một chút", chữ ký saigonbac, lưu tại output/saigonbac/.
2. Kênh 2 (Kênh mới): Video chuyển động từ Video B-Roll + Typography triết lý / bản lĩnh / động lực, chữ ký tùy chỉnh, lưu tại output/kenh_moi/.
"""

import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Đảm bảo thư mục gốc dự án luôn nằm đầu sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
try:
    os.chdir(project_root)
except Exception:
    pass

import streamlit as st
from dotenv import load_dotenv

from modules.pixabay_fetcher import (
    DEFAULT_DARK_KEYWORDS,
    QUICK_THEMES_VI,
    fetch_pixabay_image,
    search_pixabay_images,
    download_and_crop_pixabay_image,
    fetch_dark_moody_image_for_quote,
    resize_and_crop_to_tiktok,
)
from modules.picsum_fetcher import fetch_picsum_image, get_picsum_gallery
from modules.quote_manager import (
    get_all_categories,
    get_random_quote,
    load_all_quotes,
    suggest_keywords_from_quote,
)
from modules.quote_gen import CHANNEL_CATEGORIES, generate_quote, review_viral_potential
from modules.video_renderer import render_18s_video, render_video_from_footage
from modules.video_engine import generate_quote_preview_image, probe_video_metadata
from modules.video_fetcher import (
    VIDEO_QUICK_THEMES_VI,
    search_pixabay_videos,
    download_video_stream,
    fetch_pixabay_video_quick,
    get_local_footages,
    extract_video_frame,
)
from modules.history_db import init_db

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TikTok_MultiChannel_Tool")

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="TikTok Multi-Channel Studio (saigonbac & Kênh Mới)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS phong cách Aesthetic Dark Mode
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-tap-highlight-color: transparent;
    }
    
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        .main-header {
            font-size: 1.45rem !important;
            line-height: 1.3 !important;
        }
        .sub-header {
            font-size: 0.82rem !important;
            margin-bottom: 0.8rem !important;
        }
        .stButton>button {
            min-height: 48px !important;
            font-size: 15px !important;
        }
    }

    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #38BDF8 50%, #F43F5E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-header {
        color: #94A3B8;
        font-size: 0.92rem;
        margin-bottom: 1.0rem;
    }

    .channel-banner {
        border-radius: 12px;
        padding: 0.8rem 1.1rem;
        margin-bottom: 1.2rem;
        font-size: 0.9rem;
    }
    .channel-banner-sg {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #E2E8F0;
    }
    .channel-banner-new {
        background: rgba(40, 20, 40, 0.6);
        border: 1px solid rgba(244, 63, 94, 0.35);
        color: #FEE2E2;
    }

    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        min-height: 46px;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        touch-action: manipulation;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    
    .btn-create-sg button {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4) !important;
    }

    .btn-create-new button {
        background: linear-gradient(135deg, #E11D48 0%, #BE123C 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 15px rgba(225, 29, 72, 0.4) !important;
    }

    video, .stImage img {
        max-height: 480px !important;
        width: auto !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 11px 18px !important;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.96rem;
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
    </style>
    """,
    unsafe_allow_html=True,
)


def load_config() -> Dict[str, Any]:
    """Đọc cấu hình từ config.json, kết hợp st.secrets khi deploy trên Streamlit Cloud."""
    config_path = Path("config.json")
    cfg: Dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    # Tự động nạp API key từ st.secrets (dành riêng cho Streamlit Cloud)
    try:
        if hasattr(st, "secrets"):
            if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
                cfg["pixabay_api_key"] = str(st.secrets["PIXABAY_API_KEY"])
            if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
                os.environ["GEMINI_API_KEY"] = str(st.secrets["GEMINI_API_KEY"])
            if "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
                os.environ["OPENAI_API_KEY"] = str(st.secrets["OPENAI_API_KEY"])
    except Exception:
        pass

    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    """Lưu cấu hình vào config.json."""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# Khởi tạo CSDL SQLite & Cấu hình
init_db()
config = load_config()

# Cấu hình mặc định cho 2 kênh
ch_sg_cfg = config.get("channels", {}).get("saigonbac", {})
ch_new_cfg = config.get("channels", {}).get("new_channel", {})

# ==============================================================================
# KHỞI TẠO SESSION STATE CHO KÊNH 1 (saigonbac)
# ==============================================================================
if "sg_quote_text" not in st.session_state:
    sample_q = get_random_quote(channel="saigonbac")
    st.session_state.sg_quote_text = sample_q.get("quote", "Đi qua những ngày mưa bão mới hiểu được, hóa ra bình yên lớn nhất chính là một buổi sáng thảnh thơi ngồi ngắm nắng lên.")

if "sg_quote_text_area" not in st.session_state:
    st.session_state.sg_quote_text_area = st.session_state.sg_quote_text

if "sg_bg_image" not in st.session_state:
    bg_init = Path("temp/background.jpg")
    if not bg_init.exists():
        footages = list(Path("assets/footages").glob("*.*"))
        for f in footages:
            if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                bg_init = f
                break
    st.session_state.sg_bg_image = str(bg_init) if bg_init.exists() else None

if "sg_rendered_video" not in st.session_state:
    st.session_state.sg_rendered_video = None

if "sg_signature" not in st.session_state:
    st.session_state.sg_signature = ch_sg_cfg.get("signature", "saigonbac")

if "sg_pix_theme_input" not in st.session_state:
    st.session_state["sg_pix_theme_input"] = "🌧️ Mưa Phố Đêm"

if "sg_pix_page" not in st.session_state:
    st.session_state["sg_pix_page"] = 1

if "sg_pix_gallery" not in st.session_state:
    st.session_state["sg_pix_gallery"] = []

# ==============================================================================
# KHỞI TẠO SESSION STATE CHO KÊNH 2 (Kênh Mới - Video B-Roll)
# ==============================================================================
if "new_quote_text" not in st.session_state:
    sample_q_new = get_random_quote(channel="kenh_moi")
    st.session_state.new_quote_text = sample_q_new.get(
        "quote",
        "Đừng vội nổi giận khi bị xem thường. Lúc chưa có gì trong tay, im lặng làm việc vẫn có ích hơn tranh cãi."
    )

if "new_quote_text_area" not in st.session_state:
    st.session_state.new_quote_text_area = st.session_state.new_quote_text

if "new_bg_video" not in st.session_state:
    local_samples = get_local_footages()
    st.session_state.new_bg_video = local_samples[0]["path"] if local_samples else None

if "new_rendered_video" not in st.session_state:
    st.session_state.new_rendered_video = None

if "new_signature" not in st.session_state:
    st.session_state.new_signature = ch_new_cfg.get("signature", "saigonchill")

if "new_vid_theme_input" not in st.session_state:
    st.session_state["new_vid_theme_input"] = "🌧️ Mưa Phố Đêm"

if "new_vid_gallery" not in st.session_state:
    st.session_state["new_vid_gallery"] = []

if "new_vid_page" not in st.session_state:
    st.session_state["new_vid_page"] = 1


# ==============================================================================
# TIÊU ĐỀ CHÍNH
# ==============================================================================
st.markdown('<div class="main-header">TikTok Multi-Channel Studio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Phân tách độc lập 2 kênh TikTok: Kênh 1 saigonbac (Ảnh tĩnh 18s) & Kênh 2 (Video b-roll chuyển động).</div>',
    unsafe_allow_html=True,
)

# Phân tách 2 kênh tại cấp độ cao nhất của ứng dụng
tab_ch_saigonbac, tab_ch_new = st.tabs([
    "☕ KÊNH 1: SAIGONBAC (Ảnh Tĩnh 18s)",
    "🎬 KÊNH 2: KÊNH MỚI (Video B-Roll Chuyển Động)",
])


# ==============================================================================
# WORKSPACE KÊNH 1: SAIGONBAC (ẢNH TĨNH 18S)
# ==============================================================================
with tab_ch_saigonbac:
    st.markdown(
        """
        <div class="channel-banner channel-banner-sg">
            ☕ <b>Trạm Dừng Cảm Xúc (saigonbac)</b>: Video tĩnh 18s từ Ảnh Aesthetic Tĩnh Tại + Typography Hoài Niệm, Chữa Lành & Lòng Người, chữ ký nhận diện <code>saigonbac</code>. File xuất tự động lưu vào <code>output/saigonbac/</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    sg_col_input, sg_col_preview = st.columns([1.4, 1.0], gap="large")

    with sg_col_input:
        # 1. Quản lý quote saigonbac
        st.subheader("1. Chọn Hoặc Sinh Quote Tĩnh Tại & Chữa Lành (saigonbac)")

        sg_quote_mode = st.radio(
            "Phương thức chọn Quote:",
            options=["🤖 Dùng AI sinh quote tĩnh tại & hoài niệm", "📜 Dùng quote có sẵn trong kho", "✍️ Tự gõ quote theo ý bạn"],
            index=0,
            horizontal=True,
            key="sg_quote_mode_radio",
        )

        sg_topics = ch_sg_cfg.get("topics", list(CHANNEL_CATEGORIES.get("saigonbac", {}).keys()))

        if sg_quote_mode == "🤖 Dùng AI sinh quote tĩnh tại & hoài niệm":
            sg_sel_topic = st.selectbox("Chọn chủ đề cảm xúc:", options=sg_topics, index=0, key="sg_topic_sel")
            if st.button("✨ Sinh Quote Mới (Phong Cách Tĩnh Tại & Chữa Lành)", type="primary", use_container_width=True, key="sg_btn_ai_gen"):
                with st.spinner(f"AI đang viết câu quote tĩnh tại theo chủ đề '{sg_sel_topic}'..."):
                    try:
                        ai_res = generate_quote(topic=sg_sel_topic, config=config, style="sad_introspective", channel="saigonbac")
                        new_q = ai_res["quote"]
                        st.session_state.sg_quote_text = new_q
                        st.session_state.sg_quote_text_area = new_q
                        st.session_state["sg_viral_review"] = None
                        st.session_state.sg_rendered_video = None
                        st.toast("Đã sinh quote saigonbac thành công!", icon="✨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi AI: {e}")

        elif sg_quote_mode == "📜 Dùng quote có sẵn trong kho":
            col_sg_cat, col_sg_rnd = st.columns([1.5, 1])
            with col_sg_cat:
                sg_cat_choices = get_all_categories(channel="saigonbac")
                sg_chosen_cat = st.selectbox("Lọc chủ đề:", options=sg_cat_choices, index=0, key="sg_cat_sel")
            with col_sg_rnd:
                st.write("")
                st.write("")
                if st.button("🎲 Random Quote", use_container_width=True, key="sg_btn_rnd_quote"):
                    rnd_q = get_random_quote(sg_chosen_cat, channel="saigonbac")
                    st.session_state.sg_quote_text = rnd_q["quote"]
                    st.session_state.sg_quote_text_area = rnd_q["quote"]
                    st.session_state["sg_viral_review"] = None
                    st.session_state.sg_rendered_video = None
                    st.toast("Đã chọn quote ngẫu nhiên!", icon="🎲")
                    st.rerun()

            all_q_data = load_all_quotes(channel="saigonbac")
            filtered_q = all_q_data if sg_chosen_cat == "Tất cả" else [q for q in all_q_data if q.get("category") == sg_chosen_cat]
            q_options = [q["quote"] for q in filtered_q]
            def_idx = q_options.index(st.session_state.sg_quote_text) if st.session_state.sg_quote_text in q_options else 0
            sel_dd_quote = st.selectbox("Chọn câu có sẵn:", options=q_options, index=def_idx, key="sg_dd_quote_sel")
            if sel_dd_quote != st.session_state.sg_quote_text:
                st.session_state.sg_quote_text = sel_dd_quote
                st.session_state.sg_quote_text_area = sel_dd_quote
                st.session_state["sg_viral_review"] = None
                st.session_state.sg_rendered_video = None

        sg_edited_text = st.text_area(
            "Nội dung Quote (saigonbac):",
            value=st.session_state.sg_quote_text,
            height=80,
            key="sg_quote_text_area",
        )
        if sg_edited_text != st.session_state.sg_quote_text:
            st.session_state.sg_quote_text = sg_edited_text
            st.session_state["sg_viral_review"] = None
            st.session_state.sg_rendered_video = None

        # Bước AI Review Viral cho kênh saigonbac
        col_sg_rv1, col_sg_rv2 = st.columns([1.8, 1.2])
        with col_sg_rv1:
            btn_sg_review_viral = st.button("🎯 AI Thẩm Định Độ Viral (saigonbac)", use_container_width=True, key="sg_btn_review_viral")
        with col_sg_rv2:
            st.caption("AI phân tích Hook, cảm xúc & độ dài")

        if btn_sg_review_viral:
            with st.spinner("AI đang thẩm định tiềm năng viral trên TikTok..."):
                st.session_state["sg_viral_review"] = review_viral_potential(
                    quote=st.session_state.sg_quote_text,
                    channel_style="sad_introspective",
                    channel="saigonbac",
                    config=config,
                )

        sg_review_res = st.session_state.get("sg_viral_review")
        if sg_review_res:
            score = sg_review_res.get("score", 80)
            score_color = "#10B981" if score >= 85 else ("#F59E0B" if score >= 70 else "#EF4444")
            st.markdown(
                f"""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid {score_color}; border-radius: 12px; padding: 0.9rem; margin-top: 0.5rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: {score_color};">🎯 Điểm Viral: {score}/100</span>
                        <span style="font-weight: 600; font-size: 0.9rem;">{sg_review_res.get('verdict', '')}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; margin-bottom: 0.3rem;"><b>💪 Điểm mạnh:</b> {sg_review_res.get('strengths', '')}</div>
                    <div style="font-size: 0.85rem; color: #94A3B8;"><b>💡 Góp ý:</b> {sg_review_res.get('suggestions', '')} (Hiện có: {sg_review_res.get('word_count', 0)} từ)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            imp_q = sg_review_res.get("improved_quote")
            if imp_q and imp_q.strip() and imp_q.strip() != st.session_state.sg_quote_text.strip():
                st.markdown(f"**✨ Gợi ý bản viết lại bén hơn:** *\"{imp_q}\"*")
                if st.button("✍️ Áp Dụng Câu Viết Lại Này", key="sg_btn_apply_improved", use_container_width=True):
                    st.session_state.sg_quote_text = imp_q
                    st.session_state.sg_quote_text_area = imp_q
                    st.session_state["sg_viral_review"] = None
                    st.session_state.sg_rendered_video = None
                    st.toast("Đã áp dụng câu quote tối ưu!", icon="✨")
                    st.rerun()

        st.session_state.sg_signature = st.text_input(
            "Chữ ký nhận diện thương hiệu:",
            value=st.session_state.sg_signature,
            key="sg_signature_input",
            help="Chữ ký nhỏ gọn hiển thị ngay dưới câu quote cho kênh saigonbac.",
        ).strip()

        st.divider()

        # 2. Chọn Nguồn Ảnh Nền saigonbac
        st.subheader("2. Chọn Nguồn Ảnh Nền (Photo Khổ Dọc 9:16)")

        sg_tab_pix, sg_tab_ai, sg_tab_up = st.tabs([
            "🌐 Pixabay Photo (Kho Ảnh Gốc)",
            "🎨 AI Vẽ Ảnh Độc Bản",
            "📤 Tải Ảnh Từ Máy Tính",
        ])

        with sg_tab_pix:
            st.markdown("🎯 **Chọn nhanh chủ đề ảnh tối màu (1 Chạm):**")
            themes_list = list(QUICK_THEMES_VI.keys())
            row_cols = st.columns(2)
            for t_idx, theme_label in enumerate(themes_list):
                with row_cols[t_idx % 2]:
                    if st.button(theme_label, key=f"sg_btn_theme_{t_idx}", use_container_width=True):
                        st.session_state["sg_pix_theme_input"] = theme_label
                        st.toast(f"Đã chọn: {theme_label}", icon="✨")
                        st.rerun()

            st.write("")
            st.text_input("Nhập chủ đề ảnh tùy ý:", key="sg_pix_theme_input", placeholder="con sói, ga tàu, trời mưa...")

            c_act1, c_act2 = st.columns(2)
            with c_act1:
                btn_sg_search_img = st.button("🔍 Tìm & Chọn 4 Ảnh", type="primary", use_container_width=True, key="sg_btn_search_img")
            with c_act2:
                btn_sg_rnd_img = st.button("🎲 1 Ảnh Ngẫu Nhiên", type="secondary", use_container_width=True, key="sg_btn_rnd_img")

            c_pic1, c_pic2 = st.columns(2)
            with c_pic1:
                btn_sg_picsum_one = st.button("📸 1 Ảnh Thật Picsum (0 Key)", use_container_width=True, key="sg_btn_picsum_1")
            with c_pic2:
                btn_sg_picsum_gallery = st.button("🖼️ Xem 4 Ảnh Picsum Khác", use_container_width=True, key="sg_btn_picsum_4")

            if btn_sg_search_img:
                curr_q = st.session_state.get("sg_pix_theme_input", "mưa đêm")
                st.session_state["sg_pix_page"] = (st.session_state.get("sg_pix_page", 1) % 8) + 1
                curr_p = st.session_state["sg_pix_page"]
                with st.spinner(f"Đang tìm 4 ảnh từ Pixabay (Trang {curr_p})..."):
                    st.session_state["sg_pix_gallery"] = search_pixabay_images(
                        query=curr_q,
                        api_key=config.get("pixabay_api_key"),
                        per_page=4,
                        page=curr_p,
                    )

            if btn_sg_rnd_img:
                curr_q = st.session_state.get("sg_pix_theme_input", "mưa đêm")
                with st.spinner("Đang tải 1 ảnh ngẫu nhiên từ Pixabay..."):
                    try:
                        fetched = fetch_pixabay_image(curr_q, config.get("pixabay_api_key"), Path("temp/background_sg.jpg"))
                        st.session_state.sg_bg_image = str(fetched)
                        st.session_state.sg_rendered_video = None
                        st.toast("Đã chọn ảnh Pixabay thành công!", icon="🎨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            if btn_sg_picsum_one:
                with st.spinner("Đang tải ảnh nghệ thuật từ Picsum Photos..."):
                    try:
                        p_img = fetch_picsum_image(Path("temp/background_sg.jpg"))
                        st.session_state.sg_bg_image = str(p_img)
                        st.session_state.sg_rendered_video = None
                        st.toast("Đã tải ảnh Picsum thành công!", icon="📸")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            if btn_sg_picsum_gallery:
                with st.spinner("Đang lấy 4 ảnh từ Picsum..."):
                    st.session_state["sg_pix_gallery"] = get_picsum_gallery(limit=4)
                    st.toast("Đã nạp 4 ảnh thật từ Picsum!", icon="🖼️")

            sg_gallery_items = st.session_state.get("sg_pix_gallery", [])
            if sg_gallery_items:
                st.markdown("---")
                st.markdown("🖼️ **Chạm vào ảnh bạn thích bên dưới:**")
                g_cols = st.columns(2)
                for idx, item in enumerate(sg_gallery_items[:4]):
                    with g_cols[idx % 2]:
                        st.image(item["preview_url"], use_container_width=True)
                        if st.button(f"✅ Chọn Ảnh #{idx+1}", key=f"sg_btn_pick_{item['id']}", use_container_width=True):
                            with st.spinner("Đang tải và chuẩn hóa ảnh..."):
                                out_img = download_and_crop_pixabay_image(item["large_url"], Path("temp/background_sg.jpg"))
                                st.session_state.sg_bg_image = str(out_img)
                                st.session_state.sg_rendered_video = None
                                st.toast(f"Đã chọn ảnh #{idx+1}!", icon="✨")
                                st.rerun()

        with sg_tab_ai:
            st.markdown("💡 **AI Tự Động Vẽ Ảnh Nền Độc Bản (Chuẩn 1080x1920):**")
            sg_ai_prompt = st.text_input("Mô tả ảnh:", value="rainy street night dark moody cinematic", key="sg_ai_img_p")
            if st.button("✨ Tạo Ảnh Bằng AI", type="primary", use_container_width=True, key="sg_btn_gen_ai"):
                with st.spinner("AI đang vẽ ảnh nghệ thuật..."):
                    try:
                        from modules.ai_image_gen import generate_ai_image
                        out_ai = generate_ai_image(prompt=sg_ai_prompt, output_dir=Path("temp"), width=1080, height=1920)
                        st.session_state.sg_bg_image = str(out_ai)
                        st.session_state.sg_rendered_video = None
                        st.toast("Đã tạo ảnh AI thành công!", icon="🎨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

        with sg_tab_up:
            sg_up_file = st.file_uploader("Tải file ảnh từ máy (.jpg, .png, .webp):", type=["jpg", "jpeg", "png", "webp"], key="sg_up_file")
            if sg_up_file is not None:
                save_p = Path("temp") / sg_up_file.name
                with open(save_p, "wb") as f_up:
                    f_up.write(sg_up_file.getbuffer())
                crop_p = resize_and_crop_to_tiktok(save_p)
                st.session_state.sg_bg_image = str(crop_p)
                st.session_state.sg_rendered_video = None
                st.success(f"✅ Đã tải ảnh: {sg_up_file.name}")

        st.divider()

        # Nút tạo video saigonbac 18s
        st.markdown('<div class="btn-create-sg">', unsafe_allow_html=True)
        btn_sg_create = st.button("🚀 TẠO VIDEO SAIGONBAC 18S", type="primary", use_container_width=True, key="sg_btn_render")
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_sg_create:
            bg_target = st.session_state.sg_bg_image
            if not bg_target or not Path(bg_target).exists():
                with st.spinner("Đang chuẩn bị ảnh nền..."):
                    bg_target = str(fetch_pixabay_image("night street rain", config.get("pixabay_api_key")))
                    st.session_state.sg_bg_image = bg_target

            out_folder = Path(ch_sg_cfg.get("output_folder", "output/saigonbac"))
            out_folder.mkdir(parents=True, exist_ok=True)
            out_vid = out_folder / f"tiktok_saigonbac_{int(time.time())}.mp4"

            with st.spinner("Đang ghép typography và render video 18.0 giây cho saigonbac..."):
                try:
                    render_18s_video(
                        image_path=bg_target,
                        quote=st.session_state.sg_quote_text,
                        output_path=out_vid,
                        duration=18.0,
                        signature=st.session_state.sg_signature or "saigonbac",
                    )
                    st.session_state.sg_rendered_video = str(out_vid)
                    st.toast("Dựng video saigonbac 18s hoàn tất 100%!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi render video: {e}")

    with sg_col_preview:
        st.subheader("3. Video Preview & Tải Về")

        sg_rendered = st.session_state.sg_rendered_video
        sg_bg = st.session_state.sg_bg_image

        if sg_rendered and Path(sg_rendered).exists():
            meta = probe_video_metadata(sg_rendered)
            st.video(str(sg_rendered))
            st.markdown(
                f"""
                <div class="badge-meta">
                    📏 <b>1080x1920</b> &nbsp;|&nbsp; ⏱️ <b>{meta['duration']}s</b> &nbsp;|&nbsp; 🎞️ <b>30fps</b> &nbsp;|&nbsp; 🔇 <b>No Audio</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with open(sg_rendered, "rb") as vf:
                st.download_button(
                    label="⬇️ TẢI VIDEO SAIGONBAC (.MP4)",
                    data=vf.read(),
                    file_name="tiktok_saigonbac_ready.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True,
                    key="sg_btn_dl",
                )
        elif sg_bg and Path(sg_bg).exists():
            st.caption("👁️ **Xem Trước Chữ Trên Ảnh Nền (Tỉ Lệ Chuẩn 9:16):**")
            try:
                prev_cfg = dict(config)
                prev_cfg["branding"] = {"signature": st.session_state.sg_signature, "signature_font_size": 24}
                prev_img = generate_quote_preview_image(image_path=sg_bg, quote=st.session_state.sg_quote_text, config=prev_cfg)
                st.image(str(prev_img), use_container_width=True)
            except Exception as ex:
                st.image(str(sg_bg), use_container_width=True)
            st.info("👉 Nhấn **[ 🚀 TẠO VIDEO SAIGONBAC 18S ]** để render video hoàn chỉnh lưu vào thư mục `output/saigonbac/`.")
        else:
            st.markdown(
                """
                <div style="border: 2px dashed #475569; border-radius: 12px; height: 400px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                    <div><div style="font-size: 2.2rem; margin-bottom: 0.6rem;">📱</div><b>Khung xem trước saigonbac</b><br>Video 18s sẽ phát tại đây.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ==============================================================================
# WORKSPACE KÊNH 2: KÊNH MỚI (VIDEO B-ROLL CHUYỂN ĐỘNG)
# ==============================================================================
with tab_ch_new:
    st.markdown(
        """
        <div class="channel-banner channel-banner-new">
            🎬 <b>Kênh Mới (Motion B-Roll)</b>: Video b-roll chuyển động điện ảnh + Typography triết lý, bản lĩnh, kỷ luật bản thân. Chữ ký nhận diện riêng tùy chỉnh. File xuất tự động lưu vào <code>output/kenh_moi/</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    new_col_input, new_col_preview = st.columns([1.4, 1.0], gap="large")

    with new_col_input:
        # Cài đặt thương hiệu Kênh Mới
        st.subheader("1. Cài Đặt Nhận Diện & Quote Kênh Mới")

        col_sig, col_save_sig = st.columns([2.0, 1.0])
        with col_sig:
            st.session_state.new_signature = st.text_input(
                "Chữ ký thương hiệu Kênh Mới:",
                value=st.session_state.new_signature,
                key="new_sig_input",
                help="Ví dụ: saigonchill, bando.tamtrang, trietly.cuocsong...",
            ).strip()
        with col_save_sig:
            st.write("")
            st.write("")
            if st.button("💾 Lưu Chữ Ký", use_container_width=True, key="new_btn_save_sig"):
                if "channels" not in config:
                    config["channels"] = {}
                if "new_channel" not in config["channels"]:
                    config["channels"]["new_channel"] = {}
                config["channels"]["new_channel"]["signature"] = st.session_state.new_signature
                save_config(config)
                st.toast(f"Đã lưu chữ ký '{st.session_state.new_signature}' vào cấu hình!", icon="💾")

        new_quote_mode = st.radio(
            "Phương thức chọn Quote:",
            options=["🤖 Dùng AI sinh quote triết lý & bản lĩnh", "📜 Dùng 30 câu quote Tư Mã Ý có sẵn", "✍️ Tự gõ quote theo ý bạn"],
            index=0,
            horizontal=True,
            key="new_quote_mode_radio",
        )

        new_topics = ch_new_cfg.get("topics", list(CHANNEL_CATEGORIES.get("kenh_moi", {}).keys()))

        if new_quote_mode == "🤖 Dùng AI sinh quote triết lý & bản lĩnh":
            new_sel_topic = st.selectbox("Chọn chủ đề triết lý & bản lĩnh:", options=new_topics, index=0, key="new_topic_sel")
            if st.button("✨ Sinh Quote Triết Lý & Bản Lĩnh Mới", type="primary", use_container_width=True, key="new_btn_ai_gen"):
                with st.spinner(f"AI đang viết câu quote triết lý theo chủ đề '{new_sel_topic}'..."):
                    try:
                        ai_res_new = generate_quote(topic=new_sel_topic, config=config, style="deep_philosophical", channel="kenh_moi")
                        new_q = ai_res_new["quote"]
                        st.session_state.new_quote_text = new_q
                        st.session_state.new_quote_text_area = new_q
                        st.session_state["new_viral_review"] = None
                        st.session_state.new_rendered_video = None
                        st.toast("Đã sinh quote triết lý mới thành công!", icon="✨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi AI: {e}")

        elif new_quote_mode == "📜 Dùng 30 câu quote Tư Mã Ý có sẵn":
            col_new_cat, col_new_rnd = st.columns([1.5, 1])
            with col_new_cat:
                new_cat_choices = get_all_categories(channel="kenh_moi")
                new_chosen_cat = st.selectbox("Lọc chủ đề bản lĩnh:", options=new_cat_choices, index=0, key="new_cat_sel")
            with col_new_rnd:
                st.write("")
                st.write("")
                if st.button("🎲 Random Quote Tư Mã Ý", use_container_width=True, key="new_btn_rnd_quote"):
                    rnd_q_new = get_random_quote(new_chosen_cat, channel="kenh_moi")
                    st.session_state.new_quote_text = rnd_q_new["quote"]
                    st.session_state.new_quote_text_area = rnd_q_new["quote"]
                    st.session_state["new_viral_review"] = None
                    st.session_state.new_rendered_video = None
                    st.toast("Đã chọn câu Tư Mã Ý ngẫu nhiên!", icon="🎲")
                    st.rerun()

            all_new_q_data = load_all_quotes(channel="kenh_moi")
            filtered_new_q = all_new_q_data if new_chosen_cat == "Tất cả" else [q for q in all_new_q_data if q.get("category") == new_chosen_cat]
            new_q_options = [q["quote"] for q in filtered_new_q]
            def_idx_new = new_q_options.index(st.session_state.new_quote_text) if st.session_state.new_quote_text in new_q_options else 0
            sel_dd_new_quote = st.selectbox("Chọn câu Tư Mã Ý có sẵn:", options=new_q_options, index=def_idx_new, key="new_dd_quote_sel")
            if sel_dd_new_quote != st.session_state.new_quote_text:
                st.session_state.new_quote_text = sel_dd_new_quote
                st.session_state.new_quote_text_area = sel_dd_new_quote
                st.session_state["new_viral_review"] = None
                st.session_state.new_rendered_video = None

        new_edited_text = st.text_area(
            "Nội dung Quote (Kênh Mới):",
            value=st.session_state.new_quote_text,
            height=80,
            key="new_quote_text_area",
        )
        if new_edited_text != st.session_state.new_quote_text:
            st.session_state.new_quote_text = new_edited_text
            st.session_state["new_viral_review"] = None
            st.session_state.new_rendered_video = None

        # Bước AI Review Viral cho Kênh Mới
        col_new_rv1, col_new_rv2 = st.columns([1.8, 1.2])
        with col_new_rv1:
            btn_new_review_viral = st.button("🎯 AI Thẩm Định Độ Viral (Kênh Mới)", use_container_width=True, key="new_btn_review_viral")
        with col_new_rv2:
            st.caption("AI phân tích Hook, bản lĩnh & độ dài")

        if btn_new_review_viral:
            with st.spinner("AI đang thẩm định tiềm năng viral trên TikTok..."):
                st.session_state["new_viral_review"] = review_viral_potential(
                    quote=st.session_state.new_quote_text,
                    channel_style="deep_philosophical",
                    channel="kenh_moi",
                    config=config,
                )

        new_review_res = st.session_state.get("new_viral_review")
        if new_review_res:
            score = new_review_res.get("score", 80)
            score_color = "#10B981" if score >= 85 else ("#F59E0B" if score >= 70 else "#EF4444")
            st.markdown(
                f"""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid {score_color}; border-radius: 12px; padding: 0.9rem; margin-top: 0.5rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: {score_color};">🎯 Điểm Viral: {score}/100</span>
                        <span style="font-weight: 600; font-size: 0.9rem;">{new_review_res.get('verdict', '')}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; margin-bottom: 0.3rem;"><b>💪 Điểm mạnh:</b> {new_review_res.get('strengths', '')}</div>
                    <div style="font-size: 0.85rem; color: #94A3B8;"><b>💡 Góp ý:</b> {new_review_res.get('suggestions', '')} (Hiện có: {new_review_res.get('word_count', 0)} từ)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            imp_q_new = new_review_res.get("improved_quote")
            if imp_q_new and imp_q_new.strip() and imp_q_new.strip() != st.session_state.new_quote_text.strip():
                st.markdown(f"**✨ Gợi ý bản viết lại bén hơn:** *\"{imp_q_new}\"*")
                if st.button("✍️ Áp Dụng Câu Viết Lại Này", key="new_btn_apply_improved", use_container_width=True):
                    st.session_state.new_quote_text = imp_q_new
                    st.session_state.new_quote_text_area = imp_q_new
                    st.session_state["new_viral_review"] = None
                    st.session_state.new_rendered_video = None
                    st.toast("Đã áp dụng câu quote tối ưu!", icon="✨")
                    st.rerun()

        st.divider()

        # 2. Chọn Nguồn Video B-Roll
        st.subheader("2. Chọn Nguồn Video B-Roll (Motion Footage)")

        new_tab_pix_vid, new_tab_local_vid, new_tab_up_vid = st.tabs([
            "🌐 Pixabay Video (Kho Video Miễn Phí 100%)",
            "📁 Kho Video Có Sẵn (assets/footages/)",
            "📤 Tải Video Từ Thiết Bị",
        ])

        with new_tab_pix_vid:
            st.markdown("🎯 **Chọn nhanh chủ đề video b-roll (1 Chạm):**")
            v_themes_keys = list(VIDEO_QUICK_THEMES_VI.keys())
            v_cols = st.columns(2)
            for v_idx, v_theme in enumerate(v_themes_keys):
                with v_cols[v_idx % 2]:
                    if st.button(v_theme, key=f"new_btn_vtheme_{v_idx}", use_container_width=True):
                        st.session_state["new_vid_theme_input"] = v_theme
                        st.toast(f"Đã chọn: {v_theme}", icon="🎥")
                        st.rerun()

            st.write("")
            st.text_input("Nhập chủ đề video b-roll bạn thích:", key="new_vid_theme_input", placeholder="mưa đêm, phố xá ban đêm, bờ biển...")

            col_nv1, col_nv2 = st.columns(2)
            with col_nv1:
                btn_new_search_vids = st.button("🔍 Tìm & Chọn 4 Video", type="primary", use_container_width=True, key="new_btn_search_vids")
            with col_nv2:
                btn_new_rnd_vid = st.button("🎲 1 Video Ngẫu Nhiên", type="secondary", use_container_width=True, key="new_btn_rnd_vid")

            if btn_new_search_vids:
                curr_q = st.session_state.get("new_vid_theme_input", "mưa đêm")
                st.session_state["new_vid_page"] = (st.session_state.get("new_vid_page", 1) % 6) + 1
                curr_p = st.session_state["new_vid_page"]
                with st.spinner(f"Đang tìm 4 video đẹp nhất từ Pixabay (Trang {curr_p})..."):
                    st.session_state["new_vid_gallery"] = search_pixabay_videos(
                        query=curr_q,
                        api_key=config.get("pixabay_api_key"),
                        per_page=4,
                        page=curr_p,
                    )

            if btn_new_rnd_vid:
                curr_q = st.session_state.get("new_vid_theme_input", "mưa đêm")
                with st.spinner("Đang tải ngẫu nhiên 1 video b-roll..."):
                    try:
                        fetched_v = fetch_pixabay_video_quick(
                            query=curr_q,
                            api_key=config.get("pixabay_api_key"),
                            output_path=Path("temp/background_new_ch.mp4"),
                        )
                        st.session_state.new_bg_video = str(fetched_v)
                        st.session_state.new_rendered_video = None
                        st.toast("Đã chọn ngẫu nhiên 1 video b-roll!", icon="🎥")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            new_vid_items = st.session_state.get("new_vid_gallery", [])
            if new_vid_items:
                st.markdown("---")
                st.markdown("🎥 **Chạm vào nút bên dưới video bạn thích nhất:**")
                vg_cols = st.columns(2)
                for v_i, v_it in enumerate(new_vid_items[:4]):
                    with vg_cols[v_i % 2]:
                        if v_it.get("thumbnail"):
                            st.image(v_it["thumbnail"], use_container_width=True)
                        st.caption(f"⏱️ **{v_it['duration']}s** | 💾 **{v_it['size_mb']} MB** | 👁️ {v_it['views']:,} lượt xem")
                        if st.button(f"✅ Chọn Video #{v_i+1}", key=f"new_pick_v_{v_it['id']}", use_container_width=True):
                            with st.spinner(f"Đang tải video #{v_i+1}..."):
                                out_v = download_video_stream(v_it["download_url"], Path("temp/background_new_ch.mp4"))
                                st.session_state.new_bg_video = str(out_v)
                                st.session_state.new_rendered_video = None
                                st.toast(f"Đã chọn video #{v_i+1} làm nền!", icon="✨")
                                st.rerun()

        with new_tab_local_vid:
            st.markdown("📁 **Kho video b-roll có sẵn trong `assets/footages/`:**")
            loc_list = get_local_footages()
            if loc_list:
                l_cols = st.columns(2)
                for l_idx, l_vid in enumerate(loc_list):
                    with l_cols[l_idx % 2]:
                        st.markdown(f"🎬 **{l_vid['name']}** (`{l_vid['size_mb']} MB`)")
                        if st.button(f"✅ Chọn Video Này", key=f"new_local_vid_{l_idx}", use_container_width=True):
                            st.session_state.new_bg_video = str(l_vid["path"])
                            st.session_state.new_rendered_video = None
                            st.toast(f"Đã chọn: {l_vid['name']}", icon="🎬")
                            st.rerun()

        with new_tab_up_vid:
            new_up_file = st.file_uploader("Tải file video từ thiết bị (.mp4, .mov, .webm):", type=["mp4", "mov", "webm"], key="new_up_vid_f")
            if new_up_file is not None:
                save_v_dir = Path("temp")
                save_v_dir.mkdir(parents=True, exist_ok=True)
                save_v_p = save_v_dir / new_up_file.name
                with open(save_v_p, "wb") as f_uv:
                    f_uv.write(new_up_file.getbuffer())
                st.session_state.new_bg_video = str(save_v_p)
                st.session_state.new_rendered_video = None
                st.success(f"✅ Đã tải lên video: {new_up_file.name}")

        st.divider()

        # Nút tạo video Kênh Mới
        st.markdown('<div class="btn-create-new">', unsafe_allow_html=True)
        btn_new_create = st.button("🚀 TẠO VIDEO B-ROLL NGAY", type="primary", use_container_width=True, key="new_btn_render")
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_new_create:
            target_vid = st.session_state.new_bg_video
            if not target_vid or not Path(target_vid).exists():
                local_f = get_local_footages()
                target_vid = local_f[0]["path"] if local_f else None

            if not target_vid or not Path(target_vid).exists():
                st.error("Chưa chọn video b-roll nền!")
            else:
                out_folder_new = Path(ch_new_cfg.get("output_folder", "output/kenh_moi"))
                out_folder_new.mkdir(parents=True, exist_ok=True)
                out_broll_file = out_folder_new / f"tiktok_broll_{int(time.time())}.mp4"

                with st.spinner("Đang ghép typography lên video b-roll chuyển động..."):
                    try:
                        render_video_from_footage(
                            footage_path=target_vid,
                            quote=st.session_state.new_quote_text,
                            output_path=out_broll_file,
                            duration=10.0,
                            signature=st.session_state.new_signature or "saigonchill",
                        )
                        st.session_state.new_rendered_video = str(out_broll_file)
                        st.toast("Dựng video B-Roll hoàn tất 100%!", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi render video: {e}")

    with new_col_preview:
        st.subheader("3. Video Preview & Tải Về")

        new_rendered = st.session_state.new_rendered_video
        new_bg = st.session_state.new_bg_video

        if new_rendered and Path(new_rendered).exists():
            meta_new = probe_video_metadata(new_rendered)
            st.video(str(new_rendered))
            st.markdown(
                f"""
                <div class="badge-meta">
                    📏 <b>1080x1920</b> &nbsp;|&nbsp; ⏱️ <b>{meta_new['duration']}s</b> &nbsp;|&nbsp; 🎞️ <b>30fps</b> &nbsp;|&nbsp; 🔇 <b>No Audio</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with open(new_rendered, "rb") as vf_new:
                st.download_button(
                    label="⬇️ TẢI VIDEO B-ROLL (.MP4)",
                    data=vf_new.read(),
                    file_name="tiktok_broll_ready.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True,
                    key="new_btn_dl",
                )
        elif new_bg and Path(new_bg).exists():
            st.markdown("🎥 **Nền đang chọn: Video B-Roll Chuyển Động**")
            try:
                frame_preview = extract_video_frame(new_bg, Path("temp/video_frame_preview_new.jpg"))
                prev_cfg_new = dict(config)
                prev_cfg_new["branding"] = {"signature": st.session_state.new_signature, "signature_font_size": 24}
                prev_img_new = generate_quote_preview_image(image_path=frame_preview, quote=st.session_state.new_quote_text, config=prev_cfg_new)
                st.caption("👁️ **Xem Trước Bố Cục Chữ Trên Video (Khổ Dọc 9:16):**")
                st.image(str(prev_img_new), use_container_width=True)
            except Exception as ex:
                logger.warning(f"Lỗi frame preview: {ex}")

            with st.expander("▶️ Phát thử video b-roll gốc", expanded=False):
                st.video(str(new_bg))

            st.info("👉 Nhấn **[ 🚀 TẠO VIDEO B-ROLL NGAY ]** để render video chuyển động lưu vào thư mục `output/kenh_moi/`.")
        else:
            st.markdown(
                """
                <div style="border: 2px dashed #475569; border-radius: 12px; height: 400px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                    <div><div style="font-size: 2.2rem; margin-bottom: 0.6rem;">🎬</div><b>Khung xem trước Kênh Mới</b><br>Video b-roll sẽ phát tại đây.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
