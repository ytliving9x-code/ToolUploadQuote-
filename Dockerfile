# ==============================================================================
# Dockerfile - TikTok Aesthetic Quote Video Generator (Streamlit App)
# ==============================================================================
FROM python:3.11-slim

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Cài đặt FFmpeg và các thư viện hệ thống cần thiết cho Pillow, OpenCV và video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    fonts-dejavu \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy và cài đặt dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Tạo các thư mục lưu trữ cần thiết
RUN mkdir -p temp data/cache output/saigonbac output/kenh_moi output/cho_dang output/da_dang

# Expose cổng mặc định của Streamlit
EXPOSE 8501

# Healthcheck kiểm tra ứng dụng đang sống
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Khởi chạy Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
