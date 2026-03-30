"""
坐标转换测试

测试三层坐标系统的转换功能
"""

import pytest
import numpy as np
from src.utils.coordinate_transform import CoordinateTransform


class TestCoordinateTransform:
    """坐标转换测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        coord = CoordinateTransform(1920, 1080)
        assert coord.image_width == 1920
        assert coord.image_height == 1080
        assert coord.scale == 1.0
        assert coord.offset_x == 0.0
        assert coord.offset_y == 0.0
        
    def test_set_image_size(self):
        """测试设置图像尺寸"""
        coord = CoordinateTransform()
        coord.set_image_size(800, 600)
        assert coord.image_width == 800
        assert coord.image_height == 600
        
    def test_set_transform(self):
        """测试设置变换参数"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 100.0, 50.0)
        assert coord.scale == 2.0
        assert coord.offset_x == 100.0
        assert coord.offset_y == 50.0
        
    def test_screen_to_view(self):
        """测试屏幕坐标到视图坐标"""
        coord = CoordinateTransform()
        coord.set_transform(1.0, 100.0, 50.0)
        
        view_x, view_y = coord.screen_to_view(200, 150)
        assert view_x == 100.0  # 200 - 100
        assert view_y == 100.0  # 150 - 50
        
    def test_view_to_screen(self):
        """测试视图坐标到屏幕坐标"""
        coord = CoordinateTransform()
        coord.set_transform(1.0, 100.0, 50.0)
        
        screen_x, screen_y = coord.view_to_screen(100, 100)
        assert screen_x == 200.0  # 100 + 100
        assert screen_y == 150.0  # 100 + 50
        
    def test_view_to_image(self):
        """测试视图坐标到图像坐标"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 0.0, 0.0)
        
        image_x, image_y = coord.view_to_image(200, 100)
        assert image_x == 100.0  # 200 / 2
        assert image_y == 50.0   # 100 / 2
        
    def test_image_to_view(self):
        """测试图像坐标到视图坐标"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 0.0, 0.0)
        
        view_x, view_y = coord.image_to_view(100, 50)
        assert view_x == 200.0  # 100 * 2
        assert view_y == 100.0  # 50 * 2
        
    def test_screen_to_image(self):
        """测试屏幕坐标到图像坐标（组合转换）"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 100.0, 50.0)
        
        # 屏幕 (300, 250) -> 视图 (200, 200) -> 图像 (100, 100)
        image_x, image_y = coord.screen_to_image(300, 250)
        assert image_x == 100.0
        assert image_y == 100.0
        
    def test_image_to_screen(self):
        """测试图像坐标到屏幕坐标（组合转换）"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 100.0, 50.0)
        
        # 图像 (100, 100) -> 视图 (200, 200) -> 屏幕 (300, 250)
        screen_x, screen_y = coord.image_to_screen(100, 100)
        assert screen_x == 300.0
        assert screen_y == 250.0
        
    def test_is_valid_image_coord(self):
        """测试图像坐标有效性检查"""
        coord = CoordinateTransform(1920, 1080)
        
        assert coord.is_valid_image_coord(0, 0) is True
        assert coord.is_valid_image_coord(1919, 1079) is True
        assert coord.is_valid_image_coord(960, 540) is True
        
        assert coord.is_valid_image_coord(-1, 0) is False
        assert coord.is_valid_image_coord(0, -1) is False
        assert coord.is_valid_image_coord(1920, 1080) is False
        assert coord.is_valid_image_coord(2000, 1000) is False
        
    def test_clamp_to_image(self):
        """测试坐标限制到图像边界"""
        coord = CoordinateTransform(1920, 1080)
        
        # 正常范围内
        x, y = coord.clamp_to_image(100, 200)
        assert x == 100
        assert y == 200
        
        # 超出边界
        x, y = coord.clamp_to_image(-10, -20)
        assert x == 0
        assert y == 0
        
        x, y = coord.clamp_to_image(2000, 1500)
        assert x == 1919
        assert y == 1079
        
    def test_get_visible_image_rect(self):
        """测试获取可见图像区域"""
        coord = CoordinateTransform(1920, 1080)
        coord.set_transform(1.0, 0.0, 0.0)
        
        x, y, width, height = coord.get_visible_image_rect(800, 600)
        assert x == 0
        assert y == 0
        assert width == 800
        assert height == 600
        
    def test_batch_screen_to_image(self):
        """测试批量屏幕到图像坐标转换"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 100.0, 50.0)
        
        screen_coords = np.array([
            [300, 250],
            [400, 350],
            [500, 450]
        ])
        
        image_coords = coord.batch_screen_to_image(screen_coords)
        
        assert image_coords.shape == (3, 2)
        np.testing.assert_array_almost_equal(image_coords[0], [100.0, 100.0])
        np.testing.assert_array_almost_equal(image_coords[1], [150.0, 150.0])
        np.testing.assert_array_almost_equal(image_coords[2], [200.0, 200.0])
        
    def test_batch_image_to_screen(self):
        """测试批量图像到屏幕坐标转换"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 100.0, 50.0)
        
        image_coords = np.array([
            [100, 100],
            [150, 150],
            [200, 200]
        ])
        
        screen_coords = coord.batch_image_to_screen(image_coords)
        
        assert screen_coords.shape == (3, 2)
        np.testing.assert_array_almost_equal(screen_coords[0], [300.0, 250.0])
        np.testing.assert_array_almost_equal(screen_coords[1], [400.0, 350.0])
        np.testing.assert_array_almost_equal(screen_coords[2], [500.0, 450.0])
        
    def test_get_pixel_size_in_screen(self):
        """测试获取图像像素在屏幕上的大小"""
        coord = CoordinateTransform()
        coord.set_transform(2.5, 0.0, 0.0)
        
        assert coord.get_pixel_size_in_screen() == 2.5
        
    def test_get_screen_size_in_pixels(self):
        """测试获取屏幕像素对应的图像像素数"""
        coord = CoordinateTransform()
        coord.set_transform(2.0, 0.0, 0.0)
        
        assert coord.get_screen_size_in_pixels() == 0.5
        
    def test_roundtrip_conversion(self):
        """测试往返转换的一致性"""
        coord = CoordinateTransform(1920, 1080)
        coord.set_transform(1.5, 200.0, 100.0)
        
        # 屏幕 -> 图像 -> 屏幕
        original_screen = (500, 400)
        image_x, image_y = coord.screen_to_image(*original_screen)
        final_screen = coord.image_to_screen(image_x, image_y)
        
        assert abs(final_screen[0] - original_screen[0]) < 0.001
        assert abs(final_screen[1] - original_screen[1]) < 0.001
