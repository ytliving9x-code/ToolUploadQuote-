# Tool Tự Động Sản Xuất Video TikTok 18s Aesthetic B-Roll & Quote Typography 🎬

Hệ thống tự động hóa cục bộ (Python + Streamlit) chuyên sản xuất video ngắn TikTok dạng:
- **Nền**: Ảnh tĩnh Mood Aesthetic B-roll chất lượng cao từ **Pixabay Image Search API** (hoặc tự tải ảnh lên / thư viện).
- **Chữ**: Quote Typography tiếng Việt sâu sắc (Font Be Vietnam Pro, chữ trắng tinh, bóng đổ đen mờ mềm mại).
- **Quy chuẩn video**: Đúng chính xác **18.0 giây**, tỷ lệ dọc 9:16 (1080x1920), 30fps.
- **Âm thanh**: **KHÔNG có audio track** (`No Audio / Mute`), sẵn sàng để bạn tải về và tự chèn nhạc trending trên TikTok.

---

## 📁 Cấu Trúc Dự Án Tinh Gọn

```text
├── app.py                      # Giao diện web Streamlit tinh gọn 1 trang
├── modules/
│   ├── pixabay_fetcher.py      # Tải & căn giữa (crop) ảnh dọc Pixabay 1080x1920
│   ├── quote_manager.py        # Quản lý & lấy ngẫu nhiên câu quote từ quotes.json
│   ├── video_renderer.py       # Ghép typography & render video tĩnh 18s bằng FFmpeg
│   ├── exporter.py             # Quản lý xuất hàng chờ đăng
│   └── history_db.py           # SQLite theo dõi lịch sử sản xuất
├── assets/fonts/               # File font tiếng Việt (BeVietnamPro-Bold.ttf)
├── quotes.json                 # Danh sách câu quote mẫu (cơm áo gạo tiền, điềm đạm, thất bại)
├── config.json                 # Cấu hình Pixabay API Key và video
├── requirements.txt            # Danh sách thư viện Python
└── output/                     # Thư mục xuất video thành phẩm (tiktok_18s_ready.mp4)
```

---

## 🚀 Hướng Dẫn Khởi Chạy & Sử Dụng

### 1. Khởi chạy ứng dụng
Mở Terminal / PowerShell tại thư mục dự án và chạy lệnh:
```powershell
streamlit run app.py
```
Ứng dụng sẽ tự động mở tại: `http://localhost:8501`.

### 2. Cách lấy Pixabay API Key (Hoàn toàn Miễn Phí)
1. Đăng ký tài khoản tại [Pixabay.com](https://pixabay.com/).
2. Đăng nhập và truy cập trang tài liệu API: [pixabay.com/api/docs](https://pixabay.com/api/docs/).
3. Kéo xuống mục **Search Images**, bạn sẽ thấy chuỗi **API Key** của mình (dạng dãy số-chữ cái).
4. Dán API Key vào thanh bên cạnh trái (Sidebar) của Web Tool và bấm **"Lưu Pixabay API Key"**.
*(Lưu ý: Nếu chưa nhập key, Tool vẫn có sẵn kho ảnh Aesthetic chất lượng cao để bạn tạo video ngay lập tức!)*

---

## 🖥️ Cách Chạy Ứng Dụng

### Cách 1: Giao diện Web Trực quan (Streamlit)
```powershell
streamlit run app.py
```
Ứng dụng sẽ tự động mở tại: `http://localhost:8501`

**Các tính năng nổi bật trên giao diện:**
- **Tab Tạo Video**:
  - Chọn chủ đề (`điềm tĩnh`, `nỗ lực`, `tiền bạc`, `chữa lành`, hoặc `Ngẫu nhiên`).
  - Nút **"Sinh Toàn Bộ Mới"** / **"Đổi Quote Khác"** / **"Đổi Footage Khác"**.
  - **Chỉnh sửa thủ công**: Tự do gõ sửa lại từng chữ trong Quote, Caption hoặc Hashtags trước khi render.
  - Nút **"Render Video Ngay"**: Xem trước video trực tiếp trên trình phát dọc.
  - Nút **"Lưu Vào Thư Mục Chờ Đăng"**: Tự động lưu video và file `.txt` vào `output/cho_dang/`.
- **Tab Chờ Đăng**:
  - Danh sách video chưa upload, xem lại video, nút 1-click sao chép caption & hashtags.
  - Nút **"Đã Đăng"**: Tự động chuyển file sang thư mục `output/da_dang/` và cập nhật CSDL.
- **Tab Lịch Sử**:
  - Bảng thống kê toàn bộ quote, thời gian tạo, đường dẫn video và trạng thái.
- **Tab Cài Đặt**:
  - Nhập trực tiếp API key lưu vào `.env`, tùy chỉnh font size, độ tối overlay, thời lượng mục tiêu.

---

### Cách 2: Sản xuất tự động bằng dòng lệnh (CLI)
Dùng cho việc tự động sản xuất hàng loạt hoặc tích hợp lập lịch:
```powershell
# Tự tạo 2 video chủ đề ngẫu nhiên và lưu thẳng vào output/cho_dang/
python cli.py --count 2

# Tự tạo 1 video chủ đề cụ thể
python cli.py --count 1 --topic "điềm tĩnh"
```

---

## ⏰ Hướng Dẫn Lập Lịch Tự Động (Windows Task Scheduler)

Để tool tự động sản xuất video vào các khung giờ vàng (ví dụ: **11:30** trưa và **21:30** tối):

1. Mở **Task Scheduler** trên Windows (`Win + R` gõ `taskschd.msc`).
2. Nhấn **Create Basic Task...**:
   - Tên: `TikTok Video Generator 11h30`
   - Trigger: Chọn **Daily**, đặt giờ `11:30:00 AM`.
   - Action: Chọn **Start a program**.
   - **Program/script**: Trỏ tới file Python trong môi trường ảo:
     `D:\ToolUploalQuote\.venv\Scripts\python.exe`
   - **Add arguments**:
     `cli.py --count 1`
   - **Start in**: Thư mục dự án:
     `D:\ToolUploalQuote`
3. Nhấn Finish. Lặp lại tương tự cho khung giờ `21:30`.

*(Trên Linux/macOS, bạn chỉ cần cấu hình crontab: `30 11,21 * * * cd /path/to/project && .venv/bin/python cli.py --count 1`)*.

---

## 📲 Quy Trình Đăng Bài Thủ Công Lên TikTok

1. **Lấy video từ thư mục chờ đăng**:
   - Mở thư mục `output/cho_dang/`.
   - Chuyển file video `.mp4` sang điện thoại (qua Zalo truyền file định dạng HD, AirDrop, Google Drive hoặc Telegram).
2. **Mở ứng dụng TikTok trên điện thoại**:
   - Nhấn dấu **+** để tạo bài đăng mới -> Chọn video vừa chuyển.
   - Nhấn vào mục **"Thêm âm thanh"** (Add sound) ở trên cùng -> Chọn một bài hát đang nằm trong mục **Trending / Đang thịnh hành** (hoặc bài nhạc lofi/piano nhẹ nhàng phù hợp tâm trạng).
3. **Dán Caption & Hashtags**:
   - Mở file `.txt` tương ứng trong `output/cho_dang/` (hoặc copy trực tiếp từ tab Chờ Đăng trên app).
   - Dán vào phần mô tả của bài đăng.
4. **Đánh dấu hoàn tất**:
   - Quay lại giao diện Streamlit (tab Chờ Đăng), nhấn nút **"Đã Đăng"** để chuyển video sang `output/da_dang/`.
