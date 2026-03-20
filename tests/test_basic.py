"""
基础功能测试
"""

import numpy as np
import pytest
from src.models.view_transform import ViewTransform
from src.models.image_data import ImageData
from src.models.brush_stroke import BrushStroke
from src.utils.binarization_engine import BinarizationEngine


def test_view_transform_roundtrip():
    """测试坐标转换往返一致性"""
    transform = ViewTransform(scale=2.0, offset_x=10.0, offset_y=20.0)
    
    # 像素坐标
    px, py = 100, 200
    
    # 转换到视图坐标再转换回来
    vx, vy = transform.pixel_to_view(px, py)
    px2, py2 = transform.view_to_pixel(vx, vy)
    
    assert px == px2
    assert py == py2


def test_image_data_pixel_access():
    """测试图片数据像素访问"""
    pixels = np.zeros((10, 10), dtype=np.uint8)
    image = ImageData(pixels)
    
    # 设置像素
    image.set_pixel(5, 5, 255)
    assert image.get_pixel(5, 5) == 255
    
    # 边界检查
    assert image.is_valid_coord(0, 0) == True
    assert image.is_valid_coord(9, 9) == True
    assert image.is_valid_coord(10, 10) == False
    assert image.is_valid_coord(-1, 0) == False


def test_image_data_temp_layer():
    """测试临时图层机制"""
    pixels = np.zeros((10, 10), dtype=np.uint8)
    image = ImageData(pixels)
    
    # 开始临时图层
    image.start_temp_layer()
    image.set_pixel(5, 5, 255)
    
    # 临时图层应该有修改
    assert image.get_pixel(5, 5) == 255
    
    # 丢弃临时图层
    image.discard_temp_layer()
    
    # 主图层应该没有修改
    assert image.get_pixel(5, 5) == 0


def test_binarization_fixed_threshold():
    """测试固定阈值二值化"""
    # 创建测试图片
    image = np.array([[100, 150], [50, 200]], dtype=np.uint8)
    
    # 应用阈值 127
    result = BinarizationEngine.apply_fixed_threshold(image, 127)
    
    # 验证结果
    assert result[0, 0] == 0    # 100 < 127
    assert result[0, 1] == 255  # 150 > 127
    assert result[1, 0] == 0    # 50 < 127
    assert result[1, 1] == 255  # 200 > 127


def test_brush_stroke_rasterize():
    """测试画笔笔画光栅化"""
    pixels = np.zeros((20, 20), dtype=np.uint8)
    image = ImageData(pixels)
    
    # 创建笔画
    stroke = BrushStroke(size=5.0, color=255, hardness=1.0)
    stroke.add_point(10, 10)
    
    # 光栅化
    stroke.rasterize(image)
    
    # 验证中心点被绘制
    assert image.get_pixel(10, 10) == 255


def test_crop():
    """测试裁剪功能"""
    # 创建测试图片
    pixels = np.arange(100, dtype=np.uint8).reshape(10, 10)
    image = ImageData(pixels)
    
    # 裁剪（返回新对象）
    cropped = image.crop(2, 2, 5, 5)
    
    # 验证尺寸
    assert cropped.width == 5
    assert cropped.height == 5
    
    # 验证内容
    assert cropped.get_pixel(0, 0) == image.get_pixel(2, 2)


def test_crop_in_place():
    """测试原地裁剪功能"""
    # 创建测试图片
    pixels = np.arange(100, dtype=np.uint8).reshape(10, 10)
    image = ImageData(pixels)
    
    # 保存原始值
    original_value = image.get_pixel(2, 2)
    
    # 原地裁剪
    image.crop_in_place(2, 2, 5, 5)
    
    # 验证尺寸
    assert image.width == 5
    assert image.height == 5
    
    # 验证内容（原来的 (2,2) 现在是 (0,0)）
    assert image.get_pixel(0, 0) == original_value


def test_binarization_methods():
    """测试所有二值化方法"""
    from src.utils.binarization_engine import BinarizationEngine
    
    # 创建测试图片
    image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    # 测试所有 7 种方法
    for method in range(7):
        result = BinarizationEngine.apply_threshold(image, method, 127)
        
        # 验证结果是二值化的
        assert result.dtype == np.uint8
        assert result.shape == image.shape
        unique_values = np.unique(result)
        assert len(unique_values) <= 2  # 只有 0 和 255
        assert all(v in [0, 255] for v in unique_values)


def test_history_manager_undo_redo():
    """测试撤销/重做功能"""
    from src.models.history_manager import HistoryManager
    
    # 创建历史管理器
    history = HistoryManager()
    
    # 创建初始状态
    pixels1 = np.zeros((10, 10), dtype=np.uint8)
    image1 = ImageData(pixels1)
    history.push_state(image1)
    
    # 修改并保存第二个状态
    pixels2 = np.ones((10, 10), dtype=np.uint8) * 100
    image2 = ImageData(pixels2)
    history.push_state(image2)
    
    # 修改并保存第三个状态
    pixels3 = np.ones((10, 10), dtype=np.uint8) * 200
    image3 = ImageData(pixels3)
    history.push_state(image3)
    
    # 测试撤销
    assert history.can_undo()
    restored = history.undo(image3)
    assert np.array_equal(restored.pixels, image2.pixels)
    
    # 再次撤销
    assert history.can_undo()
    restored = history.undo(image2)
    assert np.array_equal(restored.pixels, image1.pixels)
    
    # 测试重做
    assert history.can_redo()
    restored = history.redo()
    assert np.array_equal(restored.pixels, image2.pixels)
    
    # 再次重做
    assert history.can_redo()
    restored = history.redo()
    assert np.array_equal(restored.pixels, image3.pixels)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
