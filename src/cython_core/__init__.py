"""
Cython 加速模块
"""

import glob
import os
import sys

# 智能 DLL 加载：同时查询当前目录和根目录
# 开发环境：DLL 在 src/cython_core/
# 打包环境：DLL 可能在根目录

# 获取当前目录和根目录
current_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 动态检测 DLL 文件（支持不同 Python 版本和操作系统）
dll_patterns = [
    'dithering.cp3*.pyd',      # Windows: Python 3.x
    'dithering.cp3*.so',       # Linux/Mac: Python 3.x
]

# 按优先级查找：当前目录 -> 根目录
search_paths = [current_dir, root_dir]

for search_path in search_paths:
    for pattern in dll_patterns:
        if glob.glob(os.path.join(search_path, pattern)):
            if search_path not in sys.path:
                sys.path.insert(0, search_path)
            break
    else:
        continue
    break

from .dithering import atkinson, floyd_steinberg, ordered_dithering

__all__ = [
    'floyd_steinberg',
    'atkinson',
    'ordered_dithering',
]
