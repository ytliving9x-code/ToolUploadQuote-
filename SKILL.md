---
name: tiktok-quote-studio
description: Hướng dẫn chuyên sâu và quy chuẩn kỹ thuật cho dự án TikTok Quote Studio 18s (ToolUploalQuote). Dành cho AI/Agent đọc hiểu kiến trúc, luồng render video tĩnh 18s, cơ chế chống loá typography, thanh kéo độ tối nền (dark overlay 50%) và bộ sinh caption/hashtag.
---

# 🎬 TikTok Quote Studio 18s — AI Agent Developer Blueprint

Tài liệu này là cẩm nang quy chuẩn dành cho **AI Assistant và Agent** khi tiếp nhận, bảo trì, debug hoặc phát triển tính năng mới cho kho mã nguồn **`ToolUploalQuote`**.

---

## 📌 1. Bối Cảnh & Mục Tiêu Cốt Lõi Của Dự Án

- **Mục tiêu sản phẩm**: Tự động hóa quá trình sản xuất video ngắn TikTok dạng **Aesthetic Quote 18 giây** chất lượng cao từ hình ảnh nền của người dùng và câu trích dẫn tâm trạng.
- **Đối tượng người dùng**: Người sáng tạo nội dung TikTok (TikTok Creators) xây kênh video tâm sự, triết lý sống, độc thoại đêm muộn.
- **2 Nguyên tắc sống còn của thuật toán TikTok**:
  1. **Thời lượng 18.0s cố định**: Tối ưu tỷ lệ xem hết (Completion Rate).
  2. **Không có âm thanh (`No Audio / -an`)**: Video xuất ra cố ý **tắt hoàn toàn audio track**. Người dùng sẽ gắn nhạc thịnh hành (Trending Sound) trực tiếp trong app TikTok khi đăng bài để được thuật toán đẩy lên tab Đề xuất (For You Page).

---

## 🏗️ 2. Bản Đồ Kiến Trúc File (Architecture Mapping)

```text
ToolUploalQuote/
├── app.py                      # UI Streamlit chính: Xử lý State, Input, Slider, Live Preview, Hero Button
├── config.json                 # Cấu hình thông số mặc định (branding signature, typography, render)
├── packages.txt                # Khai báo FFmpeg cho môi trường Cloud (Linux)
├── requirements.txt            # Danh sách thư viện Python
├── README.md                   # Tài liệu hướng dẫn sử dụng sản phẩm cho người dùng
├── SKILL.md                    # Cẩm nang quy chuẩn cho AI / Agent
│
├── modules/
│   ├── __init__.py             # Package init
│   ├── video_engine.py         # Đo metadata video (width, height, duration, fps) qua FFprobe
│   └── video_renderer.py       # Engine vẽ chữ Pillow & render video 18.0s bằng FFmpeg
│
├── assets/fonts/               # Bộ font tiếng Việt TrueType (BeVietnamPro, Montserrat, PlayfairDisplay, Itim)
├── output/saigonbac/           # Nơi lưu thành phẩm: cặp file .mp4 và .txt caption đi kèm
└── temp/                       # Thư mục tạm lưu ảnh crop 9:16 và PNG overlay
```

---

## ⚙️ 3. Chi Tiết Các Module Kỹ Thuật

### A. Giao Diện & Điều Khiển (`app.py`)
- **Giao diện**: Xây dựng bằng Streamlit với giao diện Dark Glassmorphism cao cấp, chia làm 2 cột:
  - **Cột Trái (Input & Cấu hình)**:
    - *Bước 1*: Ô nhập quote với đếm từ thời gian thực (chuẩn 15 - 26 từ).
    - *Bước 2*: File uploader tải ảnh (`.jpg`, `.png`, `.webp`, `.jfif`), tự động Center-Crop về 1080x1920.
    - *Bước 3*: Expander tùy chọn:
      - 🌙 **Thanh trượt độ tối hình nền (Dark Overlay)**: Từ 0% đến 90%, **mặc định 50%**.
      - 🔤 **Phông chữ**: `Be Vietnam Pro Bold`, `Montserrat Black`, `Montserrat Bold`, `Playfair Display Bold`, `Itim`.
      - 🛡️ **Mức chống loá**: Chuẩn Điện Ảnh, Siêu Chống Loá, Tự Nhiên.
      - ✍️ **Chữ ký kênh (Signature)**: Tùy chỉnh (mặc định `saigonbac`).
    - *Nút Hero*: `"✨ XUẤT VIDEO TIKTOK 18S CHUẨN HD"`.
  - **Cột Phải (Live Preview & Tải xuống)**:
    - Khung **Phone Mockup 9:16**: Hiển thị Live Preview chữ và ảnh nền thời gian thực.
    - Áp dụng độ tối nền trực tiếp bằng Pillow `Image.alpha_composite` ngay khi người dùng kéo thanh trượt.
    - Khung **"📋 Caption & Hashtags Đăng TikTok"**: Câu quote ở trên, bộ hashtag trending ở dưới (`#{signature} #tamtrang #suyngam #trietlycuocsong #cuocsong #xuhuong #fyp #viral #quotesvn #chill`) kèm nút Copy 1-click.
    - Tự động tạo file `.txt` cùng tên với video trong thư mục `output/saigonbac/`.

