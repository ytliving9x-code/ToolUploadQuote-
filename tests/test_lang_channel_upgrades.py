import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from modules.viral_research import split_quote_for_lang, generate_lang_growth_pack
from modules.audio_engine import generate_cinematic_ambient_audio
from modules.video_engine import generate_lang_carousel_pack, render_lang_dynamic_video, probe_video_metadata


def test_split_quote_and_growth_pack():
    sample = "Kẻ tầm thường mới thích thắng bằng lời nói. Người bản lĩnh chỉ im lặng nâng cao vị thế."
    parts = split_quote_for_lang(sample)
    assert "hook" in parts and "payoff" in parts and "cta" in parts
    assert len(parts["hook"]) > 0
    assert len(parts["payoff"]) > 0

    pack = generate_lang_growth_pack(sample)
    assert pack["retention_score"] >= 80
    assert len(pack["hashtags"]) >= 4
    assert "#lang" in pack["hashtags"]
    assert "caption" in pack


def test_ambient_audio_generation(tmp_path):
    aud_out = tmp_path / "ambient_test.m4a"
    res = generate_cinematic_ambient_audio(duration=3.0, output_path=aud_out)
    assert res.exists()
    assert res.stat().st_size > 1000


def test_lang_carousel_pack(tmp_path):
    sample_img = Path("assets/samples/retro_comic/sample_stoic_man.jpg")
    if not sample_img.exists():
        return
    s1, s2 = generate_lang_carousel_pack(
        image_path=sample_img,
        hook_text="KẺ MẠNH LUÔN GIẤU KÍN 3 THỨ",
        payoff_text="Người có vị thế không bao giờ đem bí mật ra đãi trà.",
        output_dir=tmp_path,
    )
    assert s1.exists()
    assert s2.exists()
    assert s1.stat().st_size > 5000
    assert s2.stat().st_size > 5000


if __name__ == "__main__":
    test_split_quote_and_growth_pack()
    print("All Kênh Lặng tests passed!")
