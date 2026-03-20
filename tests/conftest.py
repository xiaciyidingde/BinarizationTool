"""
Pytest 配置和共享 fixtures
"""

import pytest

# 尝试配置 Hypothesis（如果已安装）
try:
    from hypothesis import settings, Verbosity
    settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
    settings.load_profile("default")
except ImportError:
    pass  # Hypothesis 未安装，跳过配置


@pytest.fixture
def sample_image_data():
    """创建一个简单的测试图片数据"""
    import numpy as np
    from src.models.image_data import ImageData
    
    # 创建一个 10x10 的测试图片
    pixels = np.zeros((10, 10), dtype=np.uint8)
    return ImageData(pixels)
