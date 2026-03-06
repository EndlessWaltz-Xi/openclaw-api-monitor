#!/usr/bin/env python3
"""
克隆仓库后可直接运行，无需 pip install：
  python run.py          # 持续监测
  python run.py --once   # 单次检查
"""
import sys
from pathlib import Path

# 将 src 加入路径，便于克隆后直接运行
_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from openclaw_monitor.runner import main_loop

if __name__ == "__main__":
    main_loop()
