"""
真实图片测试

测试应用对真实图片的处理能力
"""

import numpy as np
import pytest
from pathlib import Path
import cv2
from src.models.image_data import ImageData
from src.utils.binarization_engine import BinarizationEngine


# 测试图片路径
TEST_IMAGES = [
    "img/1789x2341.png",
    "img/1920x2176.png",
    "img/10000x5000.jpg"
]


@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_load_real_image(image_path):
    """测试加载真实图片"""
    print(f"\n测试加载: {image_path}")
    
    # 检查文件是否存在
    if not Path(image_path).exists():
        pytest.skip(f"图片不存在: {image_path}")
    
    # 加载图片
    img = cv2.imread(image_path)
    assert img is not None, f"无法加载图片: {image_path}"
    
    # 转换为RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 验证是RGB格式
    assert len(img_rgb.shape) == 3, "图片应该是3维的"
    assert img_rgb.shape[2] == 3, "图片应该有3个通道"
    
    print(f"✅ 成功加载图片，尺寸: {img_rgb.shape}")


@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_preprocess_real_image(image_path):
    """测试预处理真实图片"""
    print(f"\n测试预处理: {image_path}")
    
    if not Path(image_path).exists():
        pytest.skip(f"图片不存在: {image_path}")
    
    # 加载图片
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 应用预处理
    preprocessed = BinarizationEngine.apply_preprocess(
        img_rgb,
        exposure=10,
        contrast=20,
        sharpen=30
    )
    
    # 验证预处理结果
    assert preprocessed.shape == img_rgb.shape, "预处理后尺寸应该不变"
    assert preprocessed.dtype == np.uint8, "预处理结果应该是uint8"
    assert len(preprocessed.shape) == 3, "预处理结果应该是RGB"
    assert preprocessed.shape[2] == 3, "预处理结果应该有3个通道"
    
    print(f"✅ 预处理成功，输出尺寸: {preprocessed.shape}")


@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_binarize_real_image(image_path):
    """测试二值化真实图片"""
    print(f"\n测试二值化: {image_path}")
    
    if not Path(image_path).exists():
        pytest.skip(f"图片不存在: {image_path}")
    
    # 加载图片
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 测试所有二值化方法
    methods = [
        (0, "固定阈值"),
        (1, "Otsu"),
        (2, "自适应阈值"),
        (3, "Niblack"),
        (4, "Sauvola"),
        (5, "Wolf-Jolion"),
        (6, "Bradley-Roth")
    ]
    
    for method, name in methods:
        print(f"  测试方法 {method}: {name}")
        
        # 应用二值化
        binary = BinarizationEngine.apply_threshold(img_rgb, method, 127)
        
        # 验证二值化结果
        assert binary.shape == img_rgb.shape, f"方法{method}二值化后尺寸应该不变"
        assert binary.dtype == np.uint8, f"方法{method}结果应该是uint8"
        assert len(binary.shape) == 3, f"方法{method}结果应该是RGB"
        assert binary.shape[2] == 3, f"方法{method}结果应该有3个通道"
        
        # 验证是二值化的（只有0和255）
        unique_values = np.unique(binary)
        assert len(unique_values) <= 2, f"方法{method}应该只有0和255两个值"
        assert all(v in [0, 255] for v in unique_values), f"方法{method}值应该是0或255"
        
        print(f"    ✅ 方法{method}成功")
    
    print(f"✅ 所有二值化方法测试通过")


@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_image_data_with_real_image(image_path):
    """测试ImageData处理真实图片"""
    print(f"\n测试ImageData: {image_path}")
    
    if not Path(image_path).exists():
        pytest.skip(f"图片不存在: {image_path}")
    
    # 加载图片
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 创建ImageData对象
    image_data = ImageData(img_rgb)
    
    # 验证基本属性
    assert image_data.width == img_rgb.shape[1], "宽度应该正确"
    assert image_data.height == img_rgb.shape[0], "高度应该正确"
    assert image_data.pixels.shape == img_rgb.shape, "像素数组尺寸应该正确"
    
    # 测试像素访问
    pixel = image_data.get_pixel(100, 100)
    assert isinstance(pixel, int), "get_pixel应该返回整数"
    assert 0 <= pixel <= 255, "像素值应该在0-255范围内"
    
    # 测试像素设置
    image_data.set_pixel(100, 100, 255)
    assert image_data.get_pixel(100, 100) == 255, "设置像素应该生效"
    
    print(f"✅ ImageData测试通过，尺寸: {image_data.width}x{image_data.height}")


@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_full_pipeline_real_image(image_path):
    """测试完整处理流程"""
    print(f"\n测试完整流程: {image_path}")
    
    if not Path(image_path).exists():
        pytest.skip(f"图片不存在: {image_path}")
    
    # 加载图片
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    print(f"  1. 加载图片: {img_rgb.shape}")
    
    # 预处理
    preprocessed = BinarizationEngine.apply_preprocess(
        img_rgb,
        equalize=True,
        sharpen=20,
        denoise=10,
        denoise_method=1
    )
    print(f"  2. 预处理完成: {preprocessed.shape}")
    assert preprocessed.shape == img_rgb.shape
    
    # 二值化
    binary = BinarizationEngine.apply_threshold(preprocessed, 1, 127)  # Otsu
    print(f"  3. 二值化完成: {binary.shape}")
    assert binary.shape == img_rgb.shape
    
    # 创建ImageData
    image_data = ImageData(binary, img_rgb)
    print(f"  4. 创建ImageData: {image_data.width}x{image_data.height}")
    
    # 测试裁剪
    if image_data.width > 200 and image_data.height > 200:
        cropped = image_data.crop(50, 50, 100, 100)
        print(f"  5. 裁剪测试: {cropped.width}x{cropped.height}")
        assert cropped.width == 100
        assert cropped.height == 100
    
    print(f"✅ 完整流程测试通过")


def test_memory_usage():
    """测试内存使用情况"""
    print("\n测试内存使用")
    
    # 测试大图片
    large_image_path = "img/10000x5000.jpg"
    if not Path(large_image_path).exists():
        pytest.skip(f"大图片不存在: {large_image_path}")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # 加载大图片
    img = cv2.imread(large_image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    mem_after_load = process.memory_info().rss / 1024 / 1024
    print(f"  加载后内存: {mem_after_load:.2f} MB (增加 {mem_after_load - mem_before:.2f} MB)")
    
    # 预处理
    preprocessed = BinarizationEngine.apply_preprocess(img_rgb)
    
    mem_after_preprocess = process.memory_info().rss / 1024 / 1024
    print(f"  预处理后内存: {mem_after_preprocess:.2f} MB (增加 {mem_after_preprocess - mem_after_load:.2f} MB)")
    
    # 二值化
    binary = BinarizationEngine.apply_threshold(preprocessed, 1, 127)
    
    mem_after_binary = process.memory_info().rss / 1024 / 1024
    print(f"  二值化后内存: {mem_after_binary:.2f} MB (增加 {mem_after_binary - mem_after_preprocess:.2f} MB)")
    
    # 清理
    del img, img_rgb, preprocessed, binary
    
    print(f"✅ 内存测试完成")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
