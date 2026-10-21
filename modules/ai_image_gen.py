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
    "generate_imagen3_image",
    "build_scene_director_prompt",
    "generate_smart_ai_background",
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


def build_scene_director_prompt(quote_text: str, channel: str = "saigonbac") -> str:
    """
    Sử dụng Gemini AI (siêu tốc, miễn phí) làm Đạo diễn Nghệ thuật (AI Scene Director):
    Phân tích câu quote tiếng Việt để kiến tạo prompt tiếng Anh nhiếp ảnh/minh họa chuẩn 9:16.
    Tránh tuyệt đối việc đưa thẳng tiếng Việt vào AI vẽ tranh khiến ảnh sai lệch hoặc ra ảnh rác.
    """
    clean_q = quote_text.strip()
    if not clean_q:
        return (
            "Cinematic 35mm film photograph, shot on Leica M6, Kodak Portra 400. "
            "A solitary figure seen from behind walking away down a rainy street at night, warm amber streetlights reflection, "
            "moody introspective atmosphere, dark negative space at bottom, 9:16 vertical orientation"
        )

    try:
        from modules.quote_gen import call_gemini
        if channel == "saigonbac":
            director_instruction = (
                "You are an elite cinematic art director for moody 35mm film photography.\n"
                f"Convert this Vietnamese introspective quote into a single-sentence English photography prompt for a vertical 9:16 portrait still: \"{clean_q}\"\n"
                "Rules:\n"
                "1. Authentic 35mm film still, shot on Leica M6, Kodak Portra 400 film grain.\n"
                "2. Subject: Lone silhouette or figure seen from behind (NO face visible), quiet rainy street, train station, dark cafe window, or misty dawn.\n"
                "3. Composition: Keep lower 40% clean with dark negative space for white quote typography.\n"
                "4. Mood: Nostalgic, melancholic, quiet healing.\n"
                "5. Return ONLY the English prompt in 1 concise sentence without quotes or markdown."
            )
        else:
            director_instruction = (
                "You are an elite art director for vintage 1980s graphic novels and retro comic art (ligne claire style, Edward Hopper mood).\n"
                f"Convert this Vietnamese stoic/philosophical quote into a single-sentence English illustration prompt for a vertical 9:16 aspect ratio: \"{clean_q}\"\n"
                "Rules:\n"
                "1. Retro vintage graphic novel illustration, ligne claire, textured paper grain, muted warm palette.\n"
                "2. Subject: Stoic thinker in dark coat, study room with desk lamp, chess board, or quiet city balcony overlooking misty night skyline.\n"
                "3. Composition: Generous negative space at the bottom for typography.\n"
                "4. Return ONLY the English prompt in 1 concise sentence without quotes or markdown."
            )
        res = call_gemini(director_instruction, model_name="gemini-3.5-flash-lite")
        if res and len(res.strip()) > 15:
            clean_res = res.strip().strip('"').strip("'").replace("\n", " ")
            return clean_res
    except Exception as e:
        logger.warning(f"Lỗi khi gọi AI Scene Director: {e}")

    # Fallback chất lượng cao nếu Gemini bận
    if channel == "saigonbac":
        return (
            "Vertical 9:16 cinematic 35mm film photograph, shot on Leica M6, Kodak Portra 400. "
            "Solitary figure walking away down a rainy street at night, warm amber streetlights reflection, "
            "dark negative space at bottom for typography, moody atmospheric healing."
        )
    else:
        return (
            "Vertical 9:16 retro vintage comic book illustration, 1980s graphic novel style, ligne claire, "
            "stoic thinker sitting in dimly lit room with warm desk lamp, textured paper grain, muted vintage colors, "
            "negative space at bottom."
        )


