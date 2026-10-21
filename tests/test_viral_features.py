import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from modules.viral_research import (
    score_hook_strength,
    get_random_outlier_hooks,
    boost_quote_with_ai,
)

def test_viral_research_basics():
    # 1. Kiểm tra chấm điểm Hook
    sample_text = "Bước qua tuổi 25 bạn sẽ nhận ra một điều tàn nhẫn: người càng tử tế càng dễ chịu thiệt thòi."
    result = score_hook_strength(sample_text)
    assert result["score"] >= 80, f"Expected high score, got {result['score']}"
    assert result["word_count"] > 0
    assert len(result["reasons"]) > 0

    # 2. Kiểm tra kho Outlier Hooks
    hooks_sg = get_random_outlier_hooks("saigonbac", limit=3)
    assert len(hooks_sg) == 3
    for h in hooks_sg:
        assert "hook" in h and "category" in h

    hooks_new = get_random_outlier_hooks("kenh_moi", limit=3)
    assert len(hooks_new) == 3

    # 3. Kiểm tra fallback AI Booster (khi không có API key)
    boosted = boost_quote_with_ai(sample_text, channel="saigonbac")
    assert "hook_contradiction" in boosted
    assert "hook_harsh_truth" in boosted
    assert "hook_open_loop" in boosted

    print("All viral research tests passed successfully!")

if __name__ == "__main__":
    test_viral_research_basics()
