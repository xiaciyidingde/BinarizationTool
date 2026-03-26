"""
画笔工具模块

处理画笔绘制逻辑，包括笔画开始、继续、结束，以及基于间距的点插值。
遵循 Photoshop 的画笔行为模式。
"""

from typing import TYPE_CHECKING

from ..utils.cursor_renderer import CursorRenderer
from ..utils.stroke_interpolator import StrokeInterpolator
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

        # 十字准星显示阈值（视图大小）
        self.crosshair_threshold: float = 30.0  # 当圆圈小于此值时显示十字

        self.is_drawing: bool = False
        self.current_stroke: BrushStroke | None = None
        self.last_draw_pos: tuple[int, int] | None = None

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

        # 使用 StrokeInterpolator 计算插值点
        interpolated_points = StrokeInterpolator.interpolate_points(
            self.last_draw_pos,
            (pixel_x, pixel_y),
            self.size,
            self.spacing
        )

        # 添加所有插值点
        for point in interpolated_points:
            self.current_stroke.add_point(point[0], point[1])

        # 更新最后绘制位置为最后一个插值点（保持精确间距）
        if len(interpolated_points) > 0:
            self.last_draw_pos = StrokeInterpolator.calculate_last_interpolated_position(
                self.last_draw_pos,
                (pixel_x, pixel_y),
                self.size,
                self.spacing
            )

    def end_stroke(self) -> BrushStroke | None:
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

        绘制圆形外圈显示画笔大小。
        颜色指示：红色=黑色画笔，绿色=白色画笔
        当圆圈太小时在圆圈外显示十字准星。

        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
            view_size: 画笔大小（视图坐标）
        """
        from PySide6.QtGui import QColor

        # 根据画笔颜色选择指示器颜色
        # 黑色画笔(0) -> 红色指示器
        # 白色画笔(255) -> 绿色指示器
        if self.color == 0:
            ring_color = QColor(255, 0, 0)  # 红色
        else:
            ring_color = QColor(0, 255, 0)  # 绿色

        # 使用 CursorRenderer 渲染
        CursorRenderer.render_circle_cursor(
            painter,
            view_x,
            view_y,
            view_size,
            ring_color,
            center_color=None,  # 画笔工具不显示中心点
            show_crosshair=True,
            crosshair_threshold=self.crosshair_threshold
        )
