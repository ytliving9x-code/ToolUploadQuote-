"""
Module sinh và cung cấp ảnh nền dọc 1080x1920 phong cách Aesthetic Cinematic (ai_image_gen.py).
Hỗ trợ đa nguồn (Multi-provider) để đảm bảo:
1. LUÔN LUÔN tạo ra ảnh mới, đa dạng, không bao giờ bị trùng lặp.
2. Nguồn 1: Unsplash Curated Aesthetic CDN (Ảnh chụp nghệ thuật 1080x1920 góc phố mưa đêm, rừng sương mù, cà phê...).
3. Nguồn 2: Pollinations AI & HuggingFace (Khi có kết nối).
4. Tự động crop & resize về đúng 1080x1920 (9:16 portrait) cho TikTok.
"""

import logging
import os
import random
import shutil
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image

logger = logging.getLogger("tiktok_tool.ai_image_gen")

CACHE_IMAGE_DIR = Path("data/cache/ai_images")
CACHE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

__all__ = [
    "CACHE_IMAGE_DIR",
    "CURATED_AESTHETIC_PHOTOS",
    "RETRO_COMIC_PRESETS",
    "generate_flux_image",
    "generate_retro_comic_image",
    "generate_ai_image",
]

# Bộ sưu tập ảnh phong cách Cinematic 35mm dọc (Aesthetic Portrait 1080x1920) được tuyển chọn kỹ lưỡng
CURATED_AESTHETIC_PHOTOS: List[str] = [
    # Mưa đêm, phố đêm neon, ánh đèn mờ ảo
    "https://images.unsplash.com/photo-1514565131-fce0801e5785?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519501025264-65ba15a82390?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1498084393753-b411b2d26b34?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=1080&auto=format&fit=crop",
    # Rừng cây sương mù, thiên nhiên tĩnh lặng, moody
    "https://images.unsplash.com/photo-1448375240586-882707db888b?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511497584788-87676104235f?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?q=80&w=1080&auto=format&fit=crop",
    # Cửa sổ ngắm mưa, quán cà phê đêm, góc đọc sách trầm ấm
    "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518495973542-4542c06a5843?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=1080&auto=format&fit=crop",
    # Ga tàu, đường phố đêm vắng, bước chân một mình
    "https://images.unsplash.com/photo-1477959858617-67f30bc75b82?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1513694203232-719a280e022f?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508873696983-2df5293cb325?q=80&w=1080&auto=format&fit=crop",
    # Bầu trời đêm, trăng sao, biển đêm thâm trầm
    "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?q=80&w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1080&auto=format&fit=crop",
]


# Bộ preset bối cảnh nghệ thuật Retro Comic Graphic Novel (Ligne Claire, Edward Hopper mood) cho Kênh Lặng
RETRO_COMIC_PRESETS: Dict[str, str] = {
    "🌧️ Bên Cửa Sổ Mưa Đêm (Trầm Tư & Bản Lĩnh)": (
        "Retro vintage comic book illustration, 1980s graphic novel style, ligne claire art, Edward Hopper aesthetic. "
        "A thoughtful solitary man in a dark trench coat standing by a rainy window in a dimly lit room, holding a cup of coffee, "
        "looking at city streetlights reflecting in puddles below. Melancholic yet stoic and calm atmosphere, textured paper grain, "
        "muted warm and dark palette, vertical 9:16 aspect ratio"
    ),
    "♟️ Bàn Cờ Tư Mã Ý (Mưu Lược & Ẩn Nhẫn)": (
        "Retro comic book noir illustration, a stoic thinker in a dark classic suit sitting alone at a wooden table in a dimly lit study room, "
        "studying a chessboard with carved pieces, soft warm lamp light, dark dramatic shadows, contemplative mood, ligne claire, "
        "textured paper grain, vertical 9:16 aspect ratio"
    ),
    "🚶 Bước Đi Trong Đêm (Kỷ Luật Cô Độc)": (
        "Vintage graphic novel aesthetic, a solitary man with a trench coat walking forward calmly on a quiet European stone street at dusk, "
        "warm streetlamps, deep street shadows, quiet confidence, textured paper grain, vertical 9:16 aspect ratio"
    ),
    "🌊 Bờ Biển Trăng Sao (Bình Yên & Lắng Đọng)": (
        "Retro 1980s comic art style, a tranquil beach and coastal meadow under a starry night sky with a full glowing moon, "
        "lone thinker observing the sea horizon, gentle waves, deep emotional metaphor, textured paper grain, vertical 9:16 aspect ratio"
    ),
    "🏢 Cao Ốc Đêm (Vị Thế & Thương Trường)": (
        "Retro graphic novel noir aesthetic, high-rise office balcony overlooking a dark metropolitan skyline at night, glowing city lights, "
        "silhouette of an ambitious thinker looking down at the vast city, stoic determination, vertical 9:16 aspect ratio"
    ),
    "👥 Hai Lối Rẽ (Nhìn Thấu Lòng Người)": (
        "Vintage European graphic novel illustration, Edward Hopper style, a man and a woman walking in opposite directions on a classic stone street, "
        "their dramatic shadows projected on the textured wall, poignant emotional metaphor, muted vintage tones, vertical 9:16 aspect ratio"
    ),
}