### B. Engine Render Video & Typography (`modules/video_renderer.py`)
- **`get_vietnamese_font(font_size, font_path)`**: Nạp font TrueType từ `assets/fonts/`, có cơ chế fallback an toàn sang `arial.ttf` hoặc default font.
- **`wrap_quote_to_lines(text, font, max_width=880)`**: Tự động ngắt dòng thông minh, không cắt đôi từ ngữ, bảo đảm nằm trong vùng an toàn Safe Zone của TikTok (chiều rộng tối đa 880px).
- **`create_quote_overlay(...)`**: Tạo lớp ảnh chữ trong suốt RGBA (1080x1920) tích hợp bộ 3 chống loá:
  1. *Gradient Scrim*: Chuyển mờ đen ở đáy màn hình.
  2. *Bóng kép đa tầng (Dual-layer Shadow)*: Lớp 1 (Tight shadow bán kính 1.2px) + Lớp 2 (Soft ambient shadow bán kính 4.5px).
  3. *Micro-stroke 1px*: Nét viền mảnh màu tối chống tán xạ ánh sáng (anti-halation).
- **`render_18s_video(...)`**:
  - Thời lượng: Cố định 18.0 giây.
  - Tỷ lệ: 1080 x 1920 (9:16).
  - Codec: `libx264`, preset `slow`, CRF `16` (chất lượng nén tiệm cận lossless).
  - Pixel format: `yuv420p` (tương thích 100% Android & iOS).
  - Filter chuỗi FFmpeg:
    ```text
    scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,
    crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,
    zoompan=z='min(zoom+0.000111,1.06)':d=540:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,
    eq=contrast=1.16:brightness=-0.12:saturation=0.92,colorbalance=...,
    vignette=PI/5.5,
    drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity:.2f}:t=fill,
    fps=30[bg];
    [1:v]format=rgba[text];
    [bg][text]overlay=0:0:shortest=1[outv]
    ```
  - Audio: Cờ `-an` (bắt buộc không gắn audio).

---

## 🚫 4. Các Điều CẤM KỴ (Anti-Patterns Cho AI/Agent)

Khi chỉnh sửa hoặc nâng cấp code dự án này, Agent cần tuân thủ nghiêm ngặt:
1. ❌ **KHÔNG thêm Audio Stream vào video**: Trừ khi người dùng yêu cầu rõ ràng, tuyệt đối không chèn nhạc MP3/WAV vào video xuất ra, luôn giữ cờ `-an`.
2. ❌ **KHÔNG thay đổi tỷ lệ khung hình 9:16 (1080x1920)**: Mọi filter `scale` và `crop` phải luôn giữ chuẩn dọc điện thoại.
3. ❌ **KHÔNG xóa bộ lọc `drawbox` màu đen**: Độ tối nền (mặc định 50%) là tính năng cốt lõi giúp chữ trắng không bị chìm vào ảnh nền.
4. ❌ **KHÔNG hardcode đường dẫn tuyệt đối**: Luôn dùng `Path(__file__).resolve().parent` hoặc đường dẫn tương đối để đảm bảo code chạy được trên cả Windows, Linux và Streamlit Cloud.
5. ❌ **KHÔNG can thiệp vùng Safe Zone**: Lề phải chữ phải giữ tối thiểu 180px để tránh bị cụm nút Thả tim / Bình luận / Chia sẻ của TikTok che khuất.

---

## 🧪 5. Quy Trình Kiểm Thử Nhanh (Verification Protocol)

Mỗi khi Agent thay đổi code, hãy chạy kiểm tra theo các bước:
```powershell
# 1. Kiểm tra cú pháp Python
python -m py_compile app.py modules/video_renderer.py modules/video_engine.py

# 2. Kiểm tra render thử nghiệm 1 video ngắn
python -c "from modules.video_renderer import render_18s_video; render_18s_video('temp/test_bg.jpg', 'Quote test', 'temp/test.mp4', duration=2.0, overlay_opacity=0.50)"
```
