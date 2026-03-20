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
        
        self.pixels = pixels  # 基础二值化图层
        self.height, self.width = pixels.shape
        
        # 保存原始图片用于重新二值化
        if original_pixels is not None:
            self.original_pixels = original_pixels.copy()
        else:
            self.original_pixels = pixels.copy()
        
        # 编辑掩码：标记哪些像素被用户编辑过（True=已编辑）
        self.edit_mask: Optional[np.ndarray] = None  # shape: (H, W), dtype=bool
        
        # 编辑值：存储用户编辑的像素值
        self.edit_values: Optional[np.ndarray] = None  # shape: (H, W), dtype=uint8
        
        # 临时图层用于绘制预览
        self.temp_layer: Optional[np.ndarray] = None
        
        # 临时编辑掩码：记录当前笔画中被编辑的像素
        self.temp_edit_mask: Optional[np.ndarray] = None
    
    def get_pixel(self, x: int, y: int) -> int:
        """
        获取像素值（带边界检查）
        
        优先级：临时层 > 编辑值 > 基础层
        
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
        
        # 如果该像素被编辑过，返回编辑值
        if self.edit_mask is not None and self.edit_mask[y, x]:
            return int(self.edit_values[y, x])
        
        return int(self.pixels[y, x])
    
    def set_pixel(self, x: int, y: int, value: int):
        """
        设置像素值（带边界检查）
        
        优先写入临时层，并标记该像素为已编辑。
        
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
            # 写入临时层
            self.temp_layer[y, x] = value
            # 标记为已编辑
            if self.temp_edit_mask is not None:
                self.temp_edit_mask[y, x] = True
        else:
            # 直接编辑（不在笔画中）
            if self.edit_mask is None:
                self.edit_mask = np.zeros((self.height, self.width), dtype=bool)
                self.edit_values = np.zeros((self.height, self.width), dtype=np.uint8)
            
            self.edit_mask[y, x] = True
            self.edit_values[y, x] = value
    
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
        开始绘制：创建临时图层和临时编辑掩码
        
        临时图层基于当前显示的合成结果，用于在绘制过程中提供实时预览。
        临时编辑掩码用于记录本次笔画中实际被编辑的像素。
        这遵循 Photoshop 的行为模式。
        """
        # 基于当前合成结果创建临时层
        self.temp_layer = self._get_composite_pixels().copy()
        
        # 创建临时编辑掩码
        self.temp_edit_mask = np.zeros((self.height, self.width), dtype=bool)
    
    def commit_temp_layer(self):
        """
        完成绘制：将临时图层中被编辑的像素保存到编辑掩码
        
        只保存临时编辑掩码标记的像素，而不是所有不同的像素。
        这样可以确保只有实际被画笔触碰的像素才会被标记为编辑过的。
        """
        if self.temp_layer is not None and self.temp_edit_mask is not None:
            # 初始化编辑掩码和值（如果不存在）
            if self.edit_mask is None:
                self.edit_mask = np.zeros((self.height, self.width), dtype=bool)
                self.edit_values = np.zeros((self.height, self.width), dtype=np.uint8)
            
            # 只保存被实际编辑的像素
            self.edit_mask[self.temp_edit_mask] = True
            self.edit_values[self.temp_edit_mask] = self.temp_layer[self.temp_edit_mask]
            
            # 清除临时层和临时编辑掩码
            self.temp_layer = None
            self.temp_edit_mask = None
    
    def discard_temp_layer(self):
        """
        取消绘制：丢弃临时图层和临时编辑掩码
        
        丢弃临时图层，保持主图层不变。
        """
        self.temp_layer = None
        self.temp_edit_mask = None
    
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
        
        保留选中区域，删除其余部分。裁剪所有图层。
        
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
        
        # 裁剪所有图层
        self.pixels = self.pixels[y:y+height, x:x+width].copy()
        self.original_pixels = self.original_pixels[y:y+height, x:x+width].copy()
        
        if self.edit_mask is not None:
            self.edit_mask = self.edit_mask[y:y+height, x:x+width].copy()
            self.edit_values = self.edit_values[y:y+height, x:x+width].copy()
        
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
        if self.edit_mask is not None:
            new_image.edit_mask = self.edit_mask.copy()
            new_image.edit_values = self.edit_values.copy()
        if self.temp_layer is not None:
            new_image.temp_layer = self.temp_layer.copy()
        if self.temp_edit_mask is not None:
            new_image.temp_edit_mask = self.temp_edit_mask.copy()
        return new_image
    
    def get_current_pixels(self) -> np.ndarray:
        """
        获取当前显示的像素数据
        
        优先级：临时层 > 合成结果（编辑层 + 基础层）
        
        Returns:
            当前像素数据（可能是副本）
        """
        if self.temp_layer is not None:
            return self.temp_layer
        return self._get_composite_pixels()
    
    def _get_composite_pixels(self) -> np.ndarray:
        """
        获取合成后的像素数据（编辑值叠加在基础层上）
        
        Returns:
            合成后的像素数据（新副本）
        """
        if self.edit_mask is None or not self.edit_mask.any():
            return self.pixels
        
        # 创建基础层的副本
        result = self.pixels.copy()
        
        # 应用编辑掩码
        result[self.edit_mask] = self.edit_values[self.edit_mask]
        
        return result
    
    def update_base_layer(self, new_pixels: np.ndarray):
        """
        更新基础二值化图层（保留编辑图层）
        
        用于在修改二值化参数时更新基础层，同时保留用户的编辑内容。
        
        Args:
            new_pixels: 新的二值化像素数据
        """
        if new_pixels.shape != (self.height, self.width):
            raise ValueError("新像素数据的尺寸必须与当前图片一致")
        
        self.pixels = new_pixels.copy()
