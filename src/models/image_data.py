"""
图片数据模型

存储和管理二值化图片的像素数据，支持临时图层机制用于实时绘制预览。
"""

import numpy as np
from typing import Optional


class ImageData:
    """
    图片数据类，存储和管理像素数据
    
    使用 NumPy 数组存储二值化图片数据（0 或 255）。
    支持临时图层机制，用于在绘制过程中提供实时预览而不修改原始数据。
    """
    
    def __init__(self, pixels: np.ndarray, original_pixels: Optional[np.ndarray] = None):
        """
        初始化图片数据
        
        Args:
            pixels: 二值化图片数据，形状为 (H, W)，dtype=uint8
            original_pixels: 原始图片数据（用于重新二值化），可选
        """
        if pixels.dtype != np.uint8:
            pixels = pixels.astype(np.uint8)
        
        self.pixels = pixels
        self.height, self.width = pixels.shape
        
        # 保存原始图片用于重新二值化
        if original_pixels is not None:
            self.original_pixels = original_pixels.copy()
        else:
            self.original_pixels = pixels.copy()
        
        # 临时图层用于绘制预览
        self.temp_layer: Optional[np.ndarray] = None
    
    def get_pixel(self, x: int, y: int) -> int:
        """
        获取像素值（带边界检查）
        
        如果有临时层，返回临时层的值；否则返回主图层的值。
        
        Args:
            x: X 坐标
            y: Y 坐标
            
        Returns:
            像素值（0 或 255），如果坐标无效返回 0
        """
        if not self.is_valid_coord(x, y):
            return 0
        
        if self.temp_layer is not None:
            return int(self.temp_layer[y, x])
        return int(self.pixels[y, x])
    
    def set_pixel(self, x: int, y: int, value: int):
        """
        设置像素值（带边界检查）
        
        如果有临时层，写入临时层；否则写入主图层。
        
        Args:
            x: X 坐标
            y: Y 坐标
            value: 像素值（0 或 255）
        """
        if not self.is_valid_coord(x, y):
            return
        
        # 确保值为 0 或 255
        value = 0 if value < 128 else 255
        
        if self.temp_layer is not None:
            self.temp_layer[y, x] = value
        else:
            self.pixels[y, x] = value
    
    def is_valid_coord(self, x: int, y: int) -> bool:
        """
        检查坐标是否在图片范围内
        
        Args:
            x: X 坐标
            y: Y 坐标
            
        Returns:
            True 如果坐标有效，否则 False
        """
        return 0 <= x < self.width and 0 <= y < self.height
    
    def start_temp_layer(self):
        """
        开始绘制：创建临时图层
        
        临时图层是主图层的副本，用于在绘制过程中提供实时预览。
        这遵循 Photoshop 的行为模式。
        """
        self.temp_layer = self.pixels.copy()
    
    def commit_temp_layer(self):
        """
        完成绘制：将临时图层合并到主图层
        
        将临时图层的内容复制到主图层，然后丢弃临时图层。
        """
        if self.temp_layer is not None:
            self.pixels = self.temp_layer
            self.temp_layer = None
    
    def discard_temp_layer(self):
        """
        取消绘制：丢弃临时图层
        
        丢弃临时图层，保持主图层不变。
        """
        self.temp_layer = None
    
    def crop(self, x: int, y: int, width: int, height: int) -> 'ImageData':
        """
        裁剪图片（保留选中区域，删除其余部分）
        
        Args:
            x: 裁剪区域左上角 X 坐标
            y: 裁剪区域左上角 Y 坐标
            width: 裁剪区域宽度
            height: 裁剪区域高度
            
        Returns:
            新的 ImageData 对象，包含裁剪后的图片
        """
        # 确保裁剪区域在有效范围内
        x = max(0, min(x, self.width - 1))
        y = max(0, min(y, self.height - 1))
        width = max(1, min(width, self.width - x))
        height = max(1, min(height, self.height - y))
        
        # 裁剪像素数据
        cropped_pixels = self.pixels[y:y+height, x:x+width].copy()
        cropped_original = self.original_pixels[y:y+height, x:x+width].copy()
        
        return ImageData(cropped_pixels, cropped_original)
    
    def crop_in_place(self, x: int, y: int, width: int, height: int):
        """
        原地裁剪图片（修改当前对象）
        
        保留选中区域，删除其余部分。
        
        Args:
            x: 裁剪区域左上角 X 坐标
            y: 裁剪区域左上角 Y 坐标
            width: 裁剪区域宽度
            height: 裁剪区域高度
        """
        # 确保裁剪区域在有效范围内
        x = max(0, min(x, self.width - 1))
        y = max(0, min(y, self.height - 1))
        width = max(1, min(width, self.width - x))
        height = max(1, min(height, self.height - y))
        
        # 裁剪像素数据
        self.pixels = self.pixels[y:y+height, x:x+width].copy()
        self.original_pixels = self.original_pixels[y:y+height, x:x+width].copy()
        
        # 更新尺寸
        self.height, self.width = self.pixels.shape
        
        # 清除临时图层
        self.temp_layer = None
    
    def copy(self) -> 'ImageData':
        """
        深拷贝图片数据
        
        用于撤销/重做系统保存历史状态。
        
        Returns:
            新的 ImageData 对象，包含相同的数据
        """
        new_image = ImageData(self.pixels.copy(), self.original_pixels.copy())
        if self.temp_layer is not None:
            new_image.temp_layer = self.temp_layer.copy()
        return new_image
    
    def get_current_pixels(self) -> np.ndarray:
        """
        获取当前显示的像素数据
        
        如果有临时层，返回临时层；否则返回主图层。
        
        Returns:
            当前像素数据的引用（不是副本）
        """
        if self.temp_layer is not None:
            return self.temp_layer
        return self.pixels
