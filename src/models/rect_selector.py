"""
矩形选择器模块

提供通用的矩形区域选择功能。
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter, QColor
    from .view_transform import ViewTransform


class RectSelector:
    """
    矩形选择器基类
    
    管理矩形选择的状态和渲染，提供通用的矩形拖动逻辑。
    """
    
    def __init__(self):
        """初始化矩形选择器"""
        self.start_pixel: Optional[tuple[int, int]] = None
        self.end_pixel: Optional[tuple[int, int]] = None
        self.is_dragging: bool = False
    
    def start(self, x: int, y: int):
        """
        开始矩形选择
        
        Args:
            x: 起始 X 坐标（像素）
            y: 起始 Y 坐标（像素）
        """
        self.start_pixel = (x, y)
        self.end_pixel = (x, y)
        self.is_dragging = True
    
    def update(self, x: int, y: int):
        """
        更新矩形选择
        
        Args:
            x: 当前 X 坐标（像素）
            y: 当前 Y 坐标（像素）
        """
        if self.is_dragging and self.start_pixel is not None:
            self.end_pixel = (x, y)
    
    def end(self):
        """结束矩形选择"""
        self.is_dragging = False
    
    def cancel(self):
        """取消矩形选择"""
        self.is_dragging = False
        self.start_pixel = None
        self.end_pixel = None
    
    def is_active(self) -> bool:
        """
        检查是否有活动的矩形选择
        
        Returns:
            True 如果有活动选择，否则 False
        """
        return self.start_pixel is not None and self.end_pixel is not None
    
    def get_rect(self) -> Optional[tuple[int, int, int, int]]:
        """
        获取矩形范围
        
        Returns:
            (x, y, width, height) 元组，如果没有选择则返回 None
            x, y 是左上角坐标，width, height 是宽度和高度
        """
        if not self.is_active():
            return None
        
        x1, y1 = self.start_pixel
        x2, y2 = self.end_pixel
        
        # 确保 x1 <= x2, y1 <= y2
        x = min(x1, x2)
        y = min(y1, y2)
        # 包含起始和结束像素，所以需要 +1
        width = abs(x2 - x1) + 1
        height = abs(y2 - y1) + 1
        
        # 确保至少 1x1 像素
        width = max(1, width)
        height = max(1, height)
        
        return (x, y, width, height)
    
    def render_overlay(self, painter: 'QPainter', view_transform: 'ViewTransform',
                      border_color: 'QColor', show_handles: bool = True,
                      dash_style: bool = True):
        """
        渲染矩形覆盖层
        
        绘制选区边框和可选的调整手柄。
        
        Args:
            painter: Qt QPainter 对象
            view_transform: ViewTransform 对象用于坐标转换
            border_color: 边框颜色
            show_handles: 是否显示调整手柄
            dash_style: 是否使用虚线样式
        """
        if not self.is_active():
            return
        
        from PySide6.QtCore import Qt, QRectF
        from PySide6.QtGui import QPen, QBrush, QColor
        
        # 转换为视图坐标
        x1_view, y1_view = view_transform.pixel_to_view(*self.start_pixel)
        x2_view, y2_view = view_transform.pixel_to_view(*self.end_pixel)
        
        # 确保 x1 <= x2, y1 <= y2
        x_min = min(x1_view, x2_view)
        y_min = min(y1_view, y2_view)
        x_max = max(x1_view, x2_view)
        y_max = max(y1_view, y2_view)
        
        width = x_max - x_min
        height = y_max - y_min
        
        # 保存当前状态
        old_pen = painter.pen()
        old_brush = painter.brush()
        
        # 绘制选区边框
        pen = QPen(border_color, 2)
        pen.setStyle(Qt.DashLine if dash_style else Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(x_min, y_min, width, height))
        
        # 绘制调整手柄（四个角）
        if show_handles:
            handle_size = 8
            handle_color = QColor(255, 255, 255, 200)
            painter.setBrush(QBrush(handle_color))
            painter.setPen(QPen(Qt.black, 1))
            
            # 左上角
            painter.drawRect(int(x_min - handle_size/2), int(y_min - handle_size/2), 
                            handle_size, handle_size)
            # 右上角
            painter.drawRect(int(x_max - handle_size/2), int(y_min - handle_size/2), 
                            handle_size, handle_size)
            # 左下角
            painter.drawRect(int(x_min - handle_size/2), int(y_max - handle_size/2), 
                            handle_size, handle_size)
            # 右下角
            painter.drawRect(int(x_max - handle_size/2), int(y_max - handle_size/2), 
                            handle_size, handle_size)
        
        # 恢复状态
        painter.setPen(old_pen)
        painter.setBrush(old_brush)
