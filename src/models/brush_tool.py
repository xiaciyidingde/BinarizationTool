"""
画笔工具模块

处理画笔绘制逻辑，包括笔画开始、继续、结束，以及基于间距的点插值。
遵循 Photoshop 的画笔行为模式。
"""

from typing import Optional, TYPE_CHECKING
from .brush_stroke import BrushStroke

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter


class BrushTool:
    """
    画笔工具类
    
    管理画笔参数和绘制状态，提供笔画控制方法。
    支持基于间距的点插值，确保笔画连续性。
    """
    
    def __init__(self):
        """初始化画笔工具"""
        self.size: float = 10.0  # 像素单位（直径）
        self.color: int = 0  # 0=黑色, 255=白色
        self.hardness: float = 1.0  # 0.0-1.0，100% 硬度 = 完全硬边
        self.opacity: float = 1.0  # 0.0-1.0，虽然二值化图片不需要，但保留接口
        self.spacing: float = 0.25  # 笔刷间距（相对于大小），PS 默认 25%
        
        self.is_drawing: bool = False
        self.current_stroke: Optional[BrushStroke] = None
        self.last_draw_pos: Optional[tuple[int, int]] = None
    
    def start_stroke(self, pixel_x: int, pixel_y: int) -> BrushStroke:
        """
        开始新笔画
        
        立即在起始位置绘制一个笔刷印记（Photoshop 行为）。
        
        Args:
            pixel_x: 起始 X 坐标（像素）
            pixel_y: 起始 Y 坐标（像素）
            
        Returns:
            新创建的 BrushStroke 对象
        """
        self.is_drawing = True
        self.current_stroke = BrushStroke(self.size, self.color, self.hardness)
        self.current_stroke.add_point(pixel_x, pixel_y)
        self.last_draw_pos = (pixel_x, pixel_y)
        return self.current_stroke
    
    def continue_stroke(self, pixel_x: int, pixel_y: int):
        """
        继续笔画
        
        根据间距插值点以保持均匀的笔刷印记分布（Photoshop 行为）。
        
        Args:
            pixel_x: 当前 X 坐标（像素）
            pixel_y: 当前 Y 坐标（像素）
        """
        if not self.is_drawing or self.current_stroke is None:
            return
        
        if self.last_draw_pos is None:
            # 如果没有上一个位置，直接添加点
            self.current_stroke.add_point(pixel_x, pixel_y)
            self.last_draw_pos = (pixel_x, pixel_y)
            return
        
        # 计算距离
        distance = self._calculate_distance(self.last_draw_pos, (pixel_x, pixel_y))
        step_distance = self.size * self.spacing
        
        if distance >= step_distance:
            # 在路径上插值点以保持均匀间距
            num_steps = int(distance / step_distance)
            
            for i in range(1, num_steps + 1):
                t = (i * step_distance) / distance
                interp_x = int(self.last_draw_pos[0] + t * (pixel_x - self.last_draw_pos[0]))
                interp_y = int(self.last_draw_pos[1] + t * (pixel_y - self.last_draw_pos[1]))
                self.current_stroke.add_point(interp_x, interp_y)
            
            # 更新最后绘制位置为最后一个插值点
            # 这样可以保持精确的间距
            if num_steps > 0:
                t = (num_steps * step_distance) / distance
                self.last_draw_pos = (
                    int(self.last_draw_pos[0] + t * (pixel_x - self.last_draw_pos[0])),
                    int(self.last_draw_pos[1] + t * (pixel_y - self.last_draw_pos[1]))
                )
    
    def end_stroke(self) -> Optional[BrushStroke]:
        """
        结束笔画
        
        Returns:
            完成的 BrushStroke 对象，如果没有正在进行的笔画则返回 None
        """
        if not self.is_drawing:
            return None
        
        self.is_drawing = False
        stroke = self.current_stroke
        self.current_stroke = None
        self.last_draw_pos = None
        return stroke
    
    def render_cursor(self, painter: 'QPainter', view_x: float, view_y: float, 
                     view_size: float):
        """
        渲染画笔光标
        
        绘制圆形外圈显示画笔大小，加上十字准星（Photoshop 风格）。
        
        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
            view_size: 画笔大小（视图坐标）
        """
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QPen
        
        # 保存当前画笔状态
        old_pen = painter.pen()
        
        # 设置画笔光标样式
        pen = QPen(Qt.white, 1)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        
        # 绘制圆形外圈
        radius = view_size / 2.0
        painter.drawEllipse(QPointF(view_x, view_y), radius, radius)
        
        # 绘制黑色外圈（增强可见性）
        pen.setColor(Qt.black)
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(view_x, view_y), radius, radius)
        
        # 绘制十字准星
        pen.setColor(Qt.white)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        
        crosshair_size = 5
        # 水平线
        painter.drawLine(
            int(view_x - crosshair_size), int(view_y),
            int(view_x + crosshair_size), int(view_y)
        )
        # 垂直线
        painter.drawLine(
            int(view_x), int(view_y - crosshair_size),
            int(view_x), int(view_y + crosshair_size)
        )
        
        # 恢复画笔状态
        painter.setPen(old_pen)
    
    def _calculate_distance(self, p1: tuple[int, int], p2: tuple[int, int]) -> float:
        """
        计算两点之间的欧几里得距离
        
        Args:
            p1: 第一个点 (x, y)
            p2: 第二个点 (x, y)
            
        Returns:
            距离值
        """
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return (dx * dx + dy * dy) ** 0.5
