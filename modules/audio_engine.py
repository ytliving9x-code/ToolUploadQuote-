from __future__ import annotations

"""
Module Âm Thanh & Lồng Tiếng AI Cho TikTok (audio_engine.py).
Chịu trách nhiệm:
1. Lồng tiếng AI (Text-to-Speech) bằng Edge-TTS với giọng đọc nam trầm 'vi-VN-NamMinhNeural' (chuẩn gu Kênh Lặng: đanh thép, điềm tĩnh).
2. Tạo nhạc nền Ambient Cinematic Drone & Rumble bằng FFmpeg (tần số trầm 65Hz - 130Hz) giúp video có track âm thanh chuẩn, không bị TikTok quét lỗi Mute/Unoriginal.
3. Hòa âm (Audio Mixing): Trộn giọng đọc AI với nhạc nền/ambient sound, cân bằng âm lượng (Voice 100%, Music 15%) theo chuẩn TikTok QC checklist.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("tiktok_tool.audio_engine")

try:
    FFMPEG_EXE = shutil.which("ffmpeg")
    if not FFMPEG_EXE:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"


def clean_text_for_speech(text: str) -> str:
    """Loại bỏ ký tự đặc biệt, emoji, ngoặc kép trước khi chuyển văn bản thành giọng nói."""
    clean = re.sub(r"[—–\-\"\'“”‘’«»#@\(\)\[\]\{\}]", " ", text)
    # Loại bỏ emoji thông thường
    clean = re.sub(r"[\U00010000-\U0010ffff]", "", clean)
    clean = " ".join(clean.split())
    return clean.strip()


def generate_voiceover_edge_tts(
    text: str,
    output_path: Optional[Path | str] = None,
    voice: str = "vi-VN-NamMinhNeural",
    rate: str = "+0%",
    pitch: str = "-2Hz",
) -> Optional[Path]:
    """
    Tạo file âm thanh lồng tiếng AI tiếng Việt chất lượng cao bằng edge-tts.
    Giọng mặc định: vi-VN-NamMinhNeural (Nam miền Bắc trầm ấm, dứt khoát).
    """
    speech_text = clean_text_for_speech(text)
    if not speech_text:
        return None

    out_p = Path(output_path) if output_path else Path("temp") / f"voice_{uuid.uuid4().hex[:6]}.mp3"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    try:
        import edge_tts

        async def _speak() -> None:
            communicate = edge_tts.Communicate(speech_text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(out_p))

        asyncio.run(_speak())

        if out_p.exists() and out_p.stat().st_size > 100:
            logger.info(f"Đã sinh giọng đọc AI thành công: {out_p.name} ({out_p.stat().st_size} bytes)")
            return out_p
    except Exception as e:
        logger.warning(f"Lỗi khi tạo giọng đọc Edge-TTS: {e}. Sẽ dùng nhạc nền thay thế.")

    return None


def generate_cinematic_ambient_audio(
    duration: float = 8.0,
    output_path: Optional[Path | str] = None,
) -> Path:
    """
    Tạo track âm thanh nền Cinematic Ambient Bass Drone & Soft Rumble bằng FFmpeg lavfi.
    Đảm bảo video luôn có track âm thanh stereo hợp lệ, đúng phong cách Kênh Lặng (Tĩnh mịch, quyền uy).
    """
    out_p = Path(output_path) if output_path else Path("temp") / f"ambient_{uuid.uuid4().hex[:6]}.m4a"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Sinh âm thanh tần số thấp 65Hz và 130Hz nhẹ nhàng, có fade in 0.5s và fade out 1.0s
    fade_out_st = max(0.5, duration - 1.0)
    filter_expr = (
        f"aevalsrc=sin(65*2*PI*t)*0.035+sin(130*2*PI*t)*0.018:s=44100:d={duration},"
        f"afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_st:.2f}:d=1.0"
    )

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-f", "lavfi",
        "-i", filter_expr,
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(duration),
        str(out_p),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_p
    except Exception as e:
        logger.error(f"Lỗi sinh ambient audio bằng FFmpeg: {e}")
        # Dự phòng bằng file im lặng nếu FFmpeg filter lỗi
        cmd_null = [
            FFMPEG_EXE,
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-c:a", "aac",
            str(out_p),
        ]
        subprocess.run(cmd_null, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_p


def mix_voice_and_ambient(
    voice_path: Optional[Path | str],
    duration: float = 8.0,
    output_path: Optional[Path | str] = None,
    ambient_volume: float = 0.18,
    voice_volume: float = 1.0,
) -> Path:
    """
    Hòa âm giọng đọc AI và nhạc nền/ambient drone.
    Chuẩn tỷ lệ: Giọng nói 100%, Nhạc nền 15-20% theo QC Checklist TikTok.
    """
    out_p = Path(output_path) if output_path else Path("temp") / f"mixed_audio_{uuid.uuid4().hex[:6]}.m4a"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    v_path = Path(voice_path) if voice_path and Path(voice_path).exists() else None

    # Nếu không có giọng nói, chỉ xuất ambient drone
    if not v_path:
        return generate_cinematic_ambient_audio(duration=duration, output_path=out_p)

    ambient_tmp = generate_cinematic_ambient_audio(duration=duration)

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", str(v_path),
        "-i", str(ambient_tmp),
        "-filter_complex",
        f"[0:a]volume={voice_volume:.2f},apad[a0];"
        f"[1:a]volume={ambient_volume:.2f}[a1];"
        f"[a0][a1]amix=inputs=2:duration=shortest:dropout_transition=2[aout]",
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(duration),
        str(out_p),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_p
    except Exception as e:
        logger.warning(f"Lỗi khi hòa âm ({e}), chuyển sang chỉ dùng giọng đọc.")
        shutil.copy(v_path, out_p)
        return out_p
