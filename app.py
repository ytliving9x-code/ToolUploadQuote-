from __future__ import annotations

"""
Ứng dụng Web Streamlit: TikTok Multi-Channel Studio (app.py)
Phân tách độc lập 2 kênh TikTok:
1. Kênh 1 (saigonbac): Video tĩnh 18s từ Ảnh Aesthetic + Typography tâm sự hoài niệm, chữa lành & lòng người, chữ ký saigonbac, lưu tại output/saigonbac/.
2. Kênh 2 (Lặng): Video chuyển động từ Video B-Roll + Typography triết lý / bản lĩnh / kỷ luật, chữ ký lang, lưu tại output/kenh_moi/.
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
import importlib

# Tự động nạp lại các module con trong thư mục modules/ để tránh stale cache RAM của Streamlit
for _m_name in ["modules.ai_image_gen", "modules.pinterest_fetcher", "modules.video_engine", "modules.video_renderer", "modules.quote_gen", "modules.viral_research"]:
    if _m_name in sys.modules:
        try:
            importlib.reload(sys.modules[_m_name])
        except Exception:
            pass

from modules.viral_research import (
    VIRAL_HOOK_PATTERNS,
    REAL_35MM_CURATED_PHOTOS,
    download_curated_35mm_photo,
    score_hook_strength,
    boost_quote_with_ai,
)

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
from modules.quote_gen import (
    CHANNEL_CATEGORIES,
    generate_quote,
    review_viral_potential,
)
from modules.ai_image_gen import (
    RETRO_COMIC_PRESETS,
    generate_retro_comic_image,
    generate_flux_image,
)
from modules.pinterest_fetcher import (
    PINTEREST_CURATED_THEMES,
    search_and_download_pinterest,
    get_cached_pinterest_images,
)
from modules.video_renderer import render_18s_video, render_video_from_footage
from modules.video_engine import (
    generate_quote_preview_image,
    generate_retro_comic_slide,
    render_retro_comic_video,
    probe_video_metadata,
)
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
    page_title="TikTok Multi-Channel Studio (saigonbac & Lặng)",
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
# KHỞI TẠO SESSION STATE CHO KÊNH 2 (Lặng - Video B-Roll)
# ==============================================================================
if "new_quote_text" not in st.session_state:
    sample_q_new = get_random_quote(channel="kenh_moi")
    st.session_state.new_quote_text = sample_q_new.get(
        "quote",
        "Đừng vội nổi giận khi bị xem thường. Lúc chưa có gì trong tay, im lặng làm việc vẫn có ích hơn tranh cãi."
    )

if "new_bg_video" not in st.session_state:
    local_samples = get_local_footages()
    st.session_state.new_bg_video = local_samples[0]["path"] if local_samples else None

if "new_rendered_video" not in st.session_state:
    st.session_state.new_rendered_video = None

if "new_signature" not in st.session_state:
    st.session_state.new_signature = ch_new_cfg.get("signature", "lang")

if "new_vid_theme_input" not in st.session_state:
    st.session_state["new_vid_theme_input"] = "🌧️ Mưa Phố Đêm"

if "new_vid_gallery" not in st.session_state:
    st.session_state["new_vid_gallery"] = []

if "new_vid_page" not in st.session_state:
    st.session_state["new_vid_page"] = 1

if "new_format_mode" not in st.session_state:
    st.session_state.new_format_mode = "🎨 TikTok Photo Slide (Tranh Minh Họa Retro Comic 9:16)"

if "new_comic_bg_image" not in st.session_state:
    sample_c = Path("assets/samples/retro_comic/sample_stoic_man.jpg")
    st.session_state.new_comic_bg_image = str(sample_c) if sample_c.exists() else None

if "new_comic_font" not in st.session_state:
    st.session_state.new_comic_font = "PatrickHand-Regular.ttf"

if "new_comic_font_size" not in st.session_state:
    st.session_state.new_comic_font_size = 54

if "new_comic_position" not in st.session_state:
    st.session_state.new_comic_position = "upper_center"

if "new_comic_all_caps" not in st.session_state:
    st.session_state.new_comic_all_caps = True

if "new_comic_rendered_slide" not in st.session_state:
    st.session_state.new_comic_rendered_slide = None

if "new_comic_rendered_video" not in st.session_state:
    st.session_state.new_comic_rendered_video = None

if "pinterest_results" not in st.session_state:
    st.session_state.pinterest_results = []

if "flux_prompt_input" not in st.session_state:
    st.session_state.flux_prompt_input = ""


# ==============================================================================
# TIÊU ĐỀ CHÍNH
# ==============================================================================
st.markdown('<div class="main-header">TikTok Multi-Channel Studio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Phân tách độc lập 2 kênh TikTok: Kênh 1 saigonbac (Ảnh tĩnh 18s) & Kênh 2 Lặng (Video b-roll chuyển động).</div>',
    unsafe_allow_html=True,
)

# 2 Không gian làm việc riêng biệt chuẩn hóa 3 bước (1-2-3)
tab_ch_saigonbac, tab_ch_new = st.tabs([
    "☕ KÊNH 1: SAIGONBAC (Ảnh Thật 35mm 18s)",
    "🎬 KÊNH 2: LẶNG (Video B-Roll Chuyển Động)",
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
            if st.button("✨ Sinh Quote Mới (Phong Cách Tĩnh Tại & Chữa Lành)", type="primary", width='stretch', key="sg_btn_ai_gen"):
                with st.spinner(f"AI đang viết câu quote tĩnh tại theo chủ đề '{sg_sel_topic}'..."):
                    try:
                        ai_res = generate_quote(topic=sg_sel_topic, config=config, style="sad_introspective", channel="saigonbac")
                        new_q = ai_res["quote"]
                        st.session_state.sg_quote_text = new_q
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
                if st.button("🎲 Random Quote", width='stretch', key="sg_btn_rnd_quote"):
                    rnd_q = get_random_quote(sg_chosen_cat, channel="saigonbac")
                    st.session_state.sg_quote_text = rnd_q["quote"]
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
                st.session_state["sg_viral_review"] = None
                st.session_state.sg_rendered_video = None

        sg_edited_text = st.text_area(
            "Nội dung Quote (saigonbac):",
            value=st.session_state.sg_quote_text,
            height=80,
        )
        if sg_edited_text != st.session_state.sg_quote_text:
            st.session_state.sg_quote_text = sg_edited_text
            st.session_state["sg_viral_review"] = None
            st.session_state.sg_rendered_video = None

        # Bước 1B: Tối ưu Hook 3s Viral trực tiếp tại chỗ
        col_sg_rv1, col_sg_rv2 = st.columns([1.5, 1.0])
        with col_sg_rv1:
            btn_sg_boost = st.button("⚡ AI 'Độ' Hook 3s Viral (Tăng View)", type="secondary", width='stretch', key="sg_btn_boost_hook")
        with col_sg_rv2:
            btn_sg_audit = st.button("📊 Đo Điểm Hook 3s", width='stretch', key="sg_btn_audit_hook")

        if btn_sg_audit:
            with st.spinner("Đang phân tích 3 giây đầu..."):
                audit_res = score_hook_strength(st.session_state.sg_quote_text)
                st.session_state["sg_last_audit"] = audit_res

        if "sg_last_audit" in st.session_state and st.session_state["sg_last_audit"]:
            res = st.session_state["sg_last_audit"]
            st.markdown(
                f"""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #38BDF8; border-radius: 10px; padding: 0.8rem; margin: 0.5rem 0;">
                    <div style="font-size: 0.95rem; font-weight: 700; color: #38BDF8;">Điểm Níu Chân: {res['score']}/100 — {res['grade']}</div>
                    <div style="font-size: 0.82rem; color: #94A3B8;">3s đầu đọc: <i>"{res['first_hook_words']}..."</i> ({res['word_count']} từ)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if btn_sg_boost:
            with st.spinner("AI đang tạo 3 biến thể Hook giữ chân..."):
                try:
                    b_res = boost_quote_with_ai(st.session_state.sg_quote_text, channel="saigonbac", config=config)
                    st.session_state["sg_boost_variants"] = b_res
                    st.toast("Đã tạo 3 phiên bản Hook triệu view!", icon="🔥")
                except Exception as ex:
                    st.error(f"Lỗi AI: {ex}")

        if "sg_boost_variants" in st.session_state and st.session_state["sg_boost_variants"]:
            st.markdown("🎯 **Chọn phiên bản Hook Outlier để áp dụng ngay:**")
            for k_var, v_item in st.session_state["sg_boost_variants"].items():
                if isinstance(v_item, dict):
                    col_v_txt, col_v_act = st.columns([3.5, 1])
                    with col_v_txt:
                        st.markdown(f"• <b>{v_item.get('hook_type', '')}:</b> \"{v_item.get('quote', '')}\"", unsafe_allow_html=True)
                    with col_v_act:
                        if st.button("Chọn", key=f"sg_pick_v_{k_var}", width='stretch'):
                            st.session_state.sg_quote_text = v_item.get("quote", "")
                            st.session_state["sg_boost_variants"] = None
                            st.session_state["sg_last_audit"] = None
                            st.session_state.sg_rendered_video = None
                            st.toast("Đã áp dụng Hook triệu view!", icon="✨")
                            st.rerun()

        st.session_state.sg_signature = st.text_input(
            "Chữ ký nhận diện thương hiệu:",
            value=st.session_state.sg_signature,
            key="sg_signature_input",
            help="Chữ ký nhỏ gọn hiển thị ngay dưới câu quote cho kênh saigonbac.",
        ).strip()

        with st.expander("🛡️ Chống Loá Chữ Nền Sáng (Bóng Mờ Điện Ảnh + Gradient Đáy)", expanded=False):
            col_sg_ag1, col_sg_ag2 = st.columns(2)
            with col_sg_ag1:
                st.toggle("Bật Bộ Chống Loá", value=True, key="sg_toggle_antiglare", help="Tự động phủ gradient tối êm dịu ở đáy và đổ bóng mờ cho chữ.")
            with col_sg_ag2:
                st.selectbox(
                    "Độ tương phản chữ:",
                    options=["Vừa Phải (Khuyên Dùng)", "Mạnh (Cho Nền Rất Sáng/Chói)", "Nhẹ (Cho Nền Tối)"],
                    index=0,
                    key="sg_antiglare_level",
                )

        st.divider()

        # 2. Chọn Nền Ảnh Thật 35mm Điện Ảnh (saigonbac)
        st.subheader("2. Chọn Nền Ảnh Thật 35mm Điện Ảnh (Khổ Dọc 9:16)")
        st.markdown("📸 **Tuyển chọn ảnh chụp thật 35mm chất lượng cao (1-Chạm là đổi ảnh ngay):**")

        p_items = list(REAL_35MM_CURATED_PHOTOS.items())
        r1_cols = st.columns(4)
        for i in range(min(4, len(p_items))):
            p_name, p_link = p_items[i]
            with r1_cols[i]:
                if st.button(p_name, key=f"btn_p_r1_{i}", width='stretch'):
                    with st.spinner(f"Đang nạp ảnh {p_name}..."):
                        try:
                            saved = download_curated_35mm_photo(p_link, Path("temp/background_sg.jpg"))
                            st.session_state.sg_bg_image = str(saved)
                            st.session_state.sg_rendered_video = None
                            st.toast(f"Đã chọn ảnh: {p_name}!", icon="📸")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Lỗi khi nạp ảnh: {ex}")

        r2_cols = st.columns(4)
        for i in range(4, min(8, len(p_items))):
            p_name, p_link = p_items[i]
            with r2_cols[i - 4]:
                if st.button(p_name, key=f"btn_p_r2_{i}", width='stretch'):
                    with st.spinner(f"Đang nạp ảnh {p_name}..."):
                        try:
                            saved = download_curated_35mm_photo(p_link, Path("temp/background_sg.jpg"))
                            st.session_state.sg_bg_image = str(saved)
                            st.session_state.sg_rendered_video = None
                            st.toast(f"Đã chọn ảnh: {p_name}!", icon="📸")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Lỗi khi nạp ảnh: {ex}")

        with st.expander("🔍 Tìm thêm ảnh thật từ Pixabay / Picsum hoặc Tải ảnh từ máy", expanded=False):
            sg_tab_pix, sg_tab_up = st.tabs(["🌐 Tìm Ảnh Pixabay / Picsum", "📤 Tải Ảnh Từ Máy Tính"])
            with sg_tab_pix:
                st.text_input("Nhập từ khóa ảnh thật:", key="sg_pix_theme_input", placeholder="mưa đêm, ga tàu, phố cũ...")
                c_s1, c_s2 = st.columns(2)
                with c_s1:
                    btn_sg_search_img = st.button("🔍 Tìm 4 Ảnh Thật Pixabay", type="primary", width='stretch', key="sg_btn_search_img")
                with c_s2:
                    btn_sg_picsum_one = st.button("📸 1 Ảnh Thật Picsum Ngẫu Nhiên", width='stretch', key="sg_btn_picsum_1")

                if btn_sg_search_img:
                    curr_q = st.session_state.get("sg_pix_theme_input", "mưa đêm")
                    st.session_state["sg_pix_page"] = (st.session_state.get("sg_pix_page", 1) % 8) + 1
                    curr_p = st.session_state["sg_pix_page"]
                    with st.spinner(f"Đang tìm 4 ảnh thật Pixabay (Trang {curr_p})..."):
                        st.session_state["sg_pix_gallery"] = search_pixabay_images(
                            query=curr_q,
                            api_key=config.get("pixabay_api_key"),
                            per_page=4,
                            page=curr_p,
                        )

                if btn_sg_picsum_one:
                    with st.spinner("Đang tải ảnh thật nghệ thuật từ Picsum Photos..."):
                        try:
                            p_img = fetch_picsum_image(Path("temp/background_sg.jpg"))
                            st.session_state.sg_bg_image = str(p_img)
                            st.session_state.sg_rendered_video = None
                            st.toast("Đã tải ảnh Picsum thành công!", icon="📸")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

                sg_gallery_items = st.session_state.get("sg_pix_gallery", [])
                if sg_gallery_items:
                    st.markdown("🖼️ **Chạm vào ảnh bạn thích bên dưới:**")
                    g_cols = st.columns(2)
                    for idx, item in enumerate(sg_gallery_items[:4]):
                        with g_cols[idx % 2]:
                            st.image(item["preview_url"], width='stretch')
                            if st.button(f"✅ Chọn Ảnh #{idx+1}", key=f"sg_btn_pick_{item['id']}", width='stretch'):
                                with st.spinner("Đang tải và chuẩn hóa ảnh..."):
                                    out_img = download_and_crop_pixabay_image(item["large_url"], Path("temp/background_sg.jpg"))
                                    st.session_state.sg_bg_image = str(out_img)
                                    st.session_state.sg_rendered_video = None
                                    st.toast(f"Đã chọn ảnh #{idx+1}!", icon="✨")
                                    st.rerun()

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
        btn_sg_create = st.button("🚀 TẠO VIDEO SAIGONBAC 18S", type="primary", width='stretch', key="sg_btn_render")
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
                    ag_alpha_map = {"Vừa Phải (Khuyên Dùng)": 145, "Mạnh (Cho Nền Rất Sáng/Chói)": 190, "Nhẹ (Cho Nền Tối)": 95}
                    ag_radius_map = {"Vừa Phải (Khuyên Dùng)": 3.5, "Mạnh (Cho Nền Rất Sáng/Chói)": 4.8, "Nhẹ (Cho Nền Tối)": 2.2}
                    ag_stroke_map = {"Vừa Phải (Khuyên Dùng)": 1, "Mạnh (Cho Nền Rất Sáng/Chói)": 2, "Nhẹ (Cho Nền Tối)": 1}
                    sel_level = st.session_state.get("sg_antiglare_level", "Vừa Phải (Khuyên Dùng)")
                    is_ag = st.session_state.get("sg_toggle_antiglare", True)

                    render_18s_video(
                        image_path=bg_target,
                        quote=st.session_state.sg_quote_text,
                        output_path=out_vid,
                        duration=18.0,
                        signature=st.session_state.sg_signature or "saigonbac",
                        enable_gradient_scrim=is_ag,
                        scrim_max_alpha=ag_alpha_map.get(sel_level, 145),
                        shadow_blur_radius=ag_radius_map.get(sel_level, 3.5),
                        stroke_width=ag_stroke_map.get(sel_level, 1),
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
                    width='stretch',
                    key="sg_btn_dl",
                )
        elif sg_bg and Path(sg_bg).exists():
            st.caption("👁️ **Xem Trước Chữ Trên Ảnh Nền (Tỉ Lệ Chuẩn 9:16):**")
            try:
                prev_cfg = dict(config)
                prev_cfg["branding"] = {"signature": st.session_state.sg_signature, "signature_font_size": 24}
                ag_alpha_map = {"Vừa Phải (Khuyên Dùng)": 145, "Mạnh (Cho Nền Rất Sáng/Chói)": 190, "Nhẹ (Cho Nền Tối)": 95}
                ag_radius_map = {"Vừa Phải (Khuyên Dùng)": 3.5, "Mạnh (Cho Nền Rất Sáng/Chói)": 4.8, "Nhẹ (Cho Nền Tối)": 2.2}
                ag_stroke_map = {"Vừa Phải (Khuyên Dùng)": 1, "Mạnh (Cho Nền Rất Sáng/Chói)": 2, "Nhẹ (Cho Nền Tối)": 1}
                sel_level = st.session_state.get("sg_antiglare_level", "Vừa Phải (Khuyên Dùng)")
                is_ag = st.session_state.get("sg_toggle_antiglare", True)
                prev_cfg["typography"] = {
                    "enable_gradient_scrim": is_ag,
                    "scrim_max_alpha": ag_alpha_map.get(sel_level, 145),
                    "shadow_blur_radius": ag_radius_map.get(sel_level, 3.5),
                    "stroke_width": ag_stroke_map.get(sel_level, 1),
                }
                prev_img = generate_quote_preview_image(image_path=sg_bg, quote=st.session_state.sg_quote_text, config=prev_cfg)
                st.image(str(prev_img), width='stretch')
            except Exception as ex:
                st.image(str(sg_bg), width='stretch')
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
# WORKSPACE KÊNH 2: LẶNG (VIDEO B-ROLL CHUYỂN ĐỘNG)
# ==============================================================================
with tab_ch_new:
    st.markdown(
        """
        <div class="channel-banner channel-banner-new">
            🎬 <b>Kênh Lặng (Motion B-Roll)</b>: Video b-roll chuyển động điện ảnh + Typography triết lý, bản lĩnh, kỷ luật bản thân. Chữ ký nhận diện <code>lang</code> tùy chỉnh. File xuất tự động lưu vào <code>output/kenh_moi/</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    new_col_input, new_col_preview = st.columns([1.4, 1.0], gap="large")

    with new_col_input:
        # Cài đặt thương hiệu Kênh Lặng
        st.subheader("1. Cài Đặt Nhận Diện & Quote Kênh Lặng")

        col_sig, col_save_sig = st.columns([2.0, 1.0])
        with col_sig:
            st.session_state.new_signature = st.text_input(
                "Chữ ký thương hiệu Kênh Lặng:",
                value=st.session_state.new_signature,
                key="new_sig_input",
                help="Ví dụ: lang, lang.official, trietly.cuocsong...",
            ).strip()
        with col_save_sig:
            st.write("")
            st.write("")
            if st.button("💾 Lưu Chữ Ký", width='stretch', key="new_btn_save_sig"):
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
            if st.button("✨ Sinh Quote Triết Lý & Bản Lĩnh Mới", type="primary", width='stretch', key="new_btn_ai_gen"):
                with st.spinner(f"AI đang viết câu quote triết lý theo chủ đề '{new_sel_topic}'..."):
                    try:
                        ai_res_new = generate_quote(topic=new_sel_topic, config=config, style="deep_philosophical", channel="kenh_moi")
                        new_q = ai_res_new["quote"]
                        st.session_state.new_quote_text = new_q
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
                if st.button("🎲 Random Quote Tư Mã Ý", width='stretch', key="new_btn_rnd_quote"):
                    rnd_q_new = get_random_quote(new_chosen_cat, channel="kenh_moi")
                    st.session_state.new_quote_text = rnd_q_new["quote"]
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
                st.session_state["new_viral_review"] = None
                st.session_state.new_rendered_video = None

        new_edited_text = st.text_area(
            "Nội dung Quote (Kênh Lặng):",
            value=st.session_state.new_quote_text,
            height=80,
        )
        if new_edited_text != st.session_state.new_quote_text:
            st.session_state.new_quote_text = new_edited_text
            st.session_state["new_viral_review"] = None
            st.session_state.new_rendered_video = None

        # Bước 1B: Tối ưu Hook 3s Viral trực tiếp cho Kênh Lặng (Tư Mã Ý / Bản Lĩnh)
        col_new_rv1, col_new_rv2 = st.columns([1.5, 1.0])
        with col_new_rv1:
            btn_new_boost = st.button("⚡ AI 'Độ' Hook 3s (Tư Mã Ý / Kẻ Mạnh)", type="secondary", width='stretch', key="new_btn_boost_hook")
        with col_new_rv2:
            btn_new_audit = st.button("📊 Đo Điểm Hook 3s", width='stretch', key="new_btn_audit_hook")

        if btn_new_audit:
            with st.spinner("Đang phân tích 3 giây đầu..."):
                audit_res_new = score_hook_strength(st.session_state.new_quote_text)
                st.session_state["new_last_audit"] = audit_res_new

        if "new_last_audit" in st.session_state and st.session_state.get("new_last_audit"):
            res_n = st.session_state["new_last_audit"]
            st.markdown(
                f"""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #F43F5E; border-radius: 10px; padding: 0.8rem; margin: 0.5rem 0;">
                    <div style="font-size: 0.95rem; font-weight: 700; color: #F43F5E;">Điểm Níu Chân: {res_n['score']}/100 — {res_n['grade']}</div>
                    <div style="font-size: 0.82rem; color: #94A3B8;">3s đầu đọc: <i>"{res_n['first_hook_words']}..."</i> ({res_n['word_count']} từ)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if btn_new_boost:
            with st.spinner("AI đang tạo 3 biến thể Hook bản lĩnh..."):
                try:
                    b_res_n = boost_quote_with_ai(st.session_state.new_quote_text, channel="kenh_moi", config=config)
                    st.session_state["new_boost_variants"] = b_res_n
                    st.toast("Đã tạo 3 phiên bản Hook Tư Mã Ý / Kẻ Mạnh!", icon="🔥")
                except Exception as ex:
                    st.error(f"Lỗi AI: {ex}")

        if "new_boost_variants" in st.session_state and st.session_state.get("new_boost_variants"):
            st.markdown("🎯 **Chọn phiên bản Hook Outlier để áp dụng ngay:**")
            for k_var, v_item in st.session_state["new_boost_variants"].items():
                if isinstance(v_item, dict):
                    col_v_txt, col_v_act = st.columns([3.5, 1])
                    with col_v_txt:
                        st.markdown(f"• <b>{v_item.get('hook_type', '')}:</b> \"{v_item.get('quote', '')}\"", unsafe_allow_html=True)
                    with col_v_act:
                        if st.button("Chọn", key=f"new_pick_v_{k_var}", width='stretch'):
                            st.session_state.new_quote_text = v_item.get("quote", "")
                            st.session_state["new_boost_variants"] = None
                            st.session_state["new_last_audit"] = None
                            st.session_state.new_rendered_video = None
                            st.session_state.new_comic_rendered_slide = None
                            st.toast("Đã áp dụng Hook triệu view!", icon="✅")
                            st.rerun()

        st.divider()

        st.divider()

        # 2. Định dạng nội dung cho Kênh Lặng
        st.subheader("2. Chọn Định Dạng Xuất Bản (Kênh Lặng)")
        new_format_mode = st.radio(
            "Định dạng:",
            options=[
                "🎨 TikTok Photo Slide (Tranh Minh Họa Retro Comic 9:16)",
                "🎬 Video B-Roll Chuyển Động (Motion Footage 10s)",
            ],
            index=0 if st.session_state.get("new_format_mode", "").startswith("🎨") else 1,
            horizontal=True,
            key="new_format_mode_radio",
        )
        st.session_state.new_format_mode = new_format_mode

        if new_format_mode.startswith("🎨"):
            st.markdown(
                """
                <div style="background: rgba(30, 27, 75, 0.4); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; color: #DDD6FE;">
                    ✨ <b>TikTok Photo Carousel Mode:</b> Tranh minh họa hoài niệm phong cách Retro Comic / Ligne Claire & Edward Hopper + Typography viết tay nghệ thuật. Rất thích hợp làm album vuốt ảnh triệu view.
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Chọn / Sinh tranh Retro Comic
            st.markdown("##### 🖼️ Chọn Hoặc Sinh Tranh Minh Họa Retro Comic:")
            tab_comic_pin, tab_comic_flux, tab_comic_preset, tab_comic_upload = st.tabs([
                "📌 Kho Tranh Pinterest (Artist Gốc Triệu View)",
                "✨ AI FLUX.1 (Siêu Nét Điện Ảnh)",
                "🏛️ Bối Cảnh Nghệ Thuật Mẫu",
                "📤 Tải Ảnh Từ Máy Tính",
            ])

            with tab_comic_pin:
                st.markdown(
                    """
                    <div style="font-size: 0.88rem; color: #CBD5E1; margin-bottom: 0.8rem;">
                        📌 <b>Nguồn Pinterest:</b> Tải trực tiếp tranh minh họa gốc của các họa sĩ truyện tranh hoài niệm (Retro Comic / Ligne Claire / Graphic Novel), đúng phong cách kênh triệu view <i>Just.breathe</i>. Tự động crop chuẩn dọc 1080x1920 (9:16).
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("🎯 **1. Chọn nhanh chủ đề Pinterest thịnh hành (1 Chạm):**")
                pin_themes_keys = list(PINTEREST_CURATED_THEMES.keys())
                p_pin_cols = st.columns(2)
                for pin_idx, p_theme in enumerate(pin_themes_keys):
                    with p_pin_cols[pin_idx % 2]:
                        if st.button(p_theme, key=f"btn_pin_theme_{pin_idx}", width='stretch'):
                            with st.spinner(f"Đang tìm & tải tranh Pinterest: '{p_theme}'..."):
                                pin_res = search_and_download_pinterest(query=p_theme, limit=4)
                                if pin_res:
                                    st.session_state.pinterest_results = pin_res
                                    st.session_state.new_comic_bg_image = pin_res[0]["path"]
                                    st.session_state.new_comic_rendered_slide = None
                                    st.session_state.new_comic_rendered_video = None
                                    st.toast(f"Đã tải {len(pin_res)} tranh Pinterest và chọn ảnh đầu tiên!", icon="📌")
                                    st.rerun()
                                else:
                                    st.warning("Không tìm thấy ảnh trên Pinterest, vui lòng thử chủ đề khác.")

                st.markdown("🔍 **2. Hoặc tìm kiếm từ khóa Pinterest tùy ý:**")
                col_pq1, col_pq2 = st.columns([2.2, 1.0])
                with col_pq1:
                    custom_pin_query = st.text_input(
                        "Nhập từ khóa (tiếng Anh cho kết quả chuẩn nhất):",
                        placeholder="Ví dụ: retro comic couple rain, vintage ligne claire aesthetic, 1980s graphic novel...",
                        key="pin_custom_query_input",
                    )
                with col_pq2:
                    st.write("")
                    st.write("")
                    btn_search_pin = st.button("🔍 Tìm & Tải 4 Tranh", type="primary", width='stretch', key="btn_exec_search_pin")

                if btn_search_pin and custom_pin_query.strip():
                    with st.spinner(f"Đang cào 4 tranh Pinterest với từ khóa '{custom_pin_query.strip()}'..."):
                        pin_res = search_and_download_pinterest(query=custom_pin_query.strip(), limit=4)
                        if pin_res:
                            st.session_state.pinterest_results = pin_res
                            st.session_state.new_comic_bg_image = pin_res[0]["path"]
                            st.session_state.new_comic_rendered_slide = None
                            st.session_state.new_comic_rendered_video = None
                            st.toast(f"Đã tải {len(pin_res)} tranh Pinterest!", icon="🎉")
                            st.rerun()
                        else:
                            st.warning("Không tìm thấy tranh phù hợp trên Pinterest.")

                # Hiển thị bộ sưu tập tranh vừa tải
                pin_list = st.session_state.get("pinterest_results", [])
                if pin_list:
                    st.markdown("##### 🖼️ Kết Quả Vừa Tải (Bấm chọn tranh làm nền):")
                    grid_cols = st.columns(2)
                    for g_idx, pin_item in enumerate(pin_list):
                        with grid_cols[g_idx % 2]:
                            p_path = pin_item.get("path")
                            if p_path and Path(p_path).exists():
                                st.image(p_path, width='stretch')
                                is_selected = (st.session_state.new_comic_bg_image == p_path)
                                btn_label = "✅ Đang Chọn" if is_selected else f"👉 Chọn Tranh #{g_idx+1}"
                                if st.button(btn_label, key=f"btn_sel_pin_{g_idx}", width='stretch', disabled=is_selected):
                                    st.session_state.new_comic_bg_image = p_path
                                    st.session_state.new_comic_rendered_slide = None
                                    st.session_state.new_comic_rendered_video = None
                                    st.toast(f"Đã chọn Tranh #{g_idx+1}!", icon="✨")
                                    st.rerun()

                # Expander xem ảnh trong cache
                with st.expander("📁 Kho Tranh Pinterest Đã Tải Trong Máy (Cache)", expanded=False):
                    cached_pins = get_cached_pinterest_images(limit=12)
                    if cached_pins:
                        c_grid = st.columns(3)
                        for c_idx, c_pin in enumerate(cached_pins):
                            with c_grid[c_idx % 3]:
                                st.image(c_pin["path"], width='stretch')
                                if st.button("Chọn ảnh này", key=f"btn_pick_cache_{c_idx}", width='stretch'):
                                    st.session_state.new_comic_bg_image = c_pin["path"]
                                    st.session_state.new_comic_rendered_slide = None
                                    st.session_state.new_comic_rendered_video = None
                                    st.toast("Đã chọn tranh từ cache!", icon="🖼️")
                                    st.rerun()
                    else:
                        st.caption("Chưa có ảnh Pinterest trong cache.")

            with tab_comic_flux:
                st.markdown(
                    """
                    <div style="font-size: 0.88rem; color: #CBD5E1; margin-bottom: 0.8rem;">
                        ⚡ <b>FLUX.1 (Black Forest Labs):</b> Mô hình sinh ảnh điện ảnh tối tân nhất thế giới hiện nay. Tái hiện hoàn hảo phong cách Graphic Novel thập niên 80, ánh sáng mưa đêm, nét viền Ligne Claire và hạt nhiễu giấy cổ điển.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_fl_mode, col_fl_suggest = st.columns([1.5, 1.0])
                with col_fl_suggest:
                    st.write("")
                    st.write("")
                    if st.button("💡 Gợi Ý Prompt Từ Quote", width='stretch', key="btn_suggest_flux_prompt"):
                        q_now = st.session_state.new_quote_text.strip()
                        st.session_state.flux_prompt_input = f"Retro vintage comic illustration depicting the stoic depth of: {q_now[:80]}, 1980s graphic novel style, ligne claire, moody lighting, vertical 9:16"
                        st.toast("Đã sinh prompt theo ngữ cảnh câu quote!", icon="💡")
                        st.rerun()

                with col_fl_mode:
                    flux_model_sel = st.selectbox(
                        "Lựa chọn AI Model:",
                        options=["flux (FLUX.1 - Đỉnh cao nghệ thuật)", "sdxl_turbo (Siêu tốc 3 giây)"],
                        index=0,
                        key="flux_model_choice",
                    )
                    chosen_m = "flux" if "flux" in flux_model_sel else "sdxl_turbo"

                user_comic_prompt = st.text_area(
                    "Mô tả bối cảnh tranh muốn AI vẽ (Prompt):",
                    value=st.session_state.flux_prompt_input,
                    placeholder="ví dụ: thoughtful solitary man in dark trench coat standing by rainy window in dimly lit room, retro comic ligne claire...",
                    height=80,
                    key="flux_prompt_textarea",
                )
                if user_comic_prompt != st.session_state.flux_prompt_input:
                    st.session_state.flux_prompt_input = user_comic_prompt

                if st.button("✨ SINH TRANH FLUX.1 ĐỘC BẢN (1080x1920)", type="primary", width='stretch', key="new_btn_gen_flux"):
                    with st.spinner("AI FLUX.1 đang vẽ tranh nghệ thuật 9:16 (khoảng 10-15s)..."):
                        try:
                            prompt_val = st.session_state.flux_prompt_input.strip() if st.session_state.flux_prompt_input.strip() else "auto"
                            import inspect
                            sig = inspect.signature(generate_retro_comic_image)
                            if "model" in sig.parameters:
                                out_img = generate_retro_comic_image(
                                    prompt_or_theme=prompt_val,
                                    quote_context=st.session_state.new_quote_text,
                                    model=chosen_m,
                                )
                            else:
                                out_img = generate_flux_image(
                                    prompt=f"Retro vintage comic illustration, 1980s graphic novel style, ligne claire, {prompt_val}",
                                    model=chosen_m,
                                )
                            st.session_state.new_comic_bg_image = str(out_img)
                            st.session_state.new_comic_rendered_slide = None
                            st.session_state.new_comic_rendered_video = None
                            st.toast("Đã vẽ xong bức tranh FLUX.1 độc bản!", icon="🎨")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi vẽ tranh FLUX.1: {e}")

            with tab_comic_preset:
                st.caption("Chọn nhanh 1 trong 6 bối cảnh kinh điển cho Kênh Lặng (1 chạm):")
                p_cols = st.columns(2)
                preset_keys = list(RETRO_COMIC_PRESETS.keys())
                for p_idx, p_name in enumerate(preset_keys):
                    with p_cols[p_idx % 2]:
                        if st.button(p_name, key=f"new_btn_preset_{p_idx}", width='stretch'):
                            with st.spinner(f"Đang tạo tranh theo chủ đề '{p_name}'..."):
                                try:
                                    out_img = generate_retro_comic_image(prompt_or_theme=p_name)
                                    st.session_state.new_comic_bg_image = str(out_img)
                                    st.session_state.new_comic_rendered_slide = None
                                    st.session_state.new_comic_rendered_video = None
                                    st.toast(f"Đã chọn: {p_name}", icon="🖼️")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Lỗi: {e}")

            with tab_comic_upload:
                up_comic = st.file_uploader("Tải tranh từ thiết bị (.jpg, .png, .webp):", type=["jpg", "jpeg", "png", "webp"], key="new_up_comic_f")
                if up_comic is not None:
                    save_c_dir = Path("temp")
                    save_c_dir.mkdir(parents=True, exist_ok=True)
                    save_c_path = save_c_dir / f"up_comic_{up_comic.name}"
                    with open(save_c_path, "wb") as f_uc:
                        f_uc.write(up_comic.getbuffer())
                    st.session_state.new_comic_bg_image = str(save_c_path)
                    st.session_state.new_comic_rendered_slide = None
                    st.session_state.new_comic_rendered_video = None
                    st.success(f"✅ Đã tải lên ảnh: {up_comic.name}")

            st.markdown("---")
            # Tùy chỉnh Typography
            st.markdown("##### ✍️ Tùy Chỉnh Typography Retro:")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                font_options = {
                    "Patrick Hand (Viết tay hoài niệm chuẩn TikTok)": "PatrickHand-Regular.ttf",
                    "Itim (Truyện tranh mềm mại)": "Itim-Regular.ttf",
                    "Be Vietnam Pro (Đậm nét hiện đại)": "BeVietnamPro-Bold.ttf",
                }
                sel_font_label = st.selectbox("Kiểu font chữ:", options=list(font_options.keys()), index=0, key="new_sel_font")
                st.session_state.new_comic_font = font_options[sel_font_label]

                pos_options = {
                    "Phía trên (Bầu trời / Khoảng trống - Khuyên dùng)": "upper_center",
                    "Chính giữa ảnh": "center",
                    "Phía dưới góc trái": "lower_left",
                }
                sel_pos_label = st.selectbox("Vị trí chữ:", options=list(pos_options.keys()), index=0, key="new_sel_pos")
                st.session_state.new_comic_position = pos_options[sel_pos_label]

            with col_f2:
                st.session_state.new_comic_font_size = st.slider("Cỡ chữ (px):", min_value=38, max_value=72, value=st.session_state.new_comic_font_size, step=2, key="new_slide_fs")
                st.session_state.new_comic_all_caps = st.checkbox("Viết in hoa toàn bộ (ALL CAPS)", value=st.session_state.new_comic_all_caps, key="new_chk_caps")

            st.divider()

            # Nút xuất ảnh slide & video
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_render_slide = st.button("🎨 XUẤT ẢNH PHOTO SLIDE (1080x1920)", type="primary", width='stretch', key="new_btn_render_slide")
            with col_b2:
                btn_render_c_vid = st.button("🚀 RENDER VIDEO 10S (KEN BURNS)", type="secondary", width='stretch', key="new_btn_render_c_vid")

            if btn_render_slide:
                c_bg = st.session_state.new_comic_bg_image
                if not c_bg or not Path(c_bg).exists():
                    c_bg = "assets/samples/retro_comic/sample_stoic_man.jpg"
                out_dir = Path("output/kenh_moi")
                out_dir.mkdir(parents=True, exist_ok=True)
                out_slide = out_dir / f"tiktok_slide_{int(time.time())}.jpg"

                with st.spinner("Đang tạo ảnh TikTok Photo Slide 1080x1920..."):
                    try:
                        sig_text = f"— {st.session_state.new_signature.upper()} —" if st.session_state.new_signature else "— LẶNG —"
                        generated_slide = generate_retro_comic_slide(
                            image_path=c_bg,
                            quote=st.session_state.new_quote_text,
                            output_path=out_slide,
                            font_family=st.session_state.new_comic_font,
                            font_size=st.session_state.new_comic_font_size,
                            position=st.session_state.new_comic_position,
                            all_caps=st.session_state.new_comic_all_caps,
                            signature=sig_text,
                        )
                        st.session_state.new_comic_rendered_slide = str(generated_slide)
                        st.session_state.new_comic_rendered_video = None
                        st.toast("Đã xuất ảnh Photo Slide 1080x1920 thành công!", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            if btn_render_c_vid:
                c_bg = st.session_state.new_comic_bg_image
                if not c_bg or not Path(c_bg).exists():
                    c_bg = "assets/samples/retro_comic/sample_stoic_man.jpg"
                out_dir = Path("output/kenh_moi")
                out_dir.mkdir(parents=True, exist_ok=True)
                temp_slide = Path("temp/temp_slide_for_vid.jpg")
                out_vid_c = out_dir / f"tiktok_comic_vid_{int(time.time())}.mp4"

                with st.spinner("Đang render video Ken Burns 10s..."):
                    try:
                        sig_text = f"— {st.session_state.new_signature.upper()} —" if st.session_state.new_signature else "— LẶNG —"
                        generate_retro_comic_slide(
                            image_path=c_bg,
                            quote=st.session_state.new_quote_text,
                            output_path=temp_slide,
                            font_family=st.session_state.new_comic_font,
                            font_size=st.session_state.new_comic_font_size,
                            position=st.session_state.new_comic_position,
                            all_caps=st.session_state.new_comic_all_caps,
                            signature=sig_text,
                        )
                        rendered_v = render_retro_comic_video(
                            slide_image_path=temp_slide,
                            output_path=out_vid_c,
                            duration=10.0,
                        )
                        st.session_state.new_comic_rendered_video = str(rendered_v)
                        st.toast("Render video Ken Burns 10s hoàn tất!", icon="🚀")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi render video: {e}")

        else:
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
                        if st.button(v_theme, key=f"new_btn_vtheme_{v_idx}", width='stretch'):
                            st.session_state["new_vid_theme_input"] = v_theme
                            st.toast(f"Đã chọn: {v_theme}", icon="🎥")
                            st.rerun()

                st.write("")
                st.text_input("Nhập chủ đề video b-roll bạn thích:", key="new_vid_theme_input", placeholder="mưa đêm, phố xá ban đêm, bờ biển...")

                col_nv1, col_nv2 = st.columns(2)
                with col_nv1:
                    btn_new_search_vids = st.button("🔍 Tìm & Chọn 4 Video", type="primary", width='stretch', key="new_btn_search_vids")
                with col_nv2:
                    btn_new_rnd_vid = st.button("🎲 1 Video Ngẫu Nhiên", type="secondary", width='stretch', key="new_btn_rnd_vid")

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
                                st.image(v_it["thumbnail"], width='stretch')
                            st.caption(f"⏱️ **{v_it['duration']}s** | 💾 **{v_it['size_mb']} MB** | 👁️ {v_it['views']:,} lượt xem")
                            if st.button(f"✅ Chọn Video #{v_i+1}", key=f"new_pick_v_{v_it['id']}", width='stretch'):
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
                            if st.button(f"✅ Chọn Video Này", key=f"new_local_vid_{l_idx}", width='stretch'):
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
            btn_new_create = st.button("🚀 TẠO VIDEO B-ROLL NGAY", type="primary", width='stretch', key="new_btn_render")
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
        st.subheader("3. Xem Trước & Tải Về")

        if st.session_state.get("new_format_mode", "").startswith("🎨"):
            # Chế độ Photo Slide
            rendered_c_vid = st.session_state.get("new_comic_rendered_video")
            rendered_c_slide = st.session_state.get("new_comic_rendered_slide")
            bg_c = st.session_state.get("new_comic_bg_image")

            if rendered_c_vid and Path(rendered_c_vid).exists():
                meta_cv = probe_video_metadata(rendered_c_vid)
                st.video(str(rendered_c_vid))
                st.markdown(
                    f"""
                    <div class="badge-meta">
                        📏 <b>1080x1920</b> &nbsp;|&nbsp; ⏱️ <b>{meta_cv['duration']}s</b> &nbsp;|&nbsp; 🎞️ <b>30fps</b> &nbsp;|&nbsp; 🔇 <b>No Audio</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with open(rendered_c_vid, "rb") as vf_cv:
                    st.download_button(
                        label="⬇️ TẢI VIDEO KEN BURNS 10S (.MP4)",
                        data=vf_cv.read(),
                        file_name="tiktok_comic_video.mp4",
                        mime="video/mp4",
                        type="primary",
                        width='stretch',
                        key="new_btn_dl_cvid",
                    )
            elif rendered_c_slide and Path(rendered_c_slide).exists():
                st.image(str(rendered_c_slide), width='stretch')
                st.markdown(
                    """
                    <div class="badge-meta">
                        📏 <b>1080x1920 (9:16)</b> &nbsp;|&nbsp; 🖼️ <b>TikTok Photo Carousel Ready</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with open(rendered_c_slide, "rb") as sf:
                    st.download_button(
                        label="⬇️ TẢI ẢNH TIKTOK PHOTO SLIDE (.JPG)",
                        data=sf.read(),
                        file_name="tiktok_photo_slide_ready.jpg",
                        mime="image/jpeg",
                        type="primary",
                        width='stretch',
                        key="new_btn_dl_cslide",
                    )
            elif bg_c and Path(bg_c).exists():
                st.caption("👁️ **Xem trước trực tiếp (Live Preview 9:16):**")
                try:
                    sig_text = f"— {st.session_state.new_signature.upper()} —" if st.session_state.new_signature else "— LẶNG —"
                    prev_slide_p = generate_retro_comic_slide(
                        image_path=bg_c,
                        quote=st.session_state.new_quote_text,
                        output_path=Path("temp/live_comic_preview.jpg"),
                        font_family=st.session_state.new_comic_font,
                        font_size=st.session_state.new_comic_font_size,
                        position=st.session_state.new_comic_position,
                        all_caps=st.session_state.new_comic_all_caps,
                        signature=sig_text,
                    )
                    st.image(str(prev_slide_p), width='stretch')
                except Exception as ex:
                    st.image(str(bg_c), width='stretch')
                st.info("👉 Nhấn **[ 🎨 XUẤT ẢNH PHOTO SLIDE ]** để lưu file 1080x1920 vào `output/kenh_moi/`.")
            else:
                st.markdown(
                    """
                    <div style="border: 2px dashed #475569; border-radius: 12px; height: 400px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                        <div><div style="font-size: 2.2rem; margin-bottom: 0.6rem;">🎨</div><b>Khung xem trước Photo Slide</b><br>Tranh minh họa 9:16 sẽ hiển thị tại đây.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
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
                        width='stretch',
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
                    st.image(str(prev_img_new), width='stretch')
                except Exception as ex:
                    logger.warning(f"Lỗi frame preview: {ex}")

                with st.expander("▶️ Phát thử video b-roll gốc", expanded=False):
                    st.video(str(new_bg))

                st.info("👉 Nhấn **[ 🚀 TẠO VIDEO B-ROLL NGAY ]** để render video chuyển động lưu vào thư mục `output/kenh_moi/`.")
            else:
                st.markdown(
                    """
                    <div style="border: 2px dashed #475569; border-radius: 12px; height: 400px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                        <div><div style="font-size: 2.2rem; margin-bottom: 0.6rem;">🎬</div><b>Khung xem trước Kênh Lặng</b><br>Video b-roll sẽ phát tại đây.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


