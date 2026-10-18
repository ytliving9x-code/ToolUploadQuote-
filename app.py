"""
Ứng dụng Web cục bộ Streamlit: TikTok Aesthetic 18s Photo & Quote Generator (app.py)
Tự động tạo và xuất video ngắn chuẩn TikTok theo phong cách:
- Ảnh tĩnh Mood Aesthetic B-roll chất lượng cao (Pixabay / Upload / Thư viện)
- Quote Typography tiếng Việt (Be Vietnam Pro SemiBold/Bold, chữ trắng bóng mờ)
- Thời lượng cố định chính xác 18 giây, không có âm thanh (No Audio) để chèn nhạc TikTok.
"""

import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import get_key, load_dotenv, set_key

from modules.pixabay_fetcher import (
    DEFAULT_DARK_KEYWORDS,
    fetch_pixabay_image,
    search_pixabay_images,
    download_and_crop_pixabay_image,
    fetch_dark_moody_image_for_quote,
)
from modules.quote_manager import (
    get_all_categories,
    get_random_quote,
    load_all_quotes,
    suggest_keywords_from_quote,
)
from modules.quote_gen import generate_quote
from modules.video_renderer import render_18s_video
from modules.video_engine import generate_quote_preview_image, probe_video_metadata
from modules.history_db import init_db

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TikTok_18s_Tool")

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="TikTok 18s Aesthetic Quote Tool",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS phong cách Aesthetic Dark Mode tối ưu cho Điện Thoại & Desktop
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-tap-highlight-color: transparent;
    }
    
    /* Tối ưu lề và padding màn hình Mobile */
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
        font-size: 2.0rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #38BDF8 60%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-header {
        color: #94A3B8;
        font-size: 0.92rem;
        margin-bottom: 1.0rem;
    }

    /* Thiết kế thẻ Card hiện đại */
    .step-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Chuẩn hóa nút bấm Mobile (Touch Target >= 46px) */
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
    
    /* Nút chính tạo video nổi bật kiểu TikTok */
    .btn-create-main button {
        background: linear-gradient(135deg, #FE2C55 0%, #FF0050 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 15px rgba(254, 44, 85, 0.4) !important;
    }

    /* Giới hạn video & ảnh xem trước không chiếm tràn màn hình dọc */
    video, .stImage img {
        max-height: 480px !important;
        width: auto !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3) !important;
    }

    /* Khung Tabs to dễ bấm trên ngón tay */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 14px !important;
        border-radius: 10px;
        font-weight: 600;
    }
    
    .badge-18s {
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
    """Đọc cấu hình từ config.json."""
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pixabay_api_key": ""}


def save_config(config: Dict[str, Any]) -> None:
    """Lưu cấu hình vào config.json."""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# Khởi tạo CSDL SQLite
init_db()
config = load_config()

# Khởi tạo session_state
if "current_quote_text" not in st.session_state:
    sample_q = get_random_quote()
    st.session_state.current_quote_text = sample_q.get("quote", "")
    st.session_state.current_keywords = sample_q.get("keywords", ["night street rain aesthetic"])

if "current_bg_image" not in st.session_state:
    # Kiểm tra xem có ảnh tải lên hoặc background sẵn không
    bg_init = Path("temp/background.jpg")
    if not bg_init.exists():
        footages = list(Path("assets/footages").glob("*.*"))
        for f in footages:
            if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                bg_init = f
                break
    st.session_state.current_bg_image = str(bg_init) if bg_init.exists() else None

if "rendered_18s_video" not in st.session_state:
    st.session_state.rendered_18s_video = None

if "current_signature" not in st.session_state:
    st.session_state.current_signature = config.get("branding", {}).get("signature", "saigonbac")

if "auto_dark_bg_enabled" not in st.session_state:
    st.session_state.auto_dark_bg_enabled = True


# ==============================================================================
# TIÊU ĐỀ CHÍNH
# ==============================================================================
st.markdown('<div class="main-header">TikTok 18s Aesthetic Photo & Quote Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Tự động dựng video tĩnh 18 giây chuẩn 9:16 (1080x1920) từ Ảnh Pixabay + Typography Tiếng Việt (No Audio, sẵn sàng chèn nhạc trending trên TikTok).</div>',
    unsafe_allow_html=True,
)

col_input, col_preview = st.columns([1.4, 1.0], gap="large")

with col_input:
    # -------------------------------------------------------------
    # 1. QUẢN LÝ QUOTE
    # -------------------------------------------------------------
    st.subheader("1. Chọn Hoặc Tự Nhập Quote")

    quote_mode = st.radio(
        "Phương thức chọn Quote:",
        options=["🤖 Dùng AI sinh mới (Gemini/OpenAI)", "📜 Dùng quote có sẵn trong kho", "✍️ Tự gõ quote theo ý bạn"],
        index=0,
        horizontal=True,
    )

    all_quotes_data = load_all_quotes()

    # Checkbox tự động tìm ảnh nền màu tối
    st.session_state.auto_dark_bg_enabled = st.checkbox(
        "🌙 **Tự động tìm ảnh nền gam màu tối phù hợp ngay khi sinh quote**",
        value=st.session_state.auto_dark_bg_enabled,
        help="Khi bật, hệ thống sẽ tự động phân tích câu quote và tải 1 ảnh nền chất lượng cao gam màu tối (đêm, mưa, phố vắng, cinematic) cập nhật ngay vào khung xem trước 9:16.",
    )

    if quote_mode == "🤖 Dùng AI sinh mới (Gemini/OpenAI)":
        st.caption("AI viết quote 'buồn một chút' cho video TikTok: tâm sự chân thật, buồn nhẹ, trầm lắng, 15–35 từ, không sến súa.")
        ai_topic_options = config.get("topics", [
            "tự mình chịu đựng",
            "giấu nỗi buồn",
            "cô đơn",
            "áp lực tiền bạc và trưởng thành",
            "cha mẹ và gia đình",
            "khó tin người",
            "cố gắng nhưng không như ý",
            "chấp nhận buông bỏ",
            "đi dạo một mình buổi tối"
        ])
        selected_ai_topic = st.selectbox("Chọn chủ đề tâm sự:", options=ai_topic_options, index=0)

        if st.button("✨ Sinh Quote Mới Bằng AI (Phong Cách Buồn Một Chút)", type="primary", use_container_width=True):
            with st.spinner(f"AI đang viết câu quote tâm sự theo chủ đề '{selected_ai_topic}'..."):
                try:
                    ai_res = generate_quote(topic=selected_ai_topic, config=config)
                    new_q = ai_res["quote"]
                    st.session_state.current_quote_text = new_q
                    if ai_res.get("pexels_keywords"):
                        kw_first = ai_res["pexels_keywords"][0]
                        st.session_state.current_keywords = ai_res["pexels_keywords"]
                        st.session_state["pix_kw_input"] = kw_first

                    # Tự động tìm ảnh nền gam màu tối nếu tính năng đang bật
                    if st.session_state.auto_dark_bg_enabled:
                        with st.spinner("Đang tìm và áp dụng ảnh nền gam màu tối phù hợp..."):
                            dark_bg = fetch_dark_moody_image_for_quote(new_q, api_key=config.get("pixabay_api_key"))
                            st.session_state.current_bg_image = str(dark_bg)
                            st.session_state.rendered_18s_video = None

                    if ai_res.get("is_ai_generated", True):
                        st.toast("Đã sinh quote & cập nhật ảnh nền tối tâm trạng thành công!", icon="✨")
                    else:
                        st.warning("⚠️ Không thể kết nối AI hoặc phát hiện trùng lặp nhiều lần. Đã lấy câu ngẫu nhiên từ kho mẫu dự phòng.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi gọi AI: {e}")

    elif quote_mode == "📜 Dùng quote có sẵn trong kho":
        col_cat, col_rnd = st.columns([1.5, 1])
        with col_cat:
            cat_choices = get_all_categories()
            chosen_cat = st.selectbox("Lọc chủ đề:", options=cat_choices, index=0)
        with col_rnd:
            st.write("")
            st.write("")
            if st.button("🎲 Random Quote Ngẫu Nhiên", use_container_width=True):
                rnd_q = get_random_quote(chosen_cat)
                new_q = rnd_q["quote"]
                st.session_state.current_quote_text = new_q
                rnd_kws = rnd_q.get("keywords", ["night street rain aesthetic"])
                st.session_state.current_keywords = rnd_kws
                st.session_state["pix_kw_input"] = rnd_kws[0]

                # Tự động tìm ảnh nền gam màu tối nếu tính năng đang bật
                if st.session_state.auto_dark_bg_enabled:
                    with st.spinner("Đang tìm và áp dụng ảnh nền gam màu tối phù hợp..."):
                        dark_bg = fetch_dark_moody_image_for_quote(new_q, api_key=config.get("pixabay_api_key"))
                        st.session_state.current_bg_image = str(dark_bg)
                        st.session_state.rendered_18s_video = None

                st.toast("Đã chọn quote & đổi ảnh nền tối tâm trạng!", icon="🎲")
                st.rerun()

        # Lọc danh sách câu để hiển thị dropdown
        filtered_quotes = (
            all_quotes_data
            if chosen_cat == "Tất cả"
            else [q for q in all_quotes_data if q.get("category") == chosen_cat]
        )
        quote_options = [q["quote"] for q in filtered_quotes]

        # Xác định index hiện tại
        default_idx = 0
        if st.session_state.current_quote_text in quote_options:
            default_idx = quote_options.index(st.session_state.current_quote_text)

        selected_dropdown_quote = st.selectbox(
            "Chọn câu trích dẫn có sẵn:",
            options=quote_options,
            index=default_idx,
        )
        st.session_state.current_quote_text = selected_dropdown_quote

    quote_input_box = st.text_area(
        "Nội dung Quote (hiển thị trên video):",
        value=st.session_state.current_quote_text,
        height=85,
        help="Chữ sẽ được vẽ căn lề trái, lề an toàn 90px, font Be Vietnam Pro trắng tinh khiết.",
    )
    st.session_state.current_quote_text = quote_input_box

    sig_input = st.text_input(
        "Chữ ký nhận diện thương hiệu nhỏ (Signature):",
        value=st.session_state.current_signature,
        placeholder="saigonbac",
        help="Chữ ký nhỏ gọn hiển thị ngay dưới câu quote (để trống nếu không muốn chèn).",
    )
    st.session_state.current_signature = sig_input.strip()

    st.divider()

    # -------------------------------------------------------------
    # 2. CHỌN ẢNH NỀN (PIXABAY / UPLOAD / THƯ VIỆN)
    # -------------------------------------------------------------
    st.subheader("2. Chọn Nguồn Ảnh Nền (Photo Khổ Dọc 9:16)")

    tab_pixabay, tab_ai_gen, tab_upload_local = st.tabs([
        "🌐 Tải Ảnh Từ Pixabay (Kho Ảnh Gốc)",
        "🎨 AI Tạo Ảnh Độc Bản (Không Cần Key)",
        "📤 Tải Ảnh Từ Máy Tính",
    ])

    # Gợi ý từ khóa chung
    suggested_kw_list = suggest_keywords_from_quote(st.session_state.current_quote_text)

    with tab_ai_gen:
        st.markdown("💡 **AI Tự Động Vẽ Ảnh Nền Độc Bản (Chuẩn khổ dọc 1080x1920, Không Đụng Hàng, Hoàn Toàn Miễn Phí):**")
        st.caption("AI sẽ phân tích câu quote và tạo ra bức tranh nghệ thuật cinematic dành riêng cho video của bạn.")

        ai_default_prompt = suggested_kw_list[0] if suggested_kw_list else "rainy city street night lonely"
        ai_prompt_input = st.text_input(
            "Mô tả khung cảnh muốn AI vẽ (hoặc dùng gợi ý theo câu quote):",
            value=ai_default_prompt,
            key="ai_img_prompt_input",
            help="Gõ tiếng Anh hoặc tiếng Việt (vd: 'mưa đêm phố vắng', 'quán cà phê khuya', 'rainy street night moody').",
        )

        btn_gen_ai_img = st.button("✨ AI Tạo Ảnh Nền Này Ngay", type="primary", use_container_width=True)
        if btn_gen_ai_img:
            with st.spinner("AI đang vẽ ảnh nghệ thuật chuẩn 1080x1920 (khoảng 3 - 5 giây)..."):
                try:
                    from modules.ai_image_gen import generate_ai_image
                    out_ai_img = generate_ai_image(
                        prompt=ai_prompt_input,
                        output_dir=Path("temp"),
                        width=1080,
                        height=1920,
                    )
                    st.session_state.current_bg_image = str(out_ai_img)
                    st.session_state.rendered_18s_video = None
                    st.toast("Đã tạo ảnh nền nghệ thuật độc bản thành công!", icon="🎨")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi tạo ảnh AI: {e}")

    with tab_pixabay:
        from modules.pixabay_fetcher import QUICK_THEMES_VI, search_pixabay_images, fetch_pixabay_image, download_and_crop_pixabay_image

        st.markdown("🎯 **Khu Vực 1: Chọn Nhanh Chủ Đề Nổi Bật (Chạm 1 Lần)**")
        
        # Khởi tạo chủ đề mặc định nếu chưa có trong session_state
        if "pix_theme_input" not in st.session_state:
            st.session_state["pix_theme_input"] = "🌧️ Mưa Phố Đêm"

        # 6 Nút bấm chọn nhanh chủ đề tiếng Việt (xếp 2 cột x 3 hàng to bản trên mobile)
        themes_list = list(QUICK_THEMES_VI.keys())
        row_cols = st.columns(2)
        for t_idx, theme_label in enumerate(themes_list):
            with row_cols[t_idx % 2]:
                if st.button(theme_label, key=f"btn_theme_vi_{t_idx}", use_container_width=True):
                    st.session_state["pix_theme_input"] = theme_label
                    st.toast(f"Đã chọn: {theme_label}", icon="✨")
                    st.rerun()

        st.write("")
        st.markdown("✍️ **Khu Vực 2: Tự Nhập Chủ Đề Bạn Muốn (Gõ Tiếng Việt Thoải Mái)**")
        user_theme_text = st.text_input(
            "Nhập chủ đề ảnh nền bạn thích:",
            key="pix_theme_input",
            placeholder="Ví dụ: con sói, cánh đồng, ga tàu, trời mưa...",
            help="Bạn có thể gõ bất kỳ từ ngữ tiếng Việt nào, hệ thống sẽ tự động hiểu và tối ưu ảnh nền.",
        )


        st.write("")
        # Nút hành động Pixabay
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            btn_search_gallery = st.button("🔍 Tìm & Chọn 4 Ảnh", type="primary", use_container_width=True)
        with col_act2:
            btn_rnd_one = st.button("🎲 1 Ảnh Ngẫu Nhiên", type="secondary", use_container_width=True)

        # Nút chọn nhanh nguồn ảnh thật Picsum Photos (Hoàn toàn miễn phí, không cần key)
        col_pic1, col_pic2 = st.columns(2)
        with col_pic1:
            btn_picsum_one = st.button("📸 1 Ảnh Thật Picsum (Không Cần Key)", use_container_width=True, help="Tải 1 ảnh thật ngẫu nhiên chất lượng cao từ kho ảnh quốc tế Picsum Photos, không cần bất kỳ API key nào.")
        with col_pic2:
            btn_picsum_gallery = st.button("🖼️ Xem 4 Ảnh Picsum Khác", use_container_width=True, help="Xem lưới 4 ảnh chụp thật từ Picsum Photos để bạn tự chọn.")

        # Quản lý số trang Pixabay để không bao giờ bị lặp ảnh
        if "pix_current_page" not in st.session_state:
            st.session_state["pix_current_page"] = 1

        # Xử lý nút [ 🔍 Tìm & Chọn 4 Ảnh ] -> Nhảy trang để liên tục đổi mới
        if btn_search_gallery:
            current_query = st.session_state.get("pix_theme_input", "mưa đêm")
            st.session_state["pix_current_page"] = (st.session_state["pix_current_page"] % 8) + 1
            curr_p = st.session_state["pix_current_page"]
            with st.spinner(f"Đang tìm 4 ảnh đẹp nhất từ Pixabay (Trang {curr_p})..."):
                gallery_hits = search_pixabay_images(
                    query=current_query,
                    api_key=config.get("pixabay_api_key"),
                    per_page=4,
                    page=curr_p,
                )
                st.session_state["pixabay_gallery_results"] = gallery_hits
                if not gallery_hits:
                    st.warning("Không tìm thấy ảnh với chủ đề này. Bạn hãy thử từ khóa khác nhé.")

        # Xử lý nút [ 🎲 1 Ảnh Ngẫu Nhiên ] Pixabay
        if btn_rnd_one:
            current_query = st.session_state.get("pix_theme_input", "mưa đêm")
            with st.spinner("Đang tải ngẫu nhiên 1 ảnh dọc 1080x1920 từ Pixabay..."):
                try:
                    fetched_img = fetch_pixabay_image(
                        query=current_query,
                        api_key=config.get("pixabay_api_key"),
                        output_path=Path("temp/background.jpg"),
                    )
                    st.session_state.current_bg_image = str(fetched_img)
                    st.session_state.rendered_18s_video = None
                    st.toast("Đã chọn ngẫu nhiên 1 ảnh nền Pixabay thành công!", icon="🎨")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        # Xử lý nút [ 📸 1 Ảnh Thật Picsum ] -> Không cần API Key
        if btn_picsum_one:
            with st.spinner("Đang tải 1 bức ảnh thật nghệ thuật mới toanh từ Picsum Photos (không cần key)..."):
                try:
                    from modules.picsum_fetcher import fetch_picsum_image
                    p_img = fetch_picsum_image(Path("temp/background.jpg"))
                    st.session_state.current_bg_image = str(p_img)
                    st.session_state.rendered_18s_video = None
                    st.toast("Đã tải ảnh thật nghệ thuật từ Picsum Photos thành công!", icon="📸")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi tải Picsum: {e}")

        # Xử lý nút [ 🖼️ Xem 4 Ảnh Picsum Khác ] -> Lấy gallery 4 ảnh Picsum
        if btn_picsum_gallery:
            with st.spinner("Đang lấy 4 ảnh chụp thật từ kho Picsum Photos..."):
                from modules.picsum_fetcher import get_picsum_gallery
                p_gallery = get_picsum_gallery(limit=4)
                st.session_state["pixabay_gallery_results"] = p_gallery
                st.toast("Đã nạp 4 ảnh thật từ Picsum!", icon="🖼️")

        # Hiển thị 4 ảnh xem trước trong lưới 2x2
        gallery_items = st.session_state.get("pixabay_gallery_results", [])
        if gallery_items:
            st.markdown("---")
            st.markdown("🖼️ **Chạm vào ảnh bạn thích nhất bên dưới:**")
            grid_cols = st.columns(2)
            for idx, item in enumerate(gallery_items[:4]):
                col_idx = idx % 2
                with grid_cols[col_idx]:
                    st.image(item["preview_url"], use_container_width=True)
                    if st.button(f"✅ Chọn Ảnh #{idx+1}", key=f"btn_pick_img_{item['id']}", use_container_width=True):
                        with st.spinner(f"Đang tải và chuẩn hóa ảnh #{idx+1} về chuẩn 1080x1920..."):
                            out_img = download_and_crop_pixabay_image(item["large_url"], Path("temp/background.jpg"))
                            st.session_state.current_bg_image = str(out_img)
                            st.session_state.rendered_18s_video = None
                            st.toast(f"Đã chọn ảnh #{idx+1} làm hình nền video!", icon="✨")
                            st.rerun()

    with tab_upload_local:
        up_file = st.file_uploader(
            "Tải file ảnh (.jpg, .png, .webp) từ máy tính hoặc điện thoại của bạn:",
            type=["jpg", "jpeg", "png", "webp"],
        )
        if up_file is not None:
            save_dir = Path("temp")
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / up_file.name
            with open(save_path, "wb") as f_up:
                f_up.write(up_file.getbuffer())

            from modules.pixabay_fetcher import resize_and_crop_to_tiktok
            crop_path = resize_and_crop_to_tiktok(save_path)
            st.session_state.current_bg_image = str(crop_path)
            st.session_state.rendered_18s_video = None
            st.success(f"✅ Đã tải và chuẩn hóa ảnh dọc: `{up_file.name}`")

    st.divider()

    # -------------------------------------------------------------
    # NÚT BẤM CHÍNH TO RÕ (TỐI ƯU NGÓN TAY CÁI TRÊN ĐIỆN THOẠI)
    # -------------------------------------------------------------
    st.markdown('<div class="btn-create-main">', unsafe_allow_html=True)
    btn_create_18s = st.button("🚀 TẠO VIDEO 18S NGAY", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if btn_create_18s:
        bg_target = st.session_state.current_bg_image
        if not bg_target or not Path(bg_target).exists():
            # Tự động tải ảnh ngẫu nhiên nếu chưa có
            with st.spinner("Đang chuẩn bị ảnh nền Pixabay..."):
                bg_target = str(fetch_pixabay_image("night street rain", config.get("pixabay_api_key")))
                st.session_state.current_bg_image = bg_target

        with st.spinner("Đang ghép typography và render video tĩnh đúng 18.0 giây..."):
            try:
                import time
                out_vid = Path(f"output/tiktok_18s_{int(time.time())}.mp4")
                render_18s_video(
                    image_path=bg_target,
                    quote=st.session_state.current_quote_text,
                    output_path=out_vid,
                    duration=18.0,
                    signature=st.session_state.current_signature or None,
                )
                st.session_state.rendered_18s_video = str(out_vid)
                st.toast("Dựng video tĩnh 18s hoàn tất 100%!", icon="🎉")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi render video: {e}")

# ==============================================================================
# CỘT PHẢI: VIDEO PREVIEW & TẢI VỀ MÁY
# ==============================================================================
with col_preview:
    st.subheader("3. Video Preview & Tải Về")

    rendered_vid = st.session_state.rendered_18s_video
    bg_curr = st.session_state.current_bg_image

    if rendered_vid and Path(rendered_vid).exists():
        meta = probe_video_metadata(rendered_vid)
        st.video(str(rendered_vid))

        st.markdown(
            f"""
            <div class="badge-18s">
                📏 <b>1080x1920</b> &nbsp;|&nbsp;
                ⏱️ <b>{meta['duration']}s</b> &nbsp;|&nbsp;
                🎞️ <b>30fps</b> &nbsp;|&nbsp;
                🔇 <b>No Audio (Mute)</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Nút tải trực tiếp về máy
        with open(rendered_vid, "rb") as vid_file:
            vid_bytes = vid_file.read()
            st.download_button(
                label="⬇️ TẢI VIDEO VỀ MÁY (.MP4)",
                data=vid_bytes,
                file_name="tiktok_18s_ready.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True,
            )
    elif bg_curr and Path(bg_curr).exists():
        st.caption("👁️ **Xem Trước Chữ Trên Ảnh Nền (Tỉ Lệ Chuẩn 9:16):**")
        try:
            preview_config = dict(config)
            preview_config["branding"] = dict(config.get("branding", {}))
            preview_config["branding"]["signature"] = st.session_state.current_signature
            preview_img_path = generate_quote_preview_image(
                image_path=bg_curr,
                quote=st.session_state.current_quote_text,
                config=preview_config,
            )
            st.image(str(preview_img_path), use_container_width=True)
        except Exception as ex:
            logger.warning(f"Lỗi khi render ảnh preview text: {ex}")
            st.image(str(bg_curr), use_container_width=True)

        st.info("👉 Bạn có thể đổi ảnh hoặc chỉnh sửa câu quote ở cột trái. Chữ sẽ tự động cập nhật ngay lập tức trên ảnh! Khi ưng ý, nhấn **[ 🚀 TẠO VIDEO 18S NGAY ]** để render video hoàn chỉnh.")
    else:
        st.markdown(
            """
            <div style="border: 2px dashed #475569; border-radius: 12px; height: 420px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem; font-size: 0.85rem;">
                <div>
                    <div style="font-size: 2.5rem; margin-bottom: 0.8rem;">📱</div>
                    <b>Khung xem trước 9:16</b><br>
                    Video 18s sau khi render sẽ phát tại đây.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


