# 🎬 TikTok Quote Video Generator — Tool Tự Động Sản Xuất Video Quote 18s TikTok

Hệ thống phần mềm tự động hóa toàn diện bằng **Python & Streamlit**, chuyên sản xuất video ngắn TikTok dạng **Aesthetic B-Roll & Typography Độc Thoại Sâu Sắc**, tối ưu hóa hoàn hảo cho thuật toán giữ chân người xem của TikTok.

---

## 📑 MỤC LỤC TÀI LIỆU
1. [Mục Đích & Triết Lý Sản Phẩm](#1-mục-đích--triết-lý-sản-phẩm)
2. [Cấu Trúc Thư Mục Dự Án](#2-cấu-trúc-thư-mục-dự-án)
3. [Công Nghệ & Thư Viện Cốt Lõi](#3-công-nghệ--thư-viện-cốt-lõi)
4. [Các Tính Năng Chính Chi Tiết](#4-các-tính-năng-chính-chi-tiết)
   - [A. Sinh Quote Thông Minh (AI & CSDL)](#a-sinh-quote-thông-minh-ai--csdl)
   - [B. 3 Nguồn Ảnh / Video Nền Chuẩn 9:16](#b-3-nguồn-ảnh--video-nền-chuẩn-916)
   - [C. Bộ Từ Khóa Chuẩn Cinematic (Đô Thị & Thiên Nhiên)](#c-bộ-từ-khóa-chuẩn-cinematic-đô-thị--thiên-nhiên)
   - [D. Engine Render Typography & Video Tĩnh 18.0s](#d-engine-render-typography--video-tĩnh-180s)
   - [E. Quản Lý Hàng Chờ & Lịch Sử SQLite](#e-quản-lý-hàng-chờ--lịch-sử-sqlite)
5. [Quy Chuẩn Kỹ Thuật Video Thành Phẩm](#5-quy-chuẩn-kỹ-thuật-video-thành-phẩm)
6. [Hướng Dẫn Cài Đặt & Sử Dụng](#6-hướng-dẫn-cài-đặt--sử-dụng)
7. [Triển Khai Lên Streamlit Cloud](#7-triển-khai-lên-streamlit-cloud)

---

## 1. Mục Đích & Triết Lý Sản Phẩm

- **Định dạng video TikTok tĩnh 18 giây**: Video tĩnh hoặc chuyển động chậm kết hợp nhạc nền trending là một trong những format có tỷ lệ xem hết (Completion Rate) và tương tác cao nhất trên TikTok hiện nay.
- **Không Audio Track (`No Audio / Mute`)**: Video xuất ra cố ý không gắn nhạc để người sáng tạo nội dung tự chọn nhạc xu hướng (Trending Audio) trực tiếp trong ứng dụng TikTok khi đăng, giúp video dễ dàng được thuật toán đẩy xu hướng (FYP).
- **Nhân vật & Văn phong Quote**: Định vị là độc thoại của một người đàn ông 27–35 tuổi lúc đêm muộn, từng trải qua va vấp cuộc sống, cơm áo gạo tiền, các mối quan hệ. Không dạy đời, không sáo rỗng, ngôn từ đời thường nhưng sâu sắc và có sức nặng.

---

## 2. Cấu Trúc Thư Mục Dự Án

```text
ToolUploalQuote/
├── app.py                      # Giao diện Web App tương tác chính (Streamlit)
├── config.json                 # Cấu hình tham số mặc định và signature
├── packages.txt                # Khai báo cài đặt FFmpeg cho Streamlit Cloud
├── requirements.txt            # Danh sách thư viện Python cần thiết
├── README.md                   # Tài liệu chi tiết dự án
│
├── modules/                    # Các module tính năng chuyên biệt
│   ├── __init__.py             # Package init
│   ├── video_engine.py         # Kiểm tra và phân tích metadata video bằng FFprobe
│   └── video_renderer.py       # Engine dựng ảnh typography & render video 18.0s bằng FFmpeg
│
├── assets/
│   └── fonts/                  # Tuyển tập font chữ tiếng Việt cao cấp (BeVietnamPro, Montserrat,...)
│
├── generated_media/            # Lưu trữ video xuất bản
├── output/                     # Thư mục lưu sản phẩm hoàn thiện
└── temp/                       # Thư mục lưu ảnh/video tạm thời khi render
```

---

## 3. Công Nghệ & Thư Viện Cốt Lõi

| Thành Phần | Công Nghệ / Thư Viện | Vai Trò |
|---|---|---|
| **Web UI** | Streamlit | Giao diện điều khiển trực quan, mượt mà trên trình duyệt |
| **Video Engine** | FFmpeg (`ffmpeg-python`) | Render video tĩnh 18s chuẩn H.264/MP4 ở 30fps cực nhanh |
| **Typography Engine** | Pillow (PIL) | Vẽ chữ tiếng Việt căn chuẩn tỷ lệ, tự bẻ dòng, drop-shadow |
| **Font chữ** | Be Vietnam Pro Bold | Font sans-serif hiện đại, hỗ trợ dấu tiếng Việt 100% không lỗi |
| **AI LLM** | Google Gemini / Groq Llama-3 / OpenRouter | Sinh câu quote độc thoại sâu sắc theo chủ đề |
| **AI Image Gen** | Pollinations AI REST API | Tạo ảnh nền nghệ thuật 1080x1920 miễn phí không cần API key |
| **Stock Provider** | Pixabay API | Tìm kiếm và tải ảnh nền chất lượng cao |
| **Database** | SQLite3 (`data/history.db`) | Quản lý lịch sử render, đo lường độ trùng lặp bằng `difflib` |

---

## 4. Các Tính Năng Chính Chi Tiết

### A. Sinh Quote Thông Minh (AI & CSDL)
1. **Đa dạng nguồn AI**:
   - Tích hợp **Google Gemini** (`gemini-1.5-flash`), **Groq** (`llama3-70b-8192`), **OpenRouter**, **DeepSeek**.
   - Có sẵn chế độ **Fallback Offline** từ `quotes.json` nếu mất mạng hoặc chưa nhập API Key.
2. **Kỹ thuật chống trùng lặp (Anti-Duplicate)**:
   - Trước khi lưu hoặc hiển thị, thuật toán đo độ tương đồng chuỗi `SequenceMatcher` so sánh với toàn bộ các câu quote đã tạo trong CSDL SQLite.
   - Nếu độ giống nhau $\ge 70\%$, hệ thống tự động loại bỏ và tạo câu khác.
3. **Prompt độc thoại đêm muộn**:
   - Được tinh chỉnh đặc biệt: Nam 27–35 tuổi, ngồi một mình đêm muộn sau ngày làm việc.
   - Độ dài tiêu chuẩn: **12–30 từ**, chia làm 2–3 nhịp ngắn gọn, đọc đến đâu thấm đến đó.

---

### B. 3 Nguồn Ảnh / Video Nền Chuẩn 9:16
1. **Kho ảnh Pixabay (Khuyên dùng)**:
   - Tìm kiếm ảnh chất lượng cao theo từ khóa tiếng Anh.
   - Xem trước **Gallery 8 ảnh** cùng lúc trên giao diện để chọn bức ưng ý nhất chỉ với 1 click.
   - Tự động Center-Crop chính xác về 1080x1920.
2. **AI Tạo Ảnh Độc Bản (Pollinations AI)**:
   - Hoàn toàn miễn phí, **không cần đăng ký API Key**.
   - Tự động dịch prompt sang tiếng Anh nghệ thuật (Cinematic, moody, dark aesthetic, 8k resolution, vertical 9:16).
   - Mỗi lần bấm là một bức ảnh độc nhất vô nhị.
3. **Tải ảnh cá nhân từ máy tính**:
   - Cho phép người dùng kéo thả bất kỳ file ảnh JPG/PNG từ máy tính.
   - Tool tự động phân tích tỷ lệ và cắt căn giữa chuẩn 1080x1920.

---

### C. Bộ Từ Khóa Chuẩn Cinematic (Đô Thị & Thiên Nhiên)
Hệ thống tích hợp sẵn kho từ khóa tiếng Anh chuẩn Cinematic được tuyển chọn kỹ lưỡng:

#### 1. Phong cách Đô Thị & Nội Tâm (Cinematic Solitude)
- **10 Từ khóa ưu tiên đồng bộ kênh**:
  `lonely man walking at night`, `rainy city night cinematic`, `man sitting alone at night`, `man looking out window`, `dark street b roll`, `man walking alone back view`, `night city lights cinematic`, `man drinking coffee alone`, `cinematic urban solitude`, `moody city b roll`.
- **Phân loại concept**:
  - *Đường phố ban đêm — trầm, lạnh*
  - *Một mình suy nghĩ — nội tâm*
  - *Người đàn ông bước đi — trưởng thành*
  - *Mưa, cửa kính, ánh đèn — tâm trạng*
  - *Tiền bạc & Áp lực cuộc sống*
  - *Bình thản & Thường ngày*

#### 2. Phong cách Thiên Nhiên Trầm Lắng (Cinematic Nature)
- **12 Từ khóa ưu tiên thường dùng**:
  `misty mountains cinematic`, `foggy forest slow motion`, `moody ocean waves`, `waves hitting rocky shore`, `empty road through forest`, `forest river cinematic`, `rain falling on leaves`, `sunset lake reflection`, `dark pine forest fog`, `clouds moving over mountains`, `waterfall in forest cinematic`, `wind blowing through grass`.
- **Phân loại concept**:
  - *Núi rừng phủ sương* (Trưởng thành, bình thản)
  - *Biển rộng, sóng vỗ* (Cô độc, buông bỏ)
  - *Con đường xuyên rừng* (Hành trình tiếp bước)
  - *Mưa rơi trên lá cây* (Trầm lắng, chữa lành)
  - *Hoàng hôn trên hồ* (Hoài niệm, thời gian)
  - *Rừng cây và gió* (Bản lĩnh, tĩnh lặng)

---

### D. Engine Render Typography & Video Tĩnh 18.0s
1. **Quy chuẩn vùng an toàn TikTok (Safe Zone)**:
   - Kích thước: **1080 x 1920 pixel**.
   - Giới hạn lề: Chữ được đặt chính xác trong khoảng từ **Y = 150px** đến **Y = 1770px**, cách lề trái phải **80px**.
   - Đảm bảo tuyệt đối **không bị che khuất** bởi các nút Like, Comment, Share bên phải hoặc Caption và Thanh điều hướng ở dưới đáy màn hình TikTok.
2. **Hiệu ứng Typography cao cấp**:
   - Chữ màu trắng tinh (`#FFFFFF`), font `Be Vietnam Pro Bold`.
   - Bóng đổ mờ nhiều lớp (`Multi-layer Soft Drop Shadow`) màu đen mờ giúp chữ nổi bật và sắc nét trên mọi loại nền sáng/tối.
   - Tự động ngắt dòng thông minh (`Smart Word Wrap`) và co giãn kích thước font theo độ dài câu.
3. **Tốc độ xuất file cực nhanh**:
   - Sử dụng FFmpeg render trực tiếp từ ảnh typography với codec `libx264`, preset `ultrafast`, pixel format `yuv420p`.
   - Thời gian render chỉ mất khoảng **1 – 3 giây** cho toàn bộ video 18 giây.

---

### E. Quản Lý Hàng Chờ & Lịch Sử SQLite
- **Hàng chờ đăng (`output/cho_dang/`)**:
  - Mỗi video xuất bản được lưu thành cặp: `ten_video.mp4` và `ten_video.txt`.
  - File `.txt` chứa sẵn toàn bộ nội dung: Quote, Caption viết sẵn và bộ Hashtag chuẩn SEO TikTok.
  - Trên giao diện có nút **"📋 Sao Chép Caption & Hashtags"** 1-click để đăng bài ngay.
  - Khi đăng xong, bấm **"Đã Đăng"** sẽ tự động chuyển file sang thư mục `output/da_dang/`.
- **Lịch sử & Thống kê**:
  - Toàn bộ câu quote, chủ đề, thời gian tạo, đường dẫn file được lưu vĩnh viễn trong CSDL SQLite `data/history.db`.

---

## 5. Quy Chuẩn Kỹ Thuật Video Thành Phẩm

```text
Độ phân giải:       1080 x 1920 px (Tỷ lệ khung hình dọc 9:16)
Thời lượng:         Chính xác 18.0 giây (30.0 fps)
Video Codec:        H.264 / AVC (High Profile, Level 4.1)
Pixel Format:       yuv420p (Tương thích 100% mọi dòng điện thoại iOS / Android)
Audio Track:        None (Mute - Tối ưu gắn nhạc xu hướng trực tiếp trên TikTok)
Dung lượng file:    Khoảng 2MB - 5MB (Nhẹ, tải lên TikTok cực nhanh không bị nén vỡ hình)
```

---

## 6. Hướng Dẫn Cài Đặt & Sử Dụng

### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10/11, macOS, hoặc Linux.
- Python: Phiên bản **3.10 trở lên**.
- FFmpeg: Đã được cài đặt và có trong PATH hệ thống (trên Windows có thể dùng winget hoặc choco; trên Cloud dùng packages.txt).

### Bước 1: Tạo môi trường ảo & Cài đặt thư viện
```powershell
# Di chuyển vào thư mục dự án
cd D:\ToolUploalQuote

# Tạo môi trường ảo Python
python -m venv .venv

# Kích hoạt môi trường ảo (trên Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Cài đặt toàn bộ thư viện
pip install -r requirements.txt
```

### Bước 2: Khởi chạy Web App
```powershell
streamlit run app.py
```
Ứng dụng sẽ tự động khởi chạy và mở trên trình duyệt tại địa chỉ: `http://localhost:8501`.

### Bước 3: Sử dụng CLI để tạo hàng loạt (Tự động hóa)
```powershell
# Tạo 3 video chủ đề ngẫu nhiên
python cli.py --count 3

# Tạo 1 video chủ đề cụ thể (ví dụ: tiền bạc, trưởng thành)
python cli.py --count 1 --topic "tiền bạc"
```

---

## 7. Triển Khai Lên Streamlit Cloud

Dự án đã được cấu hình sẵn sàng 100% để chạy trên **Streamlit Community Cloud**:
1. Đã có file `packages.txt` chứa `ffmpeg` để máy chủ tự động cài FFmpeg Linux.
2. Đã có file `requirements.txt` chuẩn hóa các thư viện tương thích.
3. Trên trang cài đặt app của Streamlit Cloud (mục **App Settings > Secrets**), bạn chỉ cần cấu hình các biến môi trường:
```toml
PIXABAY_API_KEY = "your_pixabay_api_key_here"
GEMINI_API_KEY = "your_gemini_api_key_here"   # (tùy chọn)
GROQ_API_KEY = "your_groq_api_key_here"       # (tùy chọn)
```

---

*Tài liệu được cập nhật tự động và đồng bộ với phiên bản mới nhất của Tool.*
