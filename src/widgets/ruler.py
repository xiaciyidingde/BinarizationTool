"""
标尺组件

显示图像坐标刻度，帮助用户定位和测量
"""

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QWidget

from ..utils.coordinate_transform import CoordinateTransform


class Ruler(QWidget):
    """
    标尺组件
    
    显示图像坐标刻度，支持水平和垂直方向
    """
    
    HORIZONTAL = 0
    VERTICAL = 1
    
    def __init__(self, orientation: int, parent=None):
        """
        初始化标尺
        
        Args:
            orientation: 方向（HORIZONTAL 或 VERTICAL）
            parent: 父组件
        """
        super().__init__(parent)
        
        self.orientation = orientation
        self.coord_transform: CoordinateTransform = None
        
        # 标尺尺寸
        self.ruler_size = 20  # 标尺宽度/高度（从 25 减小到 20）
        
        # 颜色
        self.bg_color = QColor(240, 240, 240)
        self.line_color = QColor(100, 100, 100)
        self.text_color = QColor(60, 60, 60)
        
        # 字体
        self.font = QFont("Arial", 7)  # 字体大小从 8 减小到 7
        
        # 设置固定尺寸
        if self.orientation == self.HORIZONTAL:
            self.setFixedHeight(self.ruler_size)
        else:
            self.setFixedWidth(self.ruler_size)
            
        # 鼠标追踪（用于显示当前位置指示器）
        self.setMouseTracking(True)
        self.mouse_pos = None
        
    def set_coordinate_transform(self, coord_transform: CoordinateTransform):
        """
        设置坐标转换器
        
        Args:
            coord_transform: 坐标转换器实例
        """
        self.coord_transform = coord_transform
        self.update()
        
    def paintEvent(self, event):
        """绘制标尺"""
        if not self.coord_transform:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        # 绘制背景
        painter.fillRect(self.rect(), self.bg_color)
        
        # 设置字体
        painter.setFont(self.font)
        
        if self.orientation == self.HORIZONTAL:
            self._draw_horizontal_ruler(painter)
        else:
            self._draw_vertical_ruler(painter)
            
        # 绘制鼠标位置指示器
        if self.mouse_pos is not None:
            self._draw_mouse_indicator(painter)
            
    def _draw_horizontal_ruler(self, painter: QPainter):
        """绘制水平标尺"""
        width = self.width()
        height = self.height()
        
        # 计算刻度间隔
        interval = self._calculate_interval()
        
        # 获取可见范围的图像坐标
        start_img_x, _ = self.coord_transform.screen_to_image(0, 0)
        end_img_x, _ = self.coord_transform.screen_to_image(width, 0)
        
        # 起始刻度（向下取整到间隔的倍数）
        start_tick = int(start_img_x / interval) * interval
        
        # 绘制刻度
        painter.setPen(QPen(self.line_color, 1))
        
        tick = start_tick
        while tick <= end_img_x:
            # 转换到屏幕坐标
            screen_x, _ = self.coord_transform.image_to_screen(tick, 0)
            
            if 0 <= screen_x <= width:
                # 主刻度线（每个间隔）
                painter.drawLine(int(screen_x), height - 6, int(screen_x), height)  # 刻度线从 8 减小到 6
                
                # 绘制刻度值
                painter.setPen(self.text_color)
                text = str(int(tick))
                text_rect = painter.fontMetrics().boundingRect(text)
                text_x = int(screen_x - text_rect.width() / 2)
                text_y = height - 8  # 文字位置从 10 调整到 8
                painter.drawText(text_x, text_y, text)
                painter.setPen(QPen(self.line_color, 1))
                
                # 绘制次刻度线（间隔的一半）
                if interval >= 20:  # 只在间隔足够大时显示次刻度
                    sub_tick = tick + interval / 2
                    if sub_tick <= end_img_x:
                        sub_screen_x, _ = self.coord_transform.image_to_screen(sub_tick, 0)
                        if 0 <= sub_screen_x <= width:
                            painter.drawLine(int(sub_screen_x), height - 4, int(sub_screen_x), height)  # 次刻度从 5 减小到 4
            
            tick += interval
            
    def _draw_vertical_ruler(self, painter: QPainter):
        """绘制垂直标尺"""
        width = self.width()
        height = self.height()
        
        # 计算刻度间隔
        interval = self._calculate_interval()
        
        # 获取可见范围的图像坐标
        _, start_img_y = self.coord_transform.screen_to_image(0, 0)
        _, end_img_y = self.coord_transform.screen_to_image(0, height)
        
        # 起始刻度（向下取整到间隔的倍数）
        start_tick = int(start_img_y / interval) * interval
        
        # 绘制刻度
        painter.setPen(QPen(self.line_color, 1))
        
        tick = start_tick
        while tick <= end_img_y:
            # 转换到屏幕坐标
            _, screen_y = self.coord_transform.image_to_screen(0, tick)
            
            if 0 <= screen_y <= height:
                # 主刻度线（每个间隔）
                painter.drawLine(width - 6, int(screen_y), width, int(screen_y))  # 刻度线从 8 减小到 6
                
                # 绘制刻度值（旋转90度）
                painter.save()
                painter.setPen(self.text_color)
                text = str(int(tick))
                text_rect = painter.fontMetrics().boundingRect(text)
                
                # 旋转并绘制文本
                painter.translate(width - 8, int(screen_y))  # 位置从 10 调整到 8
                painter.rotate(-90)
                painter.drawText(-text_rect.width() / 2, 0, text)
                painter.restore()
                
                painter.setPen(QPen(self.line_color, 1))
                
                # 绘制次刻度线（间隔的一半）
                if interval >= 20:  # 只在间隔足够大时显示次刻度
                    sub_tick = tick + interval / 2
                    if sub_tick <= end_img_y:
                        _, sub_screen_y = self.coord_transform.image_to_screen(0, sub_tick)
                        if 0 <= sub_screen_y <= height:
                            painter.drawLine(width - 4, int(sub_screen_y), width, int(sub_screen_y))  # 次刻度从 5 减小到 4
            
            tick += interval
            
    def _calculate_interval(self) -> int:
        """
        根据缩放级别计算合适的刻度间隔
        
        Returns:
            刻度间隔（图像像素）
        """
        scale = self.coord_transform.scale
        
        # 目标：屏幕上每 50-100 像素显示一个主刻度
        target_screen_pixels = 75
        
        # 计算对应的图像像素数
        image_pixels = target_screen_pixels / scale
        
        # 选择合适的间隔（10, 20, 50, 100, 200, 500, 1000, ...）
        intervals = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        
        for interval in intervals:
            if interval >= image_pixels:
                return interval
                
        return intervals[-1]
        
    def _draw_mouse_indicator(self, painter: QPainter):
        """绘制鼠标位置指示器"""
        if not self.mouse_pos:
            return
            
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        
        if self.orientation == self.HORIZONTAL:
            x = self.mouse_pos
            painter.drawLine(x, 0, x, self.height())
        else:
            y = self.mouse_pos
            painter.drawLine(0, y, self.width(), y)
            
    def update_mouse_position(self, pos: int):
        """
        更新鼠标位置指示器
        
        Args:
            pos: 鼠标位置（水平标尺为 x，垂直标尺为 y）
        """
        self.mouse_pos = pos
        self.update()
        
    def clear_mouse_position(self):
        """清除鼠标位置指示器"""
        self.mouse_pos = None
        self.update()


class RulerCorner(QWidget):
    """
    标尺角落组件
    
    显示在水平和垂直标尺的交叉处
    """
    
    def __init__(self, parent=None):
        """
        初始化角落组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        self.ruler_size = 20  # 从 25 减小到 20
        self.setFixedSize(self.ruler_size, self.ruler_size)
        
        # 颜色
        self.bg_color = QColor(220, 220, 220)
        
    def paintEvent(self, event):
        """绘制角落"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.bg_color)