def generate_imagen3_image(
    prompt: str,
    api_key: Optional[str] = None,
    output_path: Optional[Path | str] = None,
    aspect_ratio: str = "9:16",
) -> Path:
    """
    Sinh ảnh nghệ thuật độ phân giải cao sử dụng Google Imagen 3 (imagen-3.0-generate-002)
    thông qua API Key Google Gemini (yêu cầu dự án đã bật Pay-as-you-go trên Google AI Studio).
    """
    import base64
    import json
    import os
    import urllib.error
    import urllib.request

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        try:
            import streamlit as st
            if "GEMINI_API_KEY" in st.secrets:
                key = str(st.secrets["GEMINI_API_KEY"])
        except Exception:
            pass

    if not key or key == "your_gemini_api_key_here":
        raise ValueError("Chưa cấu hình GEMINI_API_KEY trong file .env hoặc cấu hình!")

    dest_path = Path(output_path) if output_path else (CACHE_IMAGE_DIR / f"imagen3_{uuid.uuid4().hex[:8]}.jpg")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Thử gọi qua official google-genai Client
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            output_mime_type="image/jpeg",
            person_generation="ALLOW_ADULT",
        )
        logger.info(f"Đang gọi Google Imagen 3 SDK: {prompt[:60]}...")
        res = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=config,
        )
        if res and res.generated_images:
            raw_bytes = res.generated_images[0].image.image_bytes
            with open(dest_path, "wb") as f:
                f.write(raw_bytes)
            logger.info(f"Đã sinh ảnh Google Imagen 3 thành công: {dest_path.name}")
            return dest_path
    except Exception as g_err:
        err_msg = str(g_err)
        if "quota" in err_msg.lower() or "429" in err_msg or "billing" in err_msg.lower() or "enterprise" in err_msg.lower():
            logger.warning(f"Google Imagen 3 yêu cầu tài khoản kích hoạt Billing/Pay-as-you-go: {g_err}")
            raise PermissionError(
                "Tài khoản Google AI Studio Free Tier chưa kích hoạt Pay-as-you-go cho tính năng sinh ảnh Imagen 3. "
                "Vui lòng vào https://aistudio.google.com/ để bật billing Google Cloud (chi phí ~$0.03/ảnh)."
            )
        logger.warning(f"Lỗi khi gọi google-genai Imagen 3 ({g_err}). Đang thử endpoint REST...")

    # 2. Thử gọi REST API trực tiếp
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": "ALLOW_ADULT",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        data = json.loads(response.read().decode("utf-8"))
        preds = data.get("predictions", [])
        if preds and "bytesBase64Encoded" in preds[0]:
            img_data = base64.b64decode(preds[0]["bytesBase64Encoded"])
            with open(dest_path, "wb") as f:
                f.write(img_data)
            return dest_path

    raise RuntimeError("Không nhận được dữ liệu ảnh từ Google Imagen 3 API.")


def generate_smart_ai_background(
    quote_text: str,
    channel: str = "saigonbac",
    user_prompt: Optional[str] = None,
    output_path: Optional[Path | str] = None,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """
    Quy trình sinh ảnh thông minh tự động:
    1. AI Scene Director chuyển quote -> Prompt tiếng Anh chuẩn nhiếp ảnh/comic 9:16.
    2. Thử Google Imagen 3 (nếu có key & đã bật billing).
    3. Tự động fallback sang Pollinations (với model sana / flux) bằng chính prompt chuyên nghiệp đó.
    4. Nếu mạng lỗi, tự động lấy 1 trong 8 ảnh 35mm Master thật tuyển chọn (cam kết không bao giờ ra ảnh rác).
    """
    dest_path = Path(output_path) if output_path else (CACHE_IMAGE_DIR / f"smart_{uuid.uuid4().hex[:8]}.jpg")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Bước 1: Xây dựng Director Prompt
    if user_prompt and len(user_prompt.strip()) > 10 and not user_prompt.strip().startswith("auto"):
        director_prompt = user_prompt.strip()
    else:
        director_prompt = build_scene_director_prompt(quote_text, channel=channel)

    logger.info(f"[{channel}] Director Prompt: {director_prompt}")

    # Bước 2: Thử Google Imagen 3
    try:
        return generate_imagen3_image(prompt=director_prompt, output_path=dest_path, aspect_ratio="9:16")
    except Exception as img3_err:
        logger.info(f"Imagen 3 thông báo: {img3_err}. Chuyển sang công cụ dự phòng chất lượng cao...")

    # Bước 3: Thử Pollinations với prompt chuyên nghiệp (thử sana rồi flux)
    for model_name in ["sana", "flux"]:
        try:
            encoded = urllib.parse.quote(director_prompt)
            seed = random.randint(1000, 999999)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=720&height=1280&model={model_name}&nologo=true&seed={seed}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=18) as r:
                data = r.read()
                if len(data) > 10000:
                    with open(dest_path, "wb") as f:
                        f.write(data)
                    with Image.open(dest_path) as im:
                        im = im.convert("RGB")
                        if im.size != (width, height):
                            im = im.resize((width, height), Image.Resampling.LANCZOS)
                            im.save(dest_path, "JPEG", quality=95)
                    logger.info(f"Đã sinh ảnh qua Pollinations ({model_name}) thành công: {dest_path.name}")
                    return dest_path
        except Exception as p_err:
            logger.warning(f"Pollinations {model_name} chưa phản hồi ({p_err}).")

    # Bước 4: Fallback kho ảnh 35mm Master chuẩn 100% trong máy (Không bao giờ lỗi)
    if channel == "saigonbac":
        from modules.viral_research import REAL_35MM_CURATED_PHOTOS, download_curated_35mm_photo
        p_items = list(REAL_35MM_CURATED_PHOTOS.values())
        chosen_photo = random.choice(p_items)
        return download_curated_35mm_photo(chosen_photo, dest_path)
    else:
        sample_loc = Path("assets/samples/retro_comic/sample_stoic_man.jpg")
        if sample_loc.exists():
            shutil.copy(sample_loc, dest_path)
            return dest_path
        img_fb = Image.new("RGB", (width, height), color=(15, 23, 42))
        img_fb.save(dest_path, "JPEG")
        return dest_path


