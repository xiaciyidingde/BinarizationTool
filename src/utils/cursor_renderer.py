"""
光标渲染器模块

提供通用的光标渲染功能，统一管理工具光标的外观。
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter, QColor


class CursorRenderer:
    """
    光标渲染器工具类
    
    提供静态方法渲染各种类型的工具光标。
    """
    
    @staticmethod
    def render_circle_cursor(painter: 'QPainter', 
                            view_x: float, 
                            view_y: float, 
                            view_size: float,
                            ring_color: 'QColor',
                            center_color: Optional['QColor'] = None,
                            show_crosshair: bool = True,
                            crosshair_threshold: float = 30.0):
        """
        渲染圆形光标
        
        绘制圆形外圈显示工具大小，可选的中心指示点和十字准星。
        
        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
            view_size: 圆圈大小（视图坐标）
            ring_color: 外圈颜色
            center_color: 中心点颜色（可选）
            show_crosshair: 是否显示十字准星
            crosshair_threshold: 十字准星显示阈值（当圆圈小于此值时显示）
        """
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QPen, QBrush, QColor
        
        # 保存当前画笔状态
        old_pen = painter.pen()
        old_brush = painter.brush()
        
        radius = view_size / 2.0
        
        # === 第一层：绘制彩色圆形外圈 ===
        pen = QPen(ring_color, 2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(view_x, view_y), radius, radius)
        
        # === 第二层：绘制中心指示点（可选）===
        if center_color is not None:
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
        if show_crosshair and view_size < crosshair_threshold:
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
