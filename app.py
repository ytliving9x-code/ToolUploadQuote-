from __future__ import annotations

"""
Ứng dụng Web Streamlit: Sài Gòn Bạc Studio (app.py)
Tập trung 100% cho kênh Sài Gòn Bạc (saigonbac):
1. Nhập Prompt / Ý tưởng để AI sáng tác quote tĩnh tại, hoài niệm (hoặc tự gõ quote).
2. Tải ảnh nền chất lượng cao từ máy tính (tự động crop chuẩn dọc 9:16 1080x1920).
3. Live Preview chữ trên ảnh & Render Video 18s TikTok chuyển động Ken Burns chuẩn điện ảnh.
"""

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
from PIL import Image

from modules.history_db import init_db
from modules.quote_gen import (
    generate_quote_from_user_prompt,
    generate_quote_from_inspiration_image,
    review_viral_potential,
)
from modules.video_engine import (
    generate_quote_preview_image,
    probe_video_metadata,
)
from modules.video_renderer import render_18s_video

# Khởi tạo database
init_db()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SaigonBac_Studio")

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Sài Gòn Bạc - TikTok 18s Studio",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS phong cách Aesthetic Dark Mode sang trọng
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-header {
        font-size: 2.2rem;
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
        background: rgba(15, 23, 42, 0.7);
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

    .btn-create-sg button {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        min-height: 54px !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 25px -4px rgba(2, 132, 199, 0.5) !important;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .btn-create-sg button:hover {
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
        except Exception as e:
            logger.error(f"Lỗi nạp config.json: {e}")
    return {}


def save_config(cfg: Dict[str, Any]) -> None:
    """Lưu cấu hình cập nhật vào config.json."""
    cfg_path = Path("config.json")
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi ghi config.json: {e}")


def crop_image_to_tiktok_portrait(image_path: Path, target_size=(1080, 1920)) -> Path:
    """Cắt và căn giữa (Center-Crop) ảnh chính xác về khổ 1080x1920 (9:16)."""
    with Image.open(image_path) as img:
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
# KHỞI TẠO SESSION STATE
# ==============================================================================
config = load_config()

default_sample_bg = Path("assets/samples/curated_saigonbac/cafe_night.jpg")
if not default_sample_bg.exists():
    # Thử tìm ảnh bất kỳ trong folder sample
    samples_dir = Path("assets/samples/curated_saigonbac")
    if samples_dir.exists():
        found = list(samples_dir.glob("*.jpg"))
        if found:
            default_sample_bg = found[0]

if "sg_quote_text" not in st.session_state:
    st.session_state.sg_quote_text = ""
if "sg_user_prompt" not in st.session_state:
    st.session_state.sg_user_prompt = ""
if "sg_bg_image" not in st.session_state:
    st.session_state.sg_bg_image = str(default_sample_bg) if default_sample_bg.exists() else None
if "sg_rendered_video" not in st.session_state:
    st.session_state.sg_rendered_video = None
if "sg_signature" not in st.session_state:
    st.session_state.sg_signature = config.get("branding", {}).get("signature", "saigonbac")
if "sg_antiglare_level" not in st.session_state:
    st.session_state.sg_antiglare_level = "Vừa Phải (Khuyên Dùng)"
if "sg_toggle_antiglare" not in st.session_state:
    st.session_state.sg_toggle_antiglare = True


# ==============================================================================
# SIDEBAR: CẤU HÌNH & THIẾT LẬP KÊNH
# ==============================================================================
with st.sidebar:
    st.markdown("### ☕ Sài Gòn Bạc Settings")
    st.caption("Cấu hình thương hiệu & chất lượng video")

    # Kiểm tra API Key
    has_gemini = bool(os.getenv("GEMINI_API_KEY") or (hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets))
    if has_gemini:
        st.success("✅ Gemini API: Đã kết nối", icon="✨")
    else:
        st.warning("⚠️ Chưa có GEMINI_API_KEY trong .env", icon="🔑")

    st.divider()

    st.markdown("**1. Thương Hiệu Nhận Diện**")
    sig_input = st.text_input(
        "Chữ ký video (Signature):",
        value=st.session_state.sg_signature,
        key="sb_sig_input",
    )
    if sig_input != st.session_state.sg_signature:
        st.session_state.sg_signature = sig_input
        config.setdefault("branding", {})["signature"] = sig_input
        save_config(config)

    st.markdown("**2. Bộ Lọc Chống Loá Chữ**")
    st.session_state.sg_toggle_antiglare = st.checkbox(
        "Bật lớp Gradient Scrim chống loá",
        value=st.session_state.sg_toggle_antiglare,
        help="Thêm lớp phủ dốc mềm mại ở đáy giúp chữ luôn dễ đọc trên mọi bức ảnh sáng hay tối.",
    )
    st.session_state.sg_antiglare_level = st.selectbox(
        "Cường độ chống loá:",
        options=["Vừa Phải (Khuyên Dùng)", "Mạnh (Cho Nền Rất Sáng/Chói)", "Nhẹ (Cho Nền Tối)"],
        index=0,
    )

    st.markdown("**3. Cấu Hình AI**")
    sel_model = st.selectbox(
        "Gemini Model:",
        options=["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-lite-latest"],
        index=0,
    )
    if sel_model != config.get("gemini_model"):
        config["gemini_model"] = sel_model
        save_config(config)

    st.divider()
    out_dir = Path("output/saigonbac")
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_videos = list(out_dir.glob("*.mp4"))
    st.markdown(f"📁 **Thư mục xuất:** `output/saigonbac/` ({len(existing_videos)} video)")
    st.caption("Định dạng video: 1080x1920 (9:16), 30fps, H.264, 18.0s không tiếng.")


# ==============================================================================
# GIAO DIỆN CHÍNH (MAIN WORKSPACE)
# ==============================================================================
st.markdown('<div class="main-header">☕ SÀI GÒN BẠC STUDIO</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Trạm dừng cảm xúc — Tạo video tĩnh 18s TikTok: Tự nhập Prompt cho AI viết quote + Tải ảnh nền chất lượng cao từ máy tính.</div>',
    unsafe_allow_html=True,
)

col_input, col_preview = st.columns([1.35, 1.0], gap="large")

# ==============================================================================
# CỘT TRÁI: BƯỚC 1 (QUOTE) & BƯỚC 2 (ẢNH NỀN)
# ==============================================================================
with col_input:
    # --- BƯỚC 1: QUOTE ---
    with st.container():
        st.markdown('<div class="step-badge">BƯỚC 1</div>', unsafe_allow_html=True)
        st.subheader("Nhập Prompt / AI Sáng Tác Quote")

        tab_prompt_text, tab_prompt_img = st.tabs([
            "✍️ Nhập Prompt Bằng Chữ",
            "🖼️ Copy Ý Tưởng Từ Ảnh (Gửi Ảnh Có Chữ)",
        ])

        with tab_prompt_text:
            user_prompt_input = st.text_area(
                "Nhập Prompt của bạn cho AI:",
                value=st.session_state.sg_user_prompt,
                placeholder="Gõ prompt tự do của bạn tại đây... (Ví dụ: Hãy viết 1 câu quote ngắn 20 từ về sự im lặng của người trưởng thành khi rời đi, câu từ sâu sắc, không sến)",
                height=90,
                key="sb_prompt_area",
            )
            st.session_state.sg_user_prompt = user_prompt_input

            btn_ai_gen = st.button("✨ GỬI PROMPT CHO AI VIẾT QUOTE", type="primary", use_container_width=True, key="btn_prompt_text")
            if btn_ai_gen:
                if not st.session_state.sg_user_prompt.strip():
                    st.warning("⚠️ Vui lòng nhập nội dung prompt của bạn vào ô trên trước khi bấm gửi.")
                else:
                    with st.spinner("AI đang viết câu quote theo đúng prompt của bạn..."):
                        try:
                            res = generate_quote_from_user_prompt(
                                user_prompt=st.session_state.sg_user_prompt,
                                config=config,
                            )
                            st.session_state.sg_quote_text = res["quote"]
                            st.session_state.sg_rendered_video = None
                            st.toast("AI đã viết xong câu quote theo prompt của bạn!", icon="✨")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi gọi AI: {e}")

        with tab_prompt_img:
            st.caption("📸 **Tải ảnh có chữ/quote bạn thích (từ TikTok, Facebook, Pinterest...)**. AI Vision sẽ đọc nội dung trong ảnh và sáng tác lại 1 câu tương tự về ý tưởng, phong cách nhưng độc bản.")
            insp_file = st.file_uploader(
                "Chọn file ảnh chụp màn hình / ảnh có chữ (.jpg, .png, .webp):",
                type=["jpg", "jpeg", "png", "webp"],
                key="sb_insp_uploader",
            )
            if insp_file is not None:
                st.image(insp_file, caption="Ảnh tham khảo đã chọn", width=220)

            insp_note = st.text_input(
                "Ghi chú thêm cho AI (Tùy chọn):",
                placeholder="Ví dụ: Giữ ý chính nhưng viết giọng trầm hơn, sâu sắc hơn...",
                key="sb_insp_note_input",
            )

            btn_insp_gen = st.button("🔍 ĐỌC CHỮ TRONG ẢNH & VIẾT QUOTE TƯƠNG TỰ", type="primary", use_container_width=True, key="btn_prompt_insp")
            if btn_insp_gen:
                if insp_file is None:
                    st.warning("⚠️ Vui lòng tải lên 1 bức ảnh có chữ để AI phân tích.")
                else:
                    with st.spinner("AI Vision đang đọc chữ trong ảnh và sáng tác câu quote tương tự..."):
                        try:
                            file_bytes = insp_file.getvalue()
                            res = generate_quote_from_inspiration_image(
                                image_input=file_bytes,
                                custom_instruction=insp_note,
                                config=config,
                            )
                            st.session_state.sg_quote_text = res["quote"]
                            st.session_state.sg_rendered_video = None
                            st.toast("AI đã đọc ảnh và sáng tác câu quote tương tự thành công!", icon="🎉")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi phân tích ảnh: {e}")

        # Ô chỉnh sửa câu quote trực tiếp
        current_quote = st.text_area(
            "Câu quote sẽ hiển thị trên video (hoặc bạn có thể tự gõ/dán câu vào đây):",
            value=st.session_state.sg_quote_text,
            placeholder="Câu quote sau khi AI viết sẽ xuất hiện tại đây, hoặc bạn có thể tự gõ/dán trực tiếp vào đây...",
            height=100,
            key="sb_quote_text_area",
        )
        if current_quote != st.session_state.sg_quote_text:
            st.session_state.sg_quote_text = current_quote
            st.session_state.sg_rendered_video = None

        # Đếm từ trực quan nếu có text
        if current_quote.strip():
            words = current_quote.strip().split()
            word_count = len(words)
            if 15 <= word_count <= 26:
                st.markdown(
                    f'<span class="word-badge-ok">✓ Độ dài lý tưởng: <b>{word_count} từ</b> (chuẩn 15 - 26 từ cho video 18s).</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="word-badge-warn">ℹ️ Hiện tại: <b>{word_count} từ</b>. Khuyên dùng từ 15 đến 26 từ để người xem kịp đọc trọn vẹn và bố cục chữ cân đối nhất.</span>',
                    unsafe_allow_html=True,
                )


    st.write("")

    # --- BƯỚC 2: ẢNH NỀN TẢI TỪ MÁY ---
    with st.container():
        st.markdown('<div class="step-badge">BƯỚC 2</div>', unsafe_allow_html=True)
        st.subheader("Chọn / Tải Ảnh Nền Từ Máy Tính")
        st.caption("Tải file ảnh đẹp (.jpg, .png, .webp). Hệ thống sẽ tự động crop và căn giữa chuẩn dọc 9:16 (1080x1920).")

        up_file = st.file_uploader(
            "Kéo thả hoặc duyệt file ảnh từ máy của bạn:",
            type=["jpg", "jpeg", "png", "webp"],
            key="sb_file_uploader",
        )
        if up_file is not None:
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            save_path = temp_dir / up_file.name
            with open(save_path, "wb") as f_out:
                f_out.write(up_file.getbuffer())

            # Chuẩn hoá kích thước 1080x1920
            crop_path = crop_image_to_tiktok_portrait(save_path)
            st.session_state.sg_bg_image = str(crop_path)
            st.session_state.sg_rendered_video = None
            st.toast(f"Đã nạp và chuẩn hóa ảnh: {up_file.name}", icon="📸")

        # Nút nạp nhanh ảnh mẫu nếu cần
        if default_sample_bg.exists():
            with st.expander("Gợi ý: Dùng ảnh mẫu có sẵn trong kho", expanded=False):
                st.caption(f"Ảnh mẫu hiện tại: `{default_sample_bg.name}`")
                if st.button("🔄 Nạp lại ảnh mẫu này", key="sb_btn_reset_sample"):
                    st.session_state.sg_bg_image = str(default_sample_bg)
                    st.session_state.sg_rendered_video = None
                    st.toast("Đã nạp ảnh mẫu saigonbac!", icon="☕")
                    st.rerun()

    st.write("")
    st.divider()

    # --- NÚT HÀNH ĐỘNG RENDER VIDEO ---
    st.markdown('<div class="btn-create-sg">', unsafe_allow_html=True)
    btn_create_video = st.button("🚀 TẠO VIDEO SAIGONBAC 18S", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if btn_create_video:
        bg_target = st.session_state.sg_bg_image
        if not bg_target or not Path(bg_target).exists():
            st.error("Chưa có ảnh nền! Vui lòng tải một file ảnh từ máy tính ở Bước 2.")
        elif not st.session_state.sg_quote_text.strip():
            st.error("Câu quote đang trống! Vui lòng nhập quote ở Bước 1.")
        else:
            out_folder = Path("output/saigonbac")
            out_folder.mkdir(parents=True, exist_ok=True)
            out_vid = out_folder / f"tiktok_saigonbac_{int(time.time())}.mp4"

            with st.spinner("Đang ghép typography và render video 18.0s chuyển động Ken Burns cho saigonbac..."):
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


# ==============================================================================
# CỘT PHẢI: BƯỚC 3 (LIVE PREVIEW & XUẤT VIDEO)
# ==============================================================================
with col_preview:
    st.markdown('<div class="step-badge">BƯỚC 3</div>', unsafe_allow_html=True)
    st.subheader("Xem Trước Chữ Trên Ảnh & Video")

    rendered_vid = st.session_state.sg_rendered_video
    bg_img = st.session_state.sg_bg_image
    quote_ready = bool(st.session_state.sg_quote_text.strip())

    # 1. Luôn hiển thị ảnh xem trước có chữ trực tiếp
    if bg_img and Path(bg_img).exists():
        if quote_ready:
            st.caption("👁️ **Ảnh xem trước có chữ (Live Typography 9:16 - Hiển thị chữ tức thì):**")
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
                prev_img = generate_quote_preview_image(image_path=bg_img, quote=st.session_state.sg_quote_text, config=prev_cfg)
                st.image(str(prev_img), use_container_width=True)
            except Exception as ex:
                st.image(str(bg_img), use_container_width=True)
        else:
            st.image(str(bg_img), use_container_width=True)
            st.caption("🖼️ Ảnh nền đã sẵn sàng. Hãy nhập câu quote ở Bước 1 để hiển thị chữ trên ảnh.")

    else:
        st.markdown(
            """
            <div style="border: 2px dashed #475569; border-radius: 14px; height: 380px; display: flex; align-items: center; justify-content: center; color: #94A3B8; text-align: center; padding: 1.5rem;">
                <div>
                    <div style="font-size: 2.5rem; margin-bottom: 0.6rem;">📱</div>
                    <b>Khung Xem Trước Sài Gòn Bạc</b><br>
                    <span style="font-size: 0.88rem; color: #64748B;">Hãy tải lên một bức ảnh ở Bước 2 để hiển thị chữ trên ảnh.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Hiển thị Video thành phẩm bên dưới (nếu đã bấm render)
    if rendered_vid and Path(rendered_vid).exists():
        st.divider()
        st.markdown("🎬 **Video 18s Đã Tạo (Chữ xuất hiện ngay từ giây 0):**")
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
                label="⬇️ TẢI VIDEO SAIGONBAC (.MP4)",
                data=vf.read(),
                file_name=f"tiktok_saigonbac_{int(time.time())}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True,
                key="sb_btn_download",
            )
        st.caption(f"Đã lưu tại: `{rendered_vid}`")