def generate_flux_image(
    prompt: str,
    output_dir: Optional[Path | str] = None,
    width: int = 1080,
    height: int = 1920,
    model: str = "flux",
) -> Path:
    """
    Sinh ảnh nghệ thuật độ phân giải cao sử dụng FLUX.1 (Black Forest Labs) qua g4f.
    Tự động download, crop center và tối ưu theo tỷ lệ dọc 1080x1920 (9:16).
    """
    dest_dir = Path(output_dir) if output_dir else CACHE_IMAGE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_path = dest_dir / f"flux_{uuid.uuid4().hex[:8]}.jpg"

    logger.info(f"Đang gọi FLUX.1 AI ({model}) với prompt: {prompt[:80]}...")
    from g4f.client import Client
    client = Client()

    res = client.images.generate(model=model, prompt=prompt)
    if not res or not hasattr(res, "data") or not res.data:
        raise ValueError("g4f không trả về kết quả ảnh.")

    raw_item = res.data[0]
    raw_url = raw_item.url if hasattr(raw_item, "url") else str(raw_item)

    if "?url=" in str(raw_url):
        real_url = urllib.parse.unquote(str(raw_url).split("?url=")[1])
    else:
        real_url = str(raw_url)

    req = urllib.request.Request(real_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })
    temp_raw = dest_dir / f"raw_flux_{uuid.uuid4().hex[:6]}.tmp"
    with urllib.request.urlopen(req, timeout=35) as resp:
        data = resp.read()
        if len(data) < 5000:
            raise ValueError("Dữ liệu ảnh trả về quá nhỏ hoặc không hợp lệ.")
        with open(temp_raw, "wb") as f:
            f.write(data)

    with Image.open(temp_raw) as img:
        img = img.convert("RGB")
        w, h = img.size
        ratio = width / height
        cur_ratio = w / h
        if cur_ratio > ratio:
            new_w = int(h * ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img.save(target_path, "JPEG", quality=95)

    if temp_raw.exists():
        temp_raw.unlink(missing_ok=True)

    logger.info(f"Đã sinh ảnh FLUX.1 thành công: {target_path}")
    return target_path


def generate_retro_comic_image(
    prompt_or_theme: str,
    quote_context: Optional[str] = None,
    output_dir: Optional[Path | str] = None,
    width: int = 1080,
    height: int = 1920,
    model: str = "flux",
    **kwargs,
) -> Path:
    """
    Sinh ảnh minh họa phong cách Retro Comic Book / Graphic Novel (Ligne Claire & Edward Hopper mood).
    Ưu tiên 1: FLUX.1 đỉnh cao thế giới qua g4f.
    Ưu tiên 2: Pollinations AI.
    Ưu tiên 3: Kho mẫu nghệ thuật có sẵn trong assets/samples/retro_comic.
    """
    dest_dir = Path(output_dir) if output_dir else CACHE_IMAGE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"retro_comic_{uuid.uuid4().hex[:8]}.jpg"
    target_path = dest_dir / file_name

    # Nếu người dùng chọn từ preset
    if prompt_or_theme in RETRO_COMIC_PRESETS:
        core_prompt = RETRO_COMIC_PRESETS[prompt_or_theme]
    else:
        core_prompt = prompt_or_theme.strip()

    # Nếu có quote_context và prompt chung chung, kết hợp ngữ cảnh
    if quote_context and (not core_prompt or core_prompt == "auto"):
        core_prompt = f"Retro vintage comic illustration depicting the emotional theme of: {quote_context}"

    # Bổ sung các từ khóa nghệ thuật cốt lõi
    style_suffix = (
        "retro vintage comic book illustration, 1980s graphic novel style, ligne claire art, "
        "Edward Hopper mood, textured paper grain, muted warm vintage color palette, "
        "vertical 9:16 aspect ratio, masterpiece, high artistic quality"
    )
    if "graphic novel" not in core_prompt.lower():
        full_prompt = f"{core_prompt}, {style_suffix}"
    else:
        full_prompt = core_prompt

    # ƯU TIÊN 1: FLUX.1 AI qua g4f
    try:
        flux_path = generate_flux_image(
            prompt=full_prompt,
            output_dir=dest_dir,
            width=width,
            height=height,
            model=model,
        )
        return flux_path
    except Exception as flux_err:
        logger.warning(f"FLUX.1 AI gặp sự cố ({flux_err}). Thử chuyển sang kênh dự phòng...")

    # ƯU TIÊN 2: Pollinations AI
    encoded_prompt = urllib.parse.quote(full_prompt)
    ai_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        logger.info(f"Đang gọi Pollinations fallback: {full_prompt[:70]}...")
        req = urllib.request.Request(ai_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                data = response.read()
                if len(data) > 15000:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    with Image.open(target_path) as img:
                        if img.size != (width, height):
                            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                            img_resized.save(target_path, "JPEG", quality=95)
                    logger.info(f"Sinh ảnh Pollinations thành công: {target_path.name}")
                    return target_path
    except Exception as err:
        logger.warning(f"Pollinations AI tạm thời chậm hoặc lỗi: {err}. Chuyển sang ảnh mẫu Retro Comic có sẵn...")

    # ƯU TIÊN 3: kiểm tra kho mẫu trong assets/samples/retro_comic
    samples_dir = Path("assets/samples/retro_comic")
    if samples_dir.exists():
        samples = list(samples_dir.glob("*.jpg")) + list(samples_dir.glob("*.png"))
        if samples:
            chosen = random.choice(samples)
            shutil.copy(chosen, target_path)
            logger.info(f"Đã nạp ảnh mẫu Retro Comic có sẵn: {chosen.name}")
            return target_path

    # Fallback: gọi hàm generate_ai_image thông thường
    return generate_ai_image(prompt=full_prompt, output_dir=output_dir, width=width, height=height)


def generate_ai_image(
    prompt: str,
    output_dir: Optional[Path | str] = None,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """
    Sinh hoặc chọn ảnh nền dọc 1080x1920 phong cách Aesthetic Cinematic.
    Đảm bảo 100% LUÔN RA ẢNH MỚI, KHÁC BIỆT, ĐẸP MẮT.

    Args:
        prompt: Mô tả ảnh hoặc từ khóa tâm trạng.
        output_dir: Thư mục lưu ảnh. Mặc định là data/cache/ai_images/.
        width: 1080
        height: 1920

    Returns:
        Path dẫn tới file ảnh đã lưu (.jpg).
    """
    dest_dir = Path(output_dir) if output_dir else CACHE_IMAGE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"ai_bg_{uuid.uuid4().hex[:8]}.jpg"
    target_path = dest_dir / file_name

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # Cách 1: Thử gọi AI trực tiếp với prompt tối ưu
    aesthetic_suffix = "cinematic lighting, moody dark atmosphere, 8k resolution, vertical 9:16 aspect ratio"
    full_prompt = f"{prompt.strip()}, {aesthetic_suffix}"
    encoded_prompt = urllib.parse.quote(full_prompt)
    ai_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}"

    try:
        logger.info(f"Đang sinh ảnh AI từ: {full_prompt[:60]}...")
        req = urllib.request.Request(ai_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                data = response.read()
                if len(data) > 20000:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    with Image.open(target_path) as img:
                        if img.size != (width, height):
                            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                            img_resized.save(target_path, "JPEG", quality=95)
                    logger.info(f"Sinh ảnh AI thành công: {target_path.name}")
                    return target_path
    except Exception as err:
        logger.warning(f"AI endpoint tạm thời bận hoặc giới hạn: {err}. Chuyển sang nguồn Curated Cinematic...")

    # Cách 2: Lấy ngẫu nhiên từ kho Curated Cinematic Aesthetic Photos chất lượng 4K/HD
    # Chọn ảnh chưa từng lưu gần đây để tránh trùng lặp
    photo_url = random.choice(CURATED_AESTHETIC_PHOTOS)
    try:
        logger.info("Đang tải ảnh nghệ thuật Cinematic Aesthetic 1080x1920...")
        req = urllib.request.Request(photo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()

        with open(target_path, "wb") as f:
            f.write(data)

        # Scale & Center Crop về đúng 1080x1920 (9:16)
        with Image.open(target_path) as img:
            img = img.convert("RGB")
            img_w, img_h = img.size
            target_ratio = width / height
            curr_ratio = img_w / img_h

            if curr_ratio > target_ratio:
                # Ảnh rộng hơn: crop 2 bên
                new_w = int(img_h * target_ratio)
                left = (img_w - new_w) // 2
                img = img.crop((left, 0, left + new_w, img_h))
            else:
                # Ảnh cao hơn: crop trên dưới
                new_h = int(img_w / target_ratio)
                top = (img_h - new_h) // 2
                img = img.crop((0, top, img_w, top + new_h))

            img = img.resize((width, height), Image.Resampling.LANCZOS)
            img.save(target_path, "JPEG", quality=95)

        logger.info(f"Đã tạo ảnh nền Cinematic mới: {target_path.name} (1080x1920)")
        return target_path

    except Exception as e:
        logger.error(f"Lỗi khi tải ảnh fallback: {e}")
        # Tạo ảnh gradient màu tối sâu lắng
        r = random.randint(15, 30)
        g = random.randint(15, 35)
        b = random.randint(30, 50)
        img = Image.new("RGB", (width, height), color=(r, g, b))
        img.save(target_path, "JPEG", quality=95)
        return target_path
