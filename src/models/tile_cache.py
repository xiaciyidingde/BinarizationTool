"""
分块缓存模块

实现基于分块的图片渲染缓存系统，用于优化大图片和高缩放级别下的性能。
"""

from typing import Optional, Dict, Tuple
from collections import OrderedDict
import numpy as np
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class TileCache:
    """
    分块缓存类
    
    将图片分成固定大小的块（tile），按需生成和缓存 QPixmap。
    使用 LRU 策略管理内存，只渲染可见区域的块。
    """
    
    def __init__(self, tile_size: int = 256, max_tiles: int = 1000):
        """
        初始化分块缓存
        
        Args:
            tile_size: 块的大小（像素单位），默认 256x256
            max_tiles: 最大缓存块数量，默认 1000（约 250MB 内存用于缓存）
        """
        self.tile_size = tile_size
        self.max_tiles = max_tiles
        
        # 缓存字典：(scale_key, tile_x, tile_y) -> QPixmap
        # 使用 OrderedDict 实现 LRU
        self.cache: OrderedDict[Tuple[int, int, int], QPixmap] = OrderedDict()
        
        # 当前图片数据
        self.pixels: Optional[np.ndarray] = None
        self.image_width: int = 0
        self.image_height: int = 0
        
        # 选区蒙版
        self.selection_mask: Optional[np.ndarray] = None
        
        # 当前缩放级别
        self.current_scale: float = 1.0
    
    def set_image(self, pixels: np.ndarray, selection_mask: Optional[np.ndarray] = None):
        """
        设置图片数据
        
        Args:
            pixels: 图片像素数据，形状为 (H, W) 或 (H, W, C)，dtype=uint8
            selection_mask: 选区蒙版，形状为 (H, W)，dtype=bool（可选）
        """
        self.pixels = pixels
        # 支持灰度图 (H, W) 和彩色图 (H, W, C)
        if len(pixels.shape) == 2:
            self.image_height, self.image_width = pixels.shape
        else:
            self.image_height, self.image_width = pixels.shape[:2]
        self.selection_mask = selection_mask
        self.clear()
    
    def update_image(self, pixels: np.ndarray, selection_mask: Optional[np.ndarray] = None):
        """
        更新图片数据但不清空缓存
        
        用于绘制过程中的增量更新。
        
        Args:
            pixels: 图片像素数据，形状为 (H, W) 或 (H, W, C)，dtype=uint8
            selection_mask: 选区蒙版，形状为 (H, W)，dtype=bool（可选）
        """
        self.pixels = pixels
        # 支持灰度图 (H, W) 和彩色图 (H, W, C)
        if len(pixels.shape) == 2:
            self.image_height, self.image_width = pixels.shape
        else:
            self.image_height, self.image_width = pixels.shape[:2]
        self.selection_mask = selection_mask
    
    def set_scale(self, scale: float):
        """
        设置缩放级别
        
        如果缩放级别变化，清空缓存。
        
        Args:
            scale: 缩放因子
        """
        if abs(scale - self.current_scale) > 0.001:
            self.current_scale = scale
            self.clear()
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()
    
    def invalidate_region(self, x: int, y: int, width: int, height: int):
        """
        使指定区域的缓存失效（像素坐标）
        
        Args:
            x: 区域左上角 X 坐标（像素）
            y: 区域左上角 Y 坐标（像素）
            width: 区域宽度（像素）
            height: 区域高度（像素）
        """
        if self.pixels is None:
            return
        
        # 计算受影响的块范围
        tile_x_start = x // self.tile_size
        tile_y_start = y // self.tile_size
        tile_x_end = (x + width - 1) // self.tile_size
        tile_y_end = (y + height - 1) // self.tile_size
        
        # 删除受影响的块
        scale_key = self._get_scale_key()
        keys_to_remove = []
        
        for key in self.cache.keys():
            if key[0] == scale_key:
                tile_x, tile_y = key[1], key[2]
                if (tile_x_start <= tile_x <= tile_x_end and 
                    tile_y_start <= tile_y <= tile_y_end):
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def get_tile(self, tile_x: int, tile_y: int) -> Optional[QPixmap]:
        """
        获取指定块的 QPixmap
        
        如果缓存中不存在，则生成并缓存。
        
        Args:
            tile_x: 块的 X 索引
            tile_y: 块的 Y 索引
            
        Returns:
            QPixmap 对象，如果块无效则返回 None
        """
        if self.pixels is None:
            return None
        
        scale_key = self._get_scale_key()
        cache_key = (scale_key, tile_x, tile_y)
        
        # 检查缓存
        if cache_key in self.cache:
            # LRU: 移到末尾
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        
        # 生成新块
        pixmap = self._generate_tile(tile_x, tile_y)
        if pixmap is None:
            return None
        
        # 添加到缓存
        self.cache[cache_key] = pixmap
        self.cache.move_to_end(cache_key)
        
        # LRU 淘汰
        while len(self.cache) > self.max_tiles:
            self.cache.popitem(last=False)
        
        return pixmap
    
    def get_tiles_in_viewport(self, view_x: float, view_y: float, 
                              view_width: int, view_height: int) -> list[Tuple[int, int, float, float, int, int, QPixmap]]:
        """
        获取视口内的所有块
        
        Args:
            view_x: 视口左上角 X 坐标（视图坐标）
            view_y: 视口左上角 Y 坐标（视图坐标）
            view_width: 视口宽度
            view_height: 视口高度
            
        Returns:
            列表，每个元素为 (tile_x, tile_y, draw_x, draw_y, width, height, pixmap)
            - tile_x, tile_y: 块索引
            - draw_x, draw_y: 绘制位置（视图坐标，浮点数）
            - width, height: 绘制尺寸（整数）
            - pixmap: QPixmap 对象
        """
        if self.pixels is None:
            return []
        
        # 计算视口对应的像素范围
        pixel_x_start = max(0, int(-view_x / self.current_scale))
        pixel_y_start = max(0, int(-view_y / self.current_scale))
        pixel_x_end = min(self.image_width, int((view_width - view_x) / self.current_scale) + 1)
        pixel_y_end = min(self.image_height, int((view_height - view_y) / self.current_scale) + 1)
        
        # 计算需要的块范围
        tile_x_start = pixel_x_start // self.tile_size
        tile_y_start = pixel_y_start // self.tile_size
        tile_x_end = pixel_x_end // self.tile_size
        tile_y_end = pixel_y_end // self.tile_size
        
        # 获取所有可见块
        tiles = []
        for tile_y in range(tile_y_start, tile_y_end + 1):
            for tile_x in range(tile_x_start, tile_x_end + 1):
                pixmap = self.get_tile(tile_x, tile_y)
                if pixmap is not None:
                    # 计算块在像素坐标中的位置
                    pixel_x = tile_x * self.tile_size
                    pixel_y = tile_y * self.tile_size
                    
                    # 计算块的实际像素大小
                    tile_width = min(self.tile_size, self.image_width - pixel_x)
                    tile_height = min(self.tile_size, self.image_height - pixel_y)
                    
                    # 计算精确的视图坐标和尺寸
                    draw_x = view_x + pixel_x * self.current_scale
                    draw_y = view_y + pixel_y * self.current_scale
                    draw_width = round(tile_width * self.current_scale)
                    draw_height = round(tile_height * self.current_scale)
                    
                    tiles.append((tile_x, tile_y, draw_x, draw_y, draw_width, draw_height, pixmap))
        
        return tiles
    
    def _generate_tile(self, tile_x: int, tile_y: int) -> Optional[QPixmap]:
        """
        生成指定块的 QPixmap
        
        Args:
            tile_x: 块的 X 索引
            tile_y: 块的 Y 索引
            
        Returns:
            QPixmap 对象，如果块无效则返回 None
        """
        if self.pixels is None:
            return None
        
        # 计算块的像素范围
        pixel_x = tile_x * self.tile_size
        pixel_y = tile_y * self.tile_size
        
        # 检查是否超出图片范围
        if pixel_x >= self.image_width or pixel_y >= self.image_height:
            return None
        
        # 计算实际块大小（边缘块可能不完整）
        tile_width = min(self.tile_size, self.image_width - pixel_x)
        tile_height = min(self.tile_size, self.image_height - pixel_y)
        
        # 提取块数据（必须复制以确保内存连续）
        tile_data = self.pixels[pixel_y:pixel_y+tile_height, pixel_x:pixel_x+tile_width].copy()
        
        # 判断是灰度图还是彩色图
        is_color = len(tile_data.shape) == 3
        
        # 如果有选区，叠加红色覆盖层
        if self.selection_mask is not None:
            # 提取选区块
            selection_tile = self.selection_mask[pixel_y:pixel_y+tile_height, pixel_x:pixel_x+tile_width]
            
            # 转换为 RGB 以支持红色覆盖
            if is_color:
                # 已经是彩色图，直接复制
                tile_rgb = tile_data.copy()
            else:
                # 灰度图转 RGB
                tile_rgb = np.stack([tile_data, tile_data, tile_data], axis=-1)
            
            # 将选中的像素设置为红色 (255, 0, 0)
            tile_rgb[selection_tile] = [255, 0, 0]
            
            # 确保数据是 C-contiguous
            if not tile_rgb.flags['C_CONTIGUOUS']:
                tile_rgb = np.ascontiguousarray(tile_rgb)
            
            # 转换为 QImage (RGB)
            bytes_per_line = tile_width * 3
            qimage = QImage(
                tile_rgb.data,
                tile_width,
                tile_height,
                bytes_per_line,
                QImage.Format_RGB888
            ).copy()
        else:
            # 没有选区
            if is_color:
                # 彩色图
                # 确保数据是 C-contiguous
                if not tile_data.flags['C_CONTIGUOUS']:
                    tile_data = np.ascontiguousarray(tile_data)
                
                # 转换为 QImage (RGB)
                bytes_per_line = tile_width * 3
                qimage = QImage(
                    tile_data.data,
                    tile_width,
                    tile_height,
                    bytes_per_line,
                    QImage.Format_RGB888
                ).copy()
            else:
                # 灰度图
                # 确保数据是 C-contiguous
                if not tile_data.flags['C_CONTIGUOUS']:
                    tile_data = np.ascontiguousarray(tile_data)
                
                # 转换为 QImage
                bytes_per_line = tile_width
                qimage = QImage(
                    tile_data.data, 
                    tile_width, 
                    tile_height, 
                    bytes_per_line, 
                    QImage.Format_Grayscale8
                ).copy()
        
        # 缩放到视图大小 - 使用 round 而不是 int 以减少累积误差
        scaled_width = round(tile_width * self.current_scale)
        scaled_height = round(tile_height * self.current_scale)
        
        # 确保至少为 1 像素
        scaled_width = max(1, scaled_width)
        scaled_height = max(1, scaled_height)
        
        # 选择合适的缩放算法
        transform_mode = Qt.SmoothTransformation if self.current_scale < 1.0 else Qt.FastTransformation
        
        # 创建 QPixmap
        pixmap = QPixmap.fromImage(qimage).scaled(
            scaled_width,
            scaled_height,
            Qt.IgnoreAspectRatio,  # 使用 IgnoreAspectRatio 确保精确尺寸
            transform_mode
        )
        
        return pixmap
    
    def _get_scale_key(self) -> int:
        """
        获取当前缩放级别的键
        
        将浮点数缩放因子转换为整数键，用于缓存索引。
        精度为 0.01。
        
        Returns:
            缩放级别键
        """
        return int(self.current_scale * 100)
    
    def get_cache_info(self) -> Dict[str, any]:
        """
        获取缓存统计信息（用于调试）
        
        Returns:
            包含缓存统计的字典
        """
        return {
            'cached_tiles': len(self.cache),
            'max_tiles': self.max_tiles,
            'tile_size': self.tile_size,
            'current_scale': self.current_scale,
            'image_size': (self.image_width, self.image_height) if self.pixels is not None else None
        }
