"""
坐标转换工具类

管理三层坐标系统的转换：
- 屏幕坐标 (Screen): Canvas widget 上的像素位置
- 视图坐标 (View): 考虑平移和缩放后的坐标
- 图像坐标 (Image): 图像像素的实际坐标
"""

import numpy as np
from typing import Tuple, Optional


class CoordinateTransform:
    """
    坐标转换管理器
    
    处理屏幕、视图、图像三层坐标系统之间的转换
    """
    
    def __init__(self, image_width: int = 0, image_height: int = 0):
        """
        初始化坐标转换器
        
        Args:
            image_width: 图像宽度
            image_height: 图像高度
        """
        self.image_width = image_width
        self.image_height = image_height
        
        # 视图变换参数
        self.scale = 1.0  # 缩放比例
        self.offset_x = 0.0  # X 轴偏移（视图坐标）
        self.offset_y = 0.0  # Y 轴偏移（视图坐标）
        
    def set_image_size(self, width: int, height: int):
        """
        设置图像尺寸
        
        Args:
            width: 图像宽度
            height: 图像高度
        """
        self.image_width = width
        self.image_height = height
        
    def set_transform(self, scale: float, offset_x: float, offset_y: float):
        """
        设置视图变换参数
        
        Args:
            scale: 缩放比例
            offset_x: X 轴偏移
            offset_y: Y 轴偏移
        """
        self.scale = scale
        self.offset_x = offset_x
        self.offset_y = offset_y
        
    def screen_to_view(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        屏幕坐标 → 视图坐标
        
        Args:
            screen_x: 屏幕 X 坐标
            screen_y: 屏幕 Y 坐标
            
        Returns:
            (view_x, view_y) 视图坐标
        """
        view_x = screen_x - self.offset_x
        view_y = screen_y - self.offset_y
        return view_x, view_y
        
    def view_to_screen(self, view_x: float, view_y: float) -> Tuple[float, float]:
        """
        视图坐标 → 屏幕坐标
        
        Args:
            view_x: 视图 X 坐标
            view_y: 视图 Y 坐标
            
        Returns:
            (screen_x, screen_y) 屏幕坐标
        """
        screen_x = view_x + self.offset_x
        screen_y = view_y + self.offset_y
        return screen_x, screen_y
        
    def view_to_image(self, view_x: float, view_y: float) -> Tuple[float, float]:
        """
        视图坐标 → 图像坐标
        
        Args:
            view_x: 视图 X 坐标
            view_y: 视图 Y 坐标
            
        Returns:
            (image_x, image_y) 图像坐标
        """
        image_x = view_x / self.scale
        image_y = view_y / self.scale
        return image_x, image_y
        
    def image_to_view(self, image_x: float, image_y: float) -> Tuple[float, float]:
        """
        图像坐标 → 视图坐标
        
        Args:
            image_x: 图像 X 坐标
            image_y: 图像 Y 坐标
            
        Returns:
            (view_x, view_y) 视图坐标
        """
        view_x = image_x * self.scale
        view_y = image_y * self.scale
        return view_x, view_y
        
    def screen_to_image(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        屏幕坐标 → 图像坐标（组合转换）
        
        Args:
            screen_x: 屏幕 X 坐标
            screen_y: 屏幕 Y 坐标
            
        Returns:
            (image_x, image_y) 图像坐标
        """
        view_x, view_y = self.screen_to_view(screen_x, screen_y)
        return self.view_to_image(view_x, view_y)
        
    def image_to_screen(self, image_x: float, image_y: float) -> Tuple[float, float]:
        """
        图像坐标 → 屏幕坐标（组合转换）
        
        Args:
            image_x: 图像 X 坐标
            image_y: 图像 Y 坐标
            
        Returns:
            (screen_x, screen_y) 屏幕坐标
        """
        view_x, view_y = self.image_to_view(image_x, image_y)
        return self.view_to_screen(view_x, view_y)
        
    def is_valid_image_coord(self, image_x: float, image_y: float) -> bool:
        """
        检查图像坐标是否在有效范围内
        
        Args:
            image_x: 图像 X 坐标
            image_y: 图像 Y 坐标
            
        Returns:
            是否在图像范围内
        """
        return (0 <= image_x < self.image_width and 
                0 <= image_y < self.image_height)
                
    def clamp_to_image(self, image_x: float, image_y: float) -> Tuple[int, int]:
        """
        将坐标限制到图像边界内
        
        Args:
            image_x: 图像 X 坐标
            image_y: 图像 Y 坐标
            
        Returns:
            (clamped_x, clamped_y) 限制后的整数坐标
        """
        x = int(np.clip(image_x, 0, self.image_width - 1))
        y = int(np.clip(image_y, 0, self.image_height - 1))
        return x, y
        
    def get_visible_image_rect(self, canvas_width: int, canvas_height: int) -> Tuple[int, int, int, int]:
        """
        获取当前可见的图像区域（图像坐标）
        
        Args:
            canvas_width: Canvas 宽度
            canvas_height: Canvas 高度
            
        Returns:
            (x, y, width, height) 可见区域的图像坐标
        """
        # 屏幕四个角转换为图像坐标
        top_left_x, top_left_y = self.screen_to_image(0, 0)
        bottom_right_x, bottom_right_y = self.screen_to_image(canvas_width, canvas_height)
        
        # 限制到图像范围
        x = max(0, int(top_left_x))
        y = max(0, int(top_left_y))
        right = min(self.image_width, int(np.ceil(bottom_right_x)))
        bottom = min(self.image_height, int(np.ceil(bottom_right_y)))
        
        width = right - x
        height = bottom - y
        
        return x, y, width, height
        
    def batch_screen_to_image(self, screen_coords: np.ndarray) -> np.ndarray:
        """
        批量转换屏幕坐标到图像坐标（向量化）
        
        Args:
            screen_coords: Nx2 数组，每行是 (screen_x, screen_y)
            
        Returns:
            Nx2 数组，每行是 (image_x, image_y)
        """
        # 屏幕 → 视图
        view_coords = screen_coords - np.array([self.offset_x, self.offset_y])
        # 视图 → 图像
        image_coords = view_coords / self.scale
        return image_coords
        
    def batch_image_to_screen(self, image_coords: np.ndarray) -> np.ndarray:
        """
        批量转换图像坐标到屏幕坐标（向量化）
        
        Args:
            image_coords: Nx2 数组，每行是 (image_x, image_y)
            
        Returns:
            Nx2 数组，每行是 (screen_x, screen_y)
        """
        # 图像 → 视图
        view_coords = image_coords * self.scale
        # 视图 → 屏幕
        screen_coords = view_coords + np.array([self.offset_x, self.offset_y])
        return screen_coords
        
    def get_pixel_size_in_screen(self) -> float:
        """
        获取一个图像像素在屏幕上的大小
        
        Returns:
            屏幕像素数
        """
        return self.scale
        
    def get_screen_size_in_pixels(self) -> float:
        """
        获取一个屏幕像素对应的图像像素数
        
        Returns:
            图像像素数
        """
        return 1.0 / self.scale if self.scale > 0 else 0