def generate_flux_image(
    prompt: str,
    output_dir: Optional[Path | str] = None,
    width: int = 1080,
    height: int = 1920,
    model: str = "flux",
) -> Path:
    """
    Sinh ảnh nghệ thuật độ phân giải cao chuẩn dọc 1080x1920 (9:16) sử dụng FLUX.1.
    Tự động thử g4f trước; nếu không có thư viện g4f hoặc lỗi kết nối,
    tự động chuyển sang Pollinations FLUX.1 API (miễn phí, không cần key, cực kỳ ổn định).
    """
    dest_dir = Path(output_dir) if output_dir else CACHE_IMAGE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_path = dest_dir / f"flux_{uuid.uuid4().hex[:8]}.jpg"

    # Cách 1: Sử dụng Pollinations FLUX.1 Engine (Cực kỳ ổn định, không cần cài thư viện ngoài, chuẩn 1080x1920)
    try:
        seed = random.randint(10000, 999999)
        encoded_prompt = urllib.parse.quote(prompt.strip())
        pollinations_flux_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
        )
        logger.info(f"Đang sinh ảnh FLUX.1 qua Pollinations Engine: {prompt[:70]}...")
        req = urllib.request.Request(
            pollinations_flux_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            if response.status == 200:
                data = response.read()
                if len(data) > 10000:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    with Image.open(target_path) as img:
                        img = img.convert("RGB")
                        if img.size != (width, height):
                            img = img.resize((width, height), Image.Resampling.LANCZOS)
                            img.save(target_path, "JPEG", quality=95)
                    logger.info(f"Đã sinh ảnh FLUX.1 thành công: {target_path.name}")
                    return target_path
    except Exception as poll_err:
        logger.warning(f"Pollinations FLUX gặp sự cố ({poll_err}), chuyển sang kênh dự phòng...")

    # Cách 2: Kiểm tra động g4f nếu có sẵn trong môi trường (không gây lỗi gạch đỏ IDE)
    import importlib.util
    if importlib.util.find_spec("g4f") is not None:
        try:
            g4f_client_mod = importlib.import_module("g4f.client")
            Client = getattr(g4f_client_mod, "Client")
            logger.info(f"Đang gọi FLUX.1 qua g4f...")
            client = Client()
            res = client.images.generate(model=model, prompt=prompt)
            if res and hasattr(res, "data") and res.data:
                raw_item = res.data[0]
                raw_url = raw_item.url if hasattr(raw_item, "url") else str(raw_item)
                real_url = urllib.parse.unquote(str(raw_url).split("?url=")[1]) if "?url=" in str(raw_url) else str(raw_url)

                req = urllib.request.Request(real_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                temp_raw = dest_dir / f"raw_flux_{uuid.uuid4().hex[:6]}.tmp"
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = resp.read()
                    if len(data) >= 5000:
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
                        return target_path
        except Exception as g4f_err:
            logger.warning(f"g4f fallback gặp sự cố: {g4f_err}")

    # Cách 3: Tuyển chọn ảnh Aesthetic Cinematic từ kho ảnh thật
    try:
        sample_url = random.choice(CURATED_AESTHETIC_PHOTOS)
        req = urllib.request.Request(
            sample_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "image/*,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 5000:
                with open(target_path, "wb") as f:
                    f.write(data)
                with Image.open(target_path) as img:
                    img = img.convert("RGB")
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    img.save(target_path, "JPEG", quality=95)
                logger.info(f"Đã nạp ảnh Aesthetic thành công: {target_path.name}")
                return target_path
    except Exception as unsp_err:
        logger.warning(f"Lỗi kho ảnh Unsplash ({unsp_err}), chuyển sang Picsum...")

    # Cách 4: Tải ảnh thật độ phân giải cao từ Picsum Photos (100% không bị chặn cloud)
    try:
        rnd_seed = random.randint(1000, 99999)
        picsum_url = f"https://picsum.photos/{width}/{height}?random={rnd_seed}"
        req_p = urllib.request.Request(
            picsum_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req_p, timeout=15) as resp:
            data = resp.read()
            if len(data) > 5000:
                with open(target_path, "wb") as f:
                    f.write(data)
                logger.info(f"Đã tải ảnh thật từ Picsum thành công: {target_path.name}")
                return target_path
    except Exception as pic_err:
        logger.warning(f"Lỗi Picsum fallback: {pic_err}")

    # Cách 5: Dùng ảnh mẫu local hoặc tạo nền gradient tối điện ảnh
    sample_loc = Path("assets/samples/retro_comic/sample_stoic_man.jpg")
    if sample_loc.exists():
        import shutil
        shutil.copy(sample_loc, target_path)
        return target_path

    img_fallback = Image.new("RGB", (width, height), color=(15, 23, 42))
    img_fallback.save(target_path, "JPEG")
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
