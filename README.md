# 🎬 TikTok Quote Studio 10s — Tool Sản Xuất Video Quote Nền Tối Chữ Trắng Chuẩn TikTok

Hệ thống phần mềm xây dựng bằng **Python & Streamlit**, chuyên sản xuất video ngắn TikTok dạng **Aesthetic Quote 10s (Nền tối dìm sáng & Chữ trắng nổi bật, hỗ trợ cả Ảnh & Video)**, tối ưu hoàn hảo cho thuật toán giữ chân người xem (Watch Time & Completion Rate) của TikTok.

---

## 📑 MỤC LỤC
1. [Triết Lý Sản Phẩm & Quy Chuẩn TikTok](#1-triết-lý-sản-phẩm--quy-chuẩn-tiktok)
2. [Cấu Trúc Thư Mục Thực Tế](#2-cấu-trúc-thư-mục-thực-tế)
3. [Công Nghệ & Thư Viện Cốt Lõi](#3-công-nghệ--thư-viện-cốt-lõi)
4. [Các Tính Năng Chính Trên Ứng Dụng](#4-các-tính-năng-chính-trên-ứng-dụng)
   - [A. Nhập Quote & Đo Độ Dài Lý Tưởng](#a-nhập-quote--đo-độ-dài-lý-tưởng)
   - [B. Tải Nền Cá Nhân & Tự Động Cắt Chuẩn 9:16](#b-tải-nền-cá-nhân--tự-động-cắt-chuẩn-916)
   - [C. Thanh Trượt Độ Tối Hình Nền (Dark Overlay 50%)](#c-thanh-trượt-độ-tối-hình-nền-dark-overlay-50)
   - [D. Bộ Phông Chữ Tiếng Việt & Chống Loá](#d-bộ-phông-chữ-tiếng-việt--chống-loá)
   - [E. Khung Điện Thoại Xem Trước Thời Gian Thực (Live Preview)](#e-khung-điện-thoại-xem-trước-thời-gian-thực-live-preview)
   - [F. Engine Render Video Tĩnh 18.0 Giây (FFmpeg)](#f-engine-render-video-tĩnh-180-giây-ffmpeg)
   - [G. Tự Động Tạo Caption & Hashtags 1-Click Copy](#g-tự-động-tạo-caption--hashtags-1-click-copy)
5. [Quy Chuẩn Kỹ Thuật Video Thành Phẩm](#5-quy-chuẩn-kỹ-thuật-video-thành-phẩm)
6. [Hướng Dẫn Cài Đặt & Sử Dụng](#6-hướng-dẫn-cài-đặt--sử-dụng)

---

## 1. Triết Lý Sản Phẩm & Quy Chuẩn TikTok

- **Định dạng video 10 giây**: Thời lượng 10.0s là "thời lượng vàng" tối ưu giữ chân người xem cho video quote TikTok: đủ dài để người xem đọc và suy ngẫm, nhưng đủ ngắn để xem hết (thậm chí lặp lại 2 lần), giúp tăng điểm tương tác mạnh mẽ.
- **Nền tối dìm sáng (Dark Moody Aesthetic)**: Sử dụng lớp phủ đen mờ (mặc định 50%) kết hợp tối 4 góc (Vignette). Bất kể ảnh gốc sáng chói hay phức tạp, toàn bộ nền đều chìm xuống làm hậu cảnh, giúp câu quote màu trắng nổi bật tuyệt đối, không gây mỏi mắt.
- **Không Audio Track (`No Audio / Mute`)**: Video xuất ra cố ý **không gắn nhạc nền** để người dùng tự chọn nhạc xu hướng (Trending Sound) trực tiếp trong ứng dụng TikTok khi đăng. Đây là mẹo SEO quan trọng nhất để video dễ được thuật toán TikTok phân phối lên For You Page (FYP).

---

## 2. Cấu Trúc Thư Mục Thực Tế

```text
ToolUploalQuote/
├── app.py                      # Giao diện chính Streamlit (Glassmorphism & Live Preview)
├── config.json                 # Cấu hình mặc định (branding, signature, thông số render)
├── packages.txt                # Khai báo gói FFmpeg cho Linux / Streamlit Cloud
├── requirements.txt            # Thư viện Python (streamlit, pillow, ffmpeg-python, imageio-ffmpeg)
├── README.md                   # Tài liệu chi tiết dự án
├── SKILL.md                    # Cẩm nang hướng dẫn cho AI/Agent đọc hiểu dự án
│
├── modules/                    # Các module tính năng cốt lõi
│   ├── __init__.py
│   ├── video_engine.py         # Trích xuất metadata video bằng FFprobe
│   └── video_renderer.py       # Engine vẽ typography chống loá & dựng video 18.0s bằng FFmpeg
│
├── assets/
│   └── fonts/                  # Phông chữ tiếng Việt (BeVietnamPro, Montserrat, PlayfairDisplay, Itim)
│
├── output/                     # Thư mục chứa video thành phẩm
│   └── saigonbac/              # Chứa cặp file: video .mp4 và caption .txt đi kèm
└── temp/                       # Thư mục đệm xử lý ảnh crop & file tạm khi render
```

---

## 3. Công Nghệ & Thư Viện Cốt Lõi

| Thành Phần | Công Nghệ / Thư Viện | Vai Trò |
| :--- | :--- | :--- |
| **Giao Diện Web (UI)** | **Streamlit** | Giao diện Dark Glassmorphism mượt mà, hỗ trợ tương tác trên cả điện thoại và máy tính. |
| **Typography Engine** | **Pillow (PIL)** | Vẽ chữ tiếng Việt chuẩn tỷ lệ, ngắt dòng thông minh, đổ bóng kép (Dual-layer Shadow) và viền mảnh (Micro-stroke). |
| **Video Engine** | **FFmpeg** | Cắt ghép, áp dụng chuyển động Ken Burns drift, tối 4 góc (Vignette), lớp phủ đen (Drawbox) và xuất file H.264 cực nhanh. |
| **Phông chữ** | **TrueType (.ttf)** | Bộ font tiếng Việt chọn lọc: `Be Vietnam Pro Bold`, `Montserrat`, `Playfair Display`, `Itim`. |

---

## 4. Các Tính Năng Chính Trên Ứng Dụng

### A. Nhập Quote & Đo Độ Dài Lý Tưởng
- Hỗ trợ nhập hoặc dán câu quote tự do.
- Tự động đếm số từ theo thời gian thực và hiển thị nhãn gợi ý:
  - **15 – 26 từ**: Độ dài lý tưởng nhất cho nhịp đọc 18 giây TikTok.
  - Tự động tính toán ngắt dòng thông minh (`Smart Word Wrap`), không bao giờ bị cắt cụt từ ngữ.

### B. Tải Nền Cá Nhân & Tự Động Cắt Chuẩn 9:16
- Người dùng tải trực tiếp ảnh từ máy tính hoặc điện thoại (`.jpg`, `.png`, `.webp`, `.jfif`).
- Hệ thống tự động **Center-Crop** và phóng tỷ lệ chính xác về **1080 x 1920 (dọc 9:16)** không viền đen.

### C. Thanh Trượt Độ Tối Hình Nền (Dark Overlay 50%)
- Tích hợp thanh trượt từ **0%** (nguyên bản) đến **90%** (rất tối), bước nhảy 5%.
- **Mặc định chuẩn 50% (`overlay_opacity=0.50`)**: Mức tối hoàn hảo để dìm mọi ánh sáng chói của hình nền, làm câu quote màu trắng bật sáng sắc nét.
- Áp dụng trực tiếp vào FFmpeg bằng filter `drawbox=x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity}:t=fill`.

### D. Bộ Phông Chữ Tiếng Việt & Chống Loá
- Tuyển chọn các font chữ có bản quyền mở, hỗ trợ 100% dấu tiếng Việt:
  - `☕ Be Vietnam Pro Bold`: Hiện đại, thanh lịch, chuẩn mực.
  - `🎞️ Playfair Display Bold`: Cổ điển có chân (Serif), lãng mạn, chiều sâu hoài niệm.
  - `🔥 Montserrat Black`: Nét cực đậm, bắt mắt, nổi bật.
  - `⚡ Montserrat Bold`: Cân đối, sắc sảo.
  - `🍃 Itim`: Nét bo tròn mềm mại như trang nhật ký.
- **Bộ 3 chống loá quang học**:
  1. *Lớp Gradient Scrim chuyển mờ êm ở đáy*.
  2. *Bóng đổ kép đa tầng (Dual-Layer Cinema Shadow)*: 1 lớp bóng sắc chân chữ + 1 lớp bóng mờ lan tỏa.
  3. *Viền siêu mảnh (Micro-stroke 1px)* chống tán xạ ánh sáng.

### E. Khung Điện Thoại Xem Trước Thời Gian Thực (Live Preview)
- Cột bên phải giả lập khung điện thoại chuẩn tỷ lệ 9:16.
- Cập nhật thời gian thực nội dung câu quote, phông chữ, chữ ký và độ tối hình nền ngay khi bạn vừa gõ chữ hoặc kéo thanh trượt.

### F. Engine Render Video Đa Phương Tiện 10.0 Giây (FFmpeg)
- Render video tốc độ cao (chỉ mất 2 – 5 giây cho video 18 giây).
- Tích hợp hiệu ứng chuyển động chậm **Ken Burns Cinematic Drift** (zoom nhẹ từ 1.0 đến 1.05) giúp video sống động, không bị đơ cứng như ảnh tĩnh đơn thuần.
- Thêm hiệu ứng tối 4 góc **Cinematic Vignette** tập trung ánh nhìn.

### G. Tự Động Tạo Caption & Hashtags 1-Click Copy
- Ngay sau khi xuất video, hệ thống tự động tổng hợp:
  - **Dòng trên**: Câu quote bạn vừa gõ trong video.
  - **Dòng dưới**: Bộ hashtag trending chuẩn SEO TikTok:
    ```text
    #{signature} #tamtrang #suyngam #trietlycuocsong #cuocsong #xuhuong #fyp #viral #quotesvn #chill
    ```
- Hộp mã có nút **📋 Copy 1-Click** ở góc phải để người dùng dán ngay vào TikTok khi đăng.
- Tự động lưu kèm file `.txt` cùng tên với video trong thư mục `output/saigonbac/`.

---

## 5. Quy Chuẩn Kỹ Thuật Video Thành Phẩm

```text
Độ phân giải:       1080 x 1920 px (Khổ dọc chuẩn TikTok 9:16)
Thời lượng:         Chính xác 10.0 giây (30.0 fps)
Video Codec:        H.264 / AVC (Profile High, Level 4.1)
Pixel Format:       yuv420p (Tương thích 100% mọi thiết bị iOS / Android)
Chất lượng nén:     CRF 16 (Gần như lossless, chữ cực kỳ sắc nét)
Hiệu ứng chuyển động: Ken Burns Cinematic Drift (Zoompan 1.0 -> 1.05)
Audio Stream:       None (Mute - Tối ưu gắn nhạc xu hướng trực tiếp trên TikTok)
Dung lượng file:    Khoảng 2MB - 6MB (Tải lên TikTok cực nhanh không bị nén vỡ)
```

---

## 6. Hướng Dẫn Cài Đặt & Sử Dụng

### Yêu Cầu Hệ Thống:
- **Python**: Phiên bản 3.10 trở lên.
- **FFmpeg**: Đã cài đặt và có trong PATH hệ thống (đã có sẵn trên máy của bạn).

### Bước 1: Kích hoạt môi trường và cài đặt thư viện
```powershell
# Di chuyển vào thư mục dự án
cd D:\ToolUploalQuote

# Kích hoạt virtualenv (nếu có)
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện
pip install -r requirements.txt
```

### Bước 2: Khởi chạy Web App
```powershell
streamlit run app.py
```
Ứng dụng sẽ tự động mở trên trình duyệt tại: `http://localhost:8501`.

### Bước 3: Xuất video & Đăng bài
1. Gõ câu quote vào ô văn bản ở Bước 1.
2. Tải ảnh nền bạn thích ở Bước 2.
3. Kéo thanh trượt độ tối nền (mặc định 50%) và chọn font chữ ở Bước 3.
4. Bấm nút **"✨ XUẤT VIDEO TIKTOK 18S CHUẨN HD"**.
5. Bấm nút **"⬇️ TẢI VIDEO XUỐNG (.MP4)"** và bấm copy caption để đăng lên TikTok!
