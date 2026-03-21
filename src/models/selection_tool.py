"""
智能选择工具模块

提供类似 Photoshop 的智能选择功能：
- 选择工具（Selection Tool）：点击选择连续的同色区域
- 快速选择工具（Quick Selection）：画刷式智能选择
- 颜色范围选择：全局选择特定颜色
"""

import numpy as np
from typing import Optional, Tuple, TYPE_CHECKING
from collections import deque

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter
    from .image_data import ImageData


class SelectionStroke:
    """
    选择笔画类
    
    类似 BrushStroke，但用于选择操作。
    在笔刷范围内只选择匹配目标颜色的像素。
    """
    
    def __init__(self, size: float, target_color: int, selection_mode: str):
        """
        初始化选择笔画
        
        Args:
            size: 笔刷直径（像素单位）
            target_color: 目标颜色（0=黑色, 255=白色）
            selection_mode: 选择模式（'add'=添加, 'subtract'=减去）
        """
        self.size = size
        self.target_color = target_color
        self.selection_mode = selection_mode
        self.points: list[tuple[int, int]] = []
    
    def add_point(self, x: int, y: int):
        """添加笔画点"""
        self.points.append((x, y))
    
    def rasterize(self, image_data: 'ImageData', selection_mask: np.ndarray, 
                  start_index: int = 0, tolerance: float = 0.71) -> tuple[int, int, int, int]:
        """
        将选择笔画光栅化到选区蒙版
        
        在笔刷范围内选择匹配目标颜色的像素。
        
        Args:
            image_data: 图片数据
            selection_mask: 选区蒙版（输出）
            start_index: 开始光栅化的点索引
            tolerance: 像素边缘容差
            
        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        if start_index >= len(self.points):
            return (0, 0, 0, 0)
        
        radius = self.size / 2.0
        pixels = image_data.get_current_pixels()
        
        # 计算受影响的区域
        x_min = image_data.width
        y_min = image_data.height
        x_max = 0
        y_max = 0
        
        for i in range(start_index, len(self.points)):
            x, y = self.points[i]
            self._select_in_circle(pixels, selection_mask, x, y, radius, tolerance)
            
            # 更新脏区域
            x_min = min(x_min, int(x - radius - 1))
            y_min = min(y_min, int(y - radius - 1))
            x_max = max(x_max, int(x + radius + 2))
            y_max = max(y_max, int(y + radius + 2))
        
        # 限制在图片范围内
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(image_data.width, x_max)
        y_max = min(image_data.height, y_max)
        
        return (x_min, y_min, x_max, y_max)
    
    def _select_in_circle(self, pixels: np.ndarray, selection_mask: np.ndarray,
                         center_x: int, center_y: int, radius: float, tolerance: float):
        """
        在圆形范围内选择匹配目标颜色的像素（NumPy 向量化）
        
        Args:
            pixels: 像素数据
            selection_mask: 选区蒙版（输出）
            center_x: 圆心 X 坐标
            center_y: 圆心 Y 坐标
            radius: 半径
            tolerance: 边缘容差
        """
        height, width = pixels.shape
        
        # 计算边界框（扩大1像素以包含边缘）
        x_min = max(0, int(center_x - radius - 1))
        x_max = min(width - 1, int(center_x + radius + 1))
        y_min = max(0, int(center_y - radius - 1))
        y_max = min(height - 1, int(center_y + radius + 1))
        
        if x_min > x_max or y_min > y_max:
            return
        
        # 创建坐标网格
        y_coords = np.arange(y_min, y_max + 1)
        x_coords = np.arange(x_min, x_max + 1)
        x_grid, y_grid = np.meshgrid(x_coords, y_coords)
        
        # 计算到中心的距离（向量化）
        dx = x_grid - center_x
        dy = y_grid - center_y
        dist = np.sqrt(dx * dx + dy * dy)
        
        # 圆形掩码（带容差）
        circle_mask = dist <= (radius + tolerance)
        
        # 提取区域数据
        region_pixels = pixels[y_min:y_max+1, x_min:x_max+1]
        
        # 颜色匹配掩码
        color_mask = (region_pixels == self.target_color)
        
        # 最终掩码：在圆内且颜色匹配
        final_mask = circle_mask & color_mask
        
        # 根据模式更新选区
        if self.selection_mode == 'add':
            selection_mask[y_min:y_max+1, x_min:x_max+1][final_mask] = True
        elif self.selection_mode == 'subtract':
            selection_mask[y_min:y_max+1, x_min:x_max+1][final_mask] = False


class SelectionTool:
    """
    智能选择工具类
    
    管理选区蒙版和提供多种选择算法。
    复用画笔工具的绘制逻辑，但只选择匹配颜色的像素。
    """
    
    # 选择模式
    MODE_NEW = 'new'        # 新建选区
    MODE_ADD = 'add'        # 添加到选区
    MODE_SUBTRACT = 'subtract'  # 从选区减去
    MODE_INTERSECT = 'intersect'  # 与选区相交
    
    def __init__(self):
        """初始化选择工具"""
        self.selection_mask: Optional[np.ndarray] = None  # 选区蒙版 (H, W), dtype=bool
        self.mode: str = self.MODE_NEW
        self.tolerance: int = 0  # 容差（0-255），对二值化图片通常为0
        self.contiguous: bool = True  # 是否只选择连续区域
        
        # 选择工具参数
        self.size: float = 50.0  # 选择范围大小（像素）
        self.selection_mode: str = 'add'  # 'add'=添加到选区, 'subtract'=从选区减去
        self.target_color: int = 0  # 目标颜色（0=黑色, 255=白色）
        
        # 光标显示
        self.crosshair_threshold: float = 30.0  # 当圆圈小于此值时显示十字
        
        # 拖动选择状态（复用画笔逻辑）
        self.is_dragging: bool = False
        self.current_stroke: Optional[SelectionStroke] = None
        self.spacing: float = 0.25  # 间距因子（相对于笔刷大小）
        self.last_point: Optional[tuple[int, int]] = None
    
    def has_selection(self) -> bool:
        """
        检查是否有活动选区
        
        Returns:
            True 如果有选区，否则 False
        """
        return self.selection_mask is not None and self.selection_mask.any()
    
    def clear_selection(self):
        """清除选区"""
        self.selection_mask = None
    
    def invert_selection(self, width: int, height: int):
        """
        反选
        
        Args:
            width: 图片宽度
            height: 图片高度
        """
        if self.selection_mask is None:
            # 如果没有选区，创建全选
            self.selection_mask = np.ones((height, width), dtype=bool)
        elif self.selection_mask.shape != (height, width):
            # 尺寸不匹配（图片被裁剪了），创建全选
            self.selection_mask = np.ones((height, width), dtype=bool)
        else:
            # 反转选区
            self.selection_mask = ~self.selection_mask
    
    def start_drag_select(self, image_data: 'ImageData', x: int, y: int) -> tuple[int, int, int, int]:
        """
        开始拖动选择（复用画笔逻辑）
        
        Args:
            image_data: 图片数据
            x: 起始 X 坐标
            y: 起始 Y 坐标
            
        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        self.is_dragging = True
        self.last_point = (x, y)
        
        # 创建新的选择笔画
        self.current_stroke = SelectionStroke(self.size, self.target_color, self.selection_mode)
        self.current_stroke.add_point(x, y)
        
        # 初始化选区蒙版
        if self.selection_mask is None or self.selection_mask.shape != (image_data.height, image_data.width):
            self.selection_mask = np.zeros((image_data.height, image_data.width), dtype=bool)
        
        # 光栅化第一个点
        return self.current_stroke.rasterize(image_data, self.selection_mask, 0)
    
    def continue_drag_select(self, image_data: 'ImageData', x: int, y: int) -> tuple[int, int, int, int]:
        """
        继续拖动选择（带插值，避免断点）
        
        Args:
            image_data: 图片数据
            x: 当前 X 坐标
            y: 当前 Y 坐标
            
        Returns:
            脏区域 (x_min, y_min, x_max, y_max)，如果没有更新则返回 (0, 0, 0, 0)
        """
        if not self.is_dragging or self.current_stroke is None or self.last_point is None:
            return (0, 0, 0, 0)
        
        # 计算距离
        last_x, last_y = self.last_point
        dist = ((x - last_x) ** 2 + (y - last_y) ** 2) ** 0.5
        
        # 间距控制
        spacing_threshold = self.size * self.spacing
        
        if dist >= spacing_threshold:
            # 计算需要插入多少个中间点
            num_steps = max(1, int(dist / spacing_threshold))
            
            # 记录开始索引
            start_index = len(self.current_stroke.points)
            
            # 插值添加点
            for i in range(1, num_steps + 1):
                t = i / num_steps
                interp_x = int(last_x + (x - last_x) * t)
                interp_y = int(last_y + (y - last_y) * t)
                self.current_stroke.add_point(interp_x, interp_y)
            
            # 增量光栅化（只处理新点）
            dirty_rect = self.current_stroke.rasterize(image_data, self.selection_mask, start_index)
            
            # 更新最后位置
            self.last_point = (x, y)
            
            return dirty_rect
        
        return (0, 0, 0, 0)
    
    def end_drag_select(self):
        """结束拖动选择"""
        self.is_dragging = False
        self.current_stroke = None
        self.last_point = None
    
    def select_by_color(self, image_data: 'ImageData', color: int):
        """
        按颜色选择：全局选择特定颜色的所有像素
        
        Args:
            image_data: 图片数据
            color: 目标颜色（0=黑色, 255=白色）
        """
        pixels = image_data.get_current_pixels()
        height, width = pixels.shape
        
        # 创建新的选区蒙版
        new_mask = self._global_color_select(pixels, 
                                             np.zeros((height, width), dtype=bool), 
                                             color)
        
        # 根据模式合并选区
        self._merge_selection(new_mask, width, height)
    
    def render_cursor(self, painter: 'QPainter', view_x: float, view_y: float, 
                     view_size: float):
        """
        渲染选择工具光标
        
        绘制圆形外圈显示选择范围。
        外圈颜色表示模式：绿色=添加，红色=删除
        中心圆点表示目标颜色：黑点=选择黑色，白点=选择白色
        
        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
            view_size: 选择范围大小（视图坐标）
        """
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QPen, QColor, QBrush
        
        # 保存当前画笔状态
        old_pen = painter.pen()
        old_brush = painter.brush()
        
        # 根据模式选择外圈颜色
        if self.selection_mode == 'add':
            ring_color = QColor(0, 255, 0)  # 绿色 - 添加
        else:
            ring_color = QColor(255, 0, 0)  # 红色 - 删除
        
        # 根据目标颜色选择中心点颜色
        if self.target_color == 0:
            center_color = QColor(0, 0, 0)  # 黑色 - 选择黑色块
        else:
            center_color = QColor(255, 255, 255)  # 白色 - 选择白色块
        
        radius = view_size / 2.0
        
        # === 第一层：绘制彩色圆形外圈 ===
        pen = QPen(ring_color, 2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(view_x, view_y), radius, radius)
        
        # === 第二层：绘制中心指示点 ===
        center_radius = min(6, radius * 0.3)  # 中心点大小，最大6像素
        if center_radius >= 2:  # 只有当足够大时才显示
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(center_color))
            painter.drawEllipse(QPointF(view_x, view_y), center_radius, center_radius)
            
            # 给中心点添加边框以增强可见性
            border_color = QColor(128, 128, 128)  # 灰色边框
            pen = QPen(border_color, 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(view_x, view_y), center_radius, center_radius)
        
        # === 第三层：绘制十字准星（在圆圈外，只在圆圈小时显示）===
        if view_size < self.crosshair_threshold:
            pen = QPen(ring_color)
            pen.setWidth(2)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
            
            # 十字准星从圆圈边缘开始，向外延伸
            gap = 2
            crosshair_length = 8
            
            # 水平线
            painter.drawLine(
                int(view_x - radius - gap - crosshair_length), int(view_y),
                int(view_x - radius - gap), int(view_y)
            )
            painter.drawLine(
                int(view_x + radius + gap), int(view_y),
                int(view_x + radius + gap + crosshair_length), int(view_y)
            )
            
            # 垂直线
            painter.drawLine(
                int(view_x), int(view_y - radius - gap - crosshair_length),
                int(view_x), int(view_y - radius - gap)
            )
            painter.drawLine(
                int(view_x), int(view_y + radius + gap),
                int(view_x), int(view_y + radius + gap + crosshair_length)
            )
        
        # 恢复画笔状态
        painter.setPen(old_pen)
        painter.setBrush(old_brush)
    
    def _global_color_select(self, pixels: np.ndarray, mask: np.ndarray, 
                            target_color: int) -> np.ndarray:
        """
        全局颜色选择
        
        Args:
            pixels: 像素数据
            mask: 选区蒙版（输出）
            target_color: 目标颜色
            
        Returns:
            更新后的蒙版
        """
        # 选择所有颜色相近的像素
        color_diff = np.abs(pixels.astype(int) - int(target_color))
        mask[color_diff <= self.tolerance] = True
        return mask
    
    def _merge_selection(self, new_mask: np.ndarray, width: int, height: int):
        """
        根据当前模式合并选区
        
        Args:
            new_mask: 新的选区蒙版
            width: 图片宽度
            height: 图片高度
        """
        if self.mode == self.MODE_NEW:
            # 新建选区
            self.selection_mask = new_mask
        elif self.mode == self.MODE_ADD:
            # 添加到选区
            if self.selection_mask is None or self.selection_mask.shape != new_mask.shape:
                # 如果没有选区或尺寸不匹配（图片被裁剪了），直接使用新选区
                self.selection_mask = new_mask
            else:
                self.selection_mask = self.selection_mask | new_mask
        elif self.mode == self.MODE_SUBTRACT:
            # 从选区减去
            if self.selection_mask is not None:
                if self.selection_mask.shape == new_mask.shape:
                    self.selection_mask = self.selection_mask & ~new_mask
                else:
                    # 尺寸不匹配，清除旧选区
                    self.selection_mask = None
        elif self.mode == self.MODE_INTERSECT:
            # 与选区相交
            if self.selection_mask is None or self.selection_mask.shape != new_mask.shape:
                # 如果没有选区或尺寸不匹配，使用空选区
                self.selection_mask = np.zeros((height, width), dtype=bool)
            else:
                self.selection_mask = self.selection_mask & new_mask
