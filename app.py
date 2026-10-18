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

# Import các modules chức năng
from modules.pixabay_fetcher import DEFAULT_DARK_KEYWORDS, fetch_pixabay_image
from modules.quote_manager import (
    get_all_categories,
    get_random_quote,
    load_all_quotes,
    suggest_keywords_from_quote,
)
from modules.quote_gen import generate_quote
from modules.video_renderer import render_18s_video
from modules.video_engine import probe_video_metadata
from modules.exporter import export_to_pending, list_pending_items, mark_as_published
from modules.history_db import get_history, init_db

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

# Custom CSS phong cách Aesthetic Dark Mode
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, #F8FAFC 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-header {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    
    .badge-18s {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
        font-size: 0.85rem;
        text-align: center;
        color: #38BDF8;
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


# ==============================================================================
# SIDEBAR: CẤU HÌNH NHANH PIXABAY API KEY
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Cấu Hình Pixabay API")
    st.caption("Khóa API miễn phí dùng để tìm và tải ảnh nền khổ dọc từ Pixabay.")

    curr_pixabay_key = config.get("pixabay_api_key", "")
    input_pixabay_key = st.text_input(
        "Pixabay API Key:",
        value=curr_pixabay_key,
        type="password",
        help="Đăng ký tài khoản miễn phí tại pixabay.com và lấy API Key trong phần API Docs.",
    )

    if st.button("💾 Lưu Pixabay API Key", use_container_width=True):
        config["pixabay_api_key"] = input_pixabay_key.strip()
        save_config(config)
        st.success("Đã lưu API Key thành công!")
        st.toast("Đã cập nhật Pixabay Key!", icon="🔐")

    st.markdown("---")
    st.markdown(
        """
        **Hướng dẫn lấy API Key Pixabay:**
        1. Đăng ký tại: [pixabay.com](https://pixabay.com/)
        2. Truy cập [pixabay.com/api/docs](https://pixabay.com/api/docs/)
        3. Kéo xuống mục **Search Images** để copy key và dán vào đây!
        *(Nếu chưa có key, Tool vẫn tự động dùng kho ảnh Aesthetic chất lượng cao).*
        """
    )
    st.markdown("---")
    st.caption("Phiên bản: **v2.0 (Pixabay 18s Static Aesthetic)**")


# ==============================================================================
# TIÊU ĐỀ CHÍNH
# ==============================================================================
st.markdown('<div class="main-header">TikTok 18s Aesthetic Photo & Quote Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Tự động dựng video tĩnh 18 giây chuẩn 9:16 (1080x1920) từ Ảnh Pixabay + Typography Tiếng Việt (No Audio, sẵn sàng chèn nhạc trending trên TikTok).</div>',
    unsafe_allow_html=True,
)

tab_maker, tab_pending_list, tab_history_list = st.tabs(
    ["🚀 Tạo Video 18 Giây", "📥 Hàng Chờ Đăng", "📊 Lịch Sử"]
)

# ==============================================================================
# TAB 1: TẠO VIDEO 18 GIÂY
# ==============================================================================
with tab_maker:
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

        if quote_mode == "🤖 Dùng AI sinh mới (Gemini/OpenAI)":
            col_ai_top, col_ai_btn = st.columns([1.5, 1])
            with col_ai_top:
                ai_topic = st.selectbox(
                    "Chọn chủ đề muốn AI viết:",
                    options=["điềm tĩnh", "tiền bạc", "nỗ lực", "chữa lành", "văn phòng"],
                    index=0,
                    help="AI sẽ nhập vai người 27-35 tuổi, lăn lộn cơm áo gạo tiền, câu chữ trần trụi gãy gọn 15-26 từ.",
                )
            with col_ai_btn:
                st.write("")
                st.write("")
                if st.button("✨ Sinh Quote AI Mới", type="primary", use_container_width=True):
                    with st.spinner("AI đang viết câu quote sâu sắc (chuẩn 15-28 từ)..."):
                        try:
                            ai_res = generate_quote(topic=ai_topic)
                            st.session_state.current_quote_text = ai_res["quote"]
                            if ai_res.get("pexels_keywords"):
                                kw_first = ai_res["pexels_keywords"][0]
                                st.session_state.current_keywords = ai_res["pexels_keywords"]
                                st.session_state["uns_kw_input"] = kw_first
                                st.session_state["pix_kw_input"] = kw_first
                            if ai_res.get("is_ai_generated", True):
                                st.toast("Đã dùng Gemini sáng tạo quote mới thành công!", icon="✨")
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
                    st.session_state.current_quote_text = rnd_q["quote"]
                    rnd_kws = rnd_q.get("keywords", ["night street rain aesthetic"])
                    st.session_state.current_keywords = rnd_kws
                    st.session_state["uns_kw_input"] = rnd_kws[0]
                    st.session_state["pix_kw_input"] = rnd_kws[0]
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
            help="Chữ sẽ được vẽ căn giữa, lề an toàn 100px, font Be Vietnam Pro SemiBold trắng tinh kèm bóng đen mờ mềm mại.",
        )
        st.session_state.current_quote_text = quote_input_box

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
            st.markdown("💡 **Từ khóa gợi ý khớp nhất với câu quote hiện tại:**")
            cols_chips = st.columns(min(len(suggested_kw_list), 4))
            for i, kw_item in enumerate(suggested_kw_list[:4]):
                with cols_chips[i]:
                    if st.button(f"👉 {kw_item}", key=f"chip_kw_{i}", use_container_width=True):
                        st.session_state.current_keywords = [kw_item]
                        st.session_state["pix_kw_input"] = kw_item
                        st.rerun()

            st.write("")
            col_kw, col_btn_pix = st.columns([2, 1])
            with col_kw:
                default_kw = suggested_kw_list[0] if suggested_kw_list else "night street rain"
                if st.session_state.current_keywords:
                    default_kw = st.session_state.current_keywords[0]
                if "pix_kw_input" not in st.session_state:
                    st.session_state["pix_kw_input"] = default_kw

                kw_input = st.text_input(
                    "Từ khóa tìm kiếm bổ sung trên Pixabay:",
                    key="pix_kw_input",
                    help="Bạn có thể gõ thêm từ khóa (ví dụ: 'rain', 'lonely', 'city') hoặc click vào các gợi ý ở trên.",
                )
            with col_btn_pix:
                st.write("")
                st.write("")
                btn_rnd_kw = st.button("🎲 Đổi Gợi Ý Khác", key="btn_rnd_pix", use_container_width=True)
                if btn_rnd_kw:
                    new_kw = random.choice(DEFAULT_DARK_KEYWORDS)
                    st.session_state.current_keywords = [new_kw]
                    st.session_state["pix_kw_input"] = new_kw
                    st.rerun()

            # Bộ lọc Pixabay: Mặc định tông màu tự nhiên (all) và tiền tố để trống để ảnh phong phú
            with st.expander("⚙️ Tùy Chỉnh Bộ Lọc Ảnh (Tông màu, Khổ ảnh)", expanded=False):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    pix_orientation = st.selectbox(
                        "Khổ ảnh (Orientation):",
                        options=["vertical", "all", "horizontal"],
                        index=0,
                        help="vertical: chỉ lấy ảnh dọc 9:16 phù hợp với TikTok.",
                    )
                with col_f2:
                    pix_colors = st.selectbox(
                        "Tông màu (Colors):",
                        options=["all (tự nhiên, đa dạng)", "black (đen/tối)", "grayscale (đen trắng)", "blue (xanh lạnh)"],
                        index=0,
                        help="Mặc định để 'all' để ảnh phong phú và đẹp nhất.",
                    )
                with col_f3:
                    pix_prefix = st.text_input(
                        "Tiền tố chủ đề (nếu muốn ghép thêm):",
                        value="",
                        help="Để trống để tìm chính xác từ khóa bạn muốn, hoặc gõ 'night', 'moody'...",
                    )

            # Nút tìm kiếm ảnh để hiện Gallery
            col_b1, col_b2 = st.columns([1.5, 1])
            with col_b1:
                btn_search_gallery = st.button("🔍 Tìm Danh Sách Ảnh Để Chọn", type="primary", use_container_width=True)
            with col_b2:
                btn_rnd_one = st.button("🎲 Tải Ngẫu Nhiên 1 Ảnh", type="secondary", use_container_width=True)

            # Lấy color param chuẩn
            color_param = None
            if "black" in pix_colors:
                color_param = "black"
            elif "grayscale" in pix_colors:
                color_param = "grayscale"
            elif "blue" in pix_colors:
                color_param = "blue"

            # Xử lý nút tìm danh sách ảnh gallery
            if btn_search_gallery:
                with st.spinner("Đang tìm các ảnh đẹp nhất từ Pixabay..."):
                    from modules.pixabay_fetcher import search_pixabay_images
                    search_q = f"{pix_prefix.strip()} {kw_input.strip()}".strip() if pix_prefix else kw_input.strip()
                    gallery_hits = search_pixabay_images(
                        query=search_q,
                        api_key=config.get("pixabay_api_key"),
                        colors=color_param,
                        orientation=pix_orientation,
                        per_page=8,
                    )
                    st.session_state["pixabay_gallery_results"] = gallery_hits
                    if not gallery_hits:
                        st.warning("Không tìm thấy ảnh với từ khóa này. Bạn hãy thử từ khóa khác nhé.")

            # Xử lý nút tải ngẫu nhiên 1 ảnh
            if btn_rnd_one:
                with st.spinner("Đang tải ngẫu nhiên 1 ảnh dọc 1080x1920..."):
                    try:
                        search_q = f"{pix_prefix.strip()} {kw_input.strip()}".strip() if pix_prefix else kw_input.strip()
                        fetched_img = fetch_pixabay_image(
                            query=search_q,
                            api_key=config.get("pixabay_api_key"),
                            output_path=Path("temp/background.jpg"),
                            colors=color_param,
                            orientation=pix_orientation,
                        )
                        st.session_state.current_bg_image = str(fetched_img)
                        st.session_state.rendered_18s_video = None
                        st.toast("Đã chọn ngẫu nhiên 1 ảnh nền thành công!", icon="🎨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            # Hiển thị Gallery xem trước để người dùng chọn
            gallery_items = st.session_state.get("pixabay_gallery_results", [])
            if gallery_items:
                st.markdown("---")
                st.markdown("🖼️ **Bấm vào nút bên dưới bức ảnh bạn ưng ý nhất để chọn:**")
                grid_cols = st.columns(4)
                for idx, item in enumerate(gallery_items):
                    col_idx = idx % 4
                    with grid_cols[col_idx]:
                        st.image(item["preview_url"], use_container_width=True)
                        if st.button(f"✅ Chọn Ảnh #{idx+1}", key=f"btn_pick_img_{item['id']}", use_container_width=True):
                            with st.spinner(f"Đang tải và chuẩn hóa ảnh #{idx+1} về chuẩn 1080x1920..."):
                                from modules.pixabay_fetcher import download_and_crop_pixabay_image
                                out_img = download_and_crop_pixabay_image(item["large_url"], Path("temp/background.jpg"))
                                st.session_state.current_bg_image = str(out_img)
                                st.session_state.rendered_18s_video = None
                                st.toast(f"Đã chọn ảnh #{idx+1} làm hình nền video!", icon="✨")
                                st.rerun()


        with tab_upload_local:
            up_file = st.file_uploader(
                "Tải file ảnh (.jpg, .png, .webp) từ máy tính của bạn:",
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
        # NÚT BẤM CHÍNH TO RÕ: TẠO VIDEO 18S NGAY
        # -------------------------------------------------------------
        btn_create_18s = st.button("🚀 TẠO VIDEO 18S NGAY", type="primary", use_container_width=True)

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

            st.write("")
            if st.button("📦 Lưu Vào Thư Mục Chờ Đăng", use_container_width=True):
                try:
                    q_data_export = {
                        "quote": st.session_state.current_quote_text,
                        "caption": f"{st.session_state.current_quote_text}\nNuốt mệt mỏi vào trong rồi bước tiếp. 🌧️",
                        "hashtags": ["#tamtrang", "#chill", "#phattrienbanthan", "#truongthanh", "#comaogaotien"],
                    }
                    mp4_f, txt_f = export_to_pending(
                        rendered_video_path=rendered_vid,
                        quote_data=q_data_export,
                    )
                    st.success(f"Đã lưu vào chờ đăng: `{mp4_f.name}`")
                    st.toast(f"Đã lưu vào hàng chờ: {mp4_f.name}", icon="📦")
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

        elif bg_curr and Path(bg_curr).exists():
            st.caption("🖼️ Ảnh nền đang chọn (Chưa render video):")
            st.image(str(bg_curr), use_container_width=True)
            st.info("👉 Nhấn nút **[ 🚀 TẠO VIDEO 18S NGAY ]** ở bên trái để xuất video hoàn chỉnh!")
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


# ==============================================================================
# TAB 2: HÀNG CHỜ ĐĂNG
# ==============================================================================
with tab_pending_list:
    st.subheader("Quản Lý Video Chờ Đăng")
    pending_items = list_pending_items()

    if not pending_items:
        st.info("Hiện chưa có video nào trong hàng chờ đăng. Hãy tạo video ở Tab 1 và bấm 'Lưu Vào Thư Mục Chờ Đăng'.")
    else:
        st.caption(f"Tổng cộng: **{len(pending_items)} video** sẵn sàng để đăng lên TikTok.")
        for idx, item in enumerate(pending_items):
            created_str = item.get("created_time", "")
            with st.expander(f"📁 {item['name']} ({created_str})", expanded=False):
                col_v, col_info = st.columns([1, 1.5])
                with col_v:
                    if Path(item["video_path"]).exists():
                        st.video(str(item["video_path"]))
                with col_info:
                    st.text_area("Caption & Hashtags:", value=item["caption"], height=120, key=f"cap_{idx}")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        with open(item["video_path"], "rb") as f_d:
                            st.download_button(
                                "⬇️ Tải Video Này",
                                data=f_d.read(),
                                file_name=Path(item["video_path"]).name,
                                mime="video/mp4",
                                key=f"dl_{idx}",
                                use_container_width=True,
                            )
                    with col_p2:
                        if st.button("✅ Đánh dấu Đã Đăng", key=f"mark_{idx}", use_container_width=True):
                            mark_as_published(item["video_path"])
                            st.toast("Đã chuyển trạng thái Đã Đăng!", icon="✅")
                            st.rerun()


# ==============================================================================
# TAB 3: LỊCH SỬ SẢN XUẤT
# ==============================================================================
with tab_history_list:
    st.subheader("Lịch Sử Sản Xuất Video")
    history_records = get_history(limit=50)

    if not history_records:
        st.info("Chưa có lịch sử sản xuất video nào được ghi nhận.")
    else:
        st.caption(f"Hiển thị {len(history_records)} video gần nhất.")
        st.dataframe(
            history_records,
            column_config={
                "id": "ID",
                "created_at": "Thời Gian",
                "topic": "Chủ Đề",
                "quote": "Nội Dung Quote",
                "video_path": "Đường Dẫn",
                "status": "Trạng Thái",
            },
            use_container_width=True,
            hide_index=True,
        )
