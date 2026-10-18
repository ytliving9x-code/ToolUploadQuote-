import sys
from pathlib import Path

# Đảm bảo root directory luôn có trong sys.path khi chạy test
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
