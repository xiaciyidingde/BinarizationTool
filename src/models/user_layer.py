"""
用户图层模块

定义用户图层类，用于存储从选区保存的二值化像素区域。
"""

import uuid
from datetime import datetime
import numpy as np


class UserLayer:
    """
    用户图层类
    
    表示用户从选区保存的二值化像素区域。
    图层保存固化的二值化结果，不受后续参数调整影响。
    """
    
    def __init__(
        self,
        name: str,
        pixels: np.ndarray,
        mask: np.ndarray,
        bbox: tuple[int, int, int, int]
    ):
        """
        初始化用户图层
        
        Args:
            name: 图层名称
            pixels: 二值化像素数据（裁剪到边界框）
            mask: 布尔掩码（裁剪到边界框）
            bbox: 边界框 (x, y, width, height)
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.pixels = pixels.copy()  # 深拷贝
        self.mask = mask.copy()
        self.bbox = bbox
        
        # 状态
        self.visible = True
        self.locked = False
        self.created_at = datetime.now()
    
    def get_bbox(self) -> tuple[int, int, int, int]:
        """获取边界框"""
        return self.bbox
    
    def get_full_mask(self, image_shape: tuple[int, int]) -> np.ndarray:
        """
        获取完整图像尺寸的掩码
        
        Args:
            image_shape: 图像尺寸 (height, width)
            
        Returns:
            与图像相同尺寸的布尔掩码
        """
        full_mask = np.zeros(image_shape, dtype=bool)
        x, y, w, h = self.bbox
        full_mask[y:y+h, x:x+w] = self.mask
        return full_mask
    
    def get_full_pixels(self, image_shape: tuple[int, int]) -> np.ndarray:
        """
        获取完整图像尺寸的像素数据
        
        Args:
            image_shape: 图像尺寸 (height, width)
            
        Returns:
            与图像相同尺寸的像素数组，非图层区域为 255（白色）
        """
        h, w = image_shape
        full_pixels = np.full((h, w), 255, dtype=np.uint8)
        
        x, y, bw, bh = self.bbox
        
        # 只复制掩码为 True 的像素
        full_pixels[y:y+bh, x:x+bw][self.mask] = self.pixels[self.mask]
        
        return full_pixels
    
    def copy(self) -> 'UserLayer':
        """创建图层的深拷贝"""
        layer = UserLayer(
            name=f"{self.name}",
            pixels=self.pixels,
            mask=self.mask,
            bbox=self.bbox
        )
        layer.visible = self.visible
        layer.locked = self.locked
        return layer
    
    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            'id': self.id,
            'name': self.name,
            'bbox': self.bbox,
            'visible': self.visible,
            'locked': self.locked,
            'created_at': self.created_at.isoformat(),
        }
    
    @staticmethod
    def from_dict(data: dict, pixels: np.ndarray, mask: np.ndarray) -> 'UserLayer':
        """从字典创建图层（用于反序列化）"""
        layer = UserLayer(
            name=data['name'],
            pixels=pixels,
            mask=mask,
            bbox=tuple(data['bbox'])
        )
        layer.id = data['id']
        layer.visible = data['visible']
        layer.locked = data['locked']
        layer.created_at = datetime.fromisoformat(data['created_at'])
        return layer
