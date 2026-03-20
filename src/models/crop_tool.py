"""
裁剪工具模块

提供矩形区域选择和裁剪功能。
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter
    from .view_transform import ViewTransform


class CropTool:
    """
    裁剪工具类
    
    管理裁剪区域的选择、调整和渲染。
    """
    
    def __init__(self):
        """初始化裁剪工具"""
        self.is_active: bool = False
        self.start_pixel: Optional[tuple[int, int]] = None
        self.end_pixel: Optional[tuple[int, int]] = None
        self.is_dragging: bool = False
    
    def start_selection(self, pixel_x: int, pixel_y: int):
        """
        开始选择裁剪区域
        
        Args:
            pixel_x: 起始 X 坐标（像素）
            pixel_y: 起始 Y 坐标（像素）
        """
        self.is_active = True
        self.is_dragging = True
        self.start_pixel = (pixel_x, pixel_y)
        self.end_pixel = (pixel_x, pixel_y)
    
    def update_selection(self, pixel_x: int, pixel_y: int):
        """
        更新裁剪区域
        
        Args:
            pixel_x: 当前 X 坐标（像素）
            pixel_y: 当前 Y 坐标（像素）
        """
        if self.is_dragging and self.start_pixel is not None:
            self.end_pixel = (pixel_x, pixel_y)
    
    def end_selection(self):
        """结束选择（左键释放）"""
        self.is_dragging = False
    
    def confirm_crop(self) -> bool:
        """
        确认裁剪（右键点击）
        
        Returns:
            True 如果有有效的裁剪区域，False 否则
        """
        if self.is_active and self.start_pixel is not None and self.end_pixel is not None:
            return True
        return False
    
    def cancel_selection(self):
        """取消选择"""
        self.is_active = False
        self.is_dragging = False
        self.start_pixel = None
        self.end_pixel = None
    
    def get_crop_rect(self) -> Optional[tuple[int, int, int, int]]:
        """
        获取裁剪矩形
        
        Returns:
            (x, y, width, height) 元组，如果没有选择则返回 None
            x, y 是左上角坐标，width, height 是宽度和高度
        """
        if not self.is_active or self.start_pixel is None or self.end_pixel is None:
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
    
    def render_overlay(self, painter: 'QPainter', view_transform: 'ViewTransform'):
        """
        渲染裁剪选区覆盖层
        
        绘制半透明覆盖层、选区边框和调整手柄。
        
        Args:
            painter: Qt QPainter 对象
            view_transform: ViewTransform 对象用于坐标转换
        """
        if not self.is_active or self.start_pixel is None or self.end_pixel is None:
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
        pen = QPen(Qt.white, 2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(x_min, y_min, width, height))
        
        # 绘制黑色边框（增强可见性）
        pen.setColor(Qt.black)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(QRectF(x_min - 1, y_min - 1, width + 2, height + 2))
        
        # 绘制调整手柄（四个角）
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
