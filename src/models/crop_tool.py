"""
裁剪工具模块

提供矩形区域选择和裁剪功能。
"""

from typing import TYPE_CHECKING

from .rect_selector import RectSelector

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter

    from .view_transform import ViewTransform


class CropTool:
    """
    裁剪工具类

    管理裁剪区域的选择、调整和渲染。
    复用 RectSelector 处理矩形选择逻辑。
    """

    def __init__(self):
        """初始化裁剪工具"""
        self.rect_selector = RectSelector()
        self.is_active: bool = False

    def start_selection(self, pixel_x: int, pixel_y: int):
        """
        开始选择裁剪区域

        Args:
            pixel_x: 起始 X 坐标（像素）
            pixel_y: 起始 Y 坐标（像素）
        """
        self.is_active = True
        self.rect_selector.start(pixel_x, pixel_y)

    def update_selection(self, pixel_x: int, pixel_y: int):
        """
        更新裁剪区域

        Args:
            pixel_x: 当前 X 坐标（像素）
            pixel_y: 当前 Y 坐标（像素）
        """
        self.rect_selector.update(pixel_x, pixel_y)

    def end_selection(self):
        """结束选择（左键释放）"""
        self.rect_selector.end()

    def confirm_crop(self) -> bool:
        """
        确认裁剪（右键点击）

        Returns:
            True 如果有有效的裁剪区域，False 否则
        """
        return self.is_active and self.rect_selector.is_active()

    def cancel_selection(self):
        """取消选择"""
        self.is_active = False
        self.rect_selector.cancel()

    def get_crop_rect(self) -> tuple[int, int, int, int] | None:
        """
        获取裁剪矩形

        Returns:
            (x, y, width, height) 元组，如果没有选择则返回 None
            x, y 是左上角坐标，width, height 是宽度和高度
        """
        if not self.is_active:
            return None
        return self.rect_selector.get_rect()

    @property
    def is_dragging(self) -> bool:
        """获取拖动状态"""
        return self.rect_selector.is_dragging

    def render_cursor(self, painter: 'QPainter', view_x: float, view_y: float):
        """
        渲染裁剪工具的十字光标

        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
        """
        from PySide6.QtGui import QColor

        from ..utils.cursor_renderer import CursorRenderer

        # 红色十字光标
        CursorRenderer.render_crosshair_cursor(
            painter, view_x, view_y,
            color=QColor(255, 0, 0),  # 红色
            size=20
        )

    def render_overlay(self, painter: 'QPainter', view_transform: 'ViewTransform'):
        """
        渲染裁剪选区覆盖层

        绘制半透明覆盖层、选区边框和调整手柄。

        Args:
            painter: Qt QPainter 对象
            view_transform: ViewTransform 对象用于坐标转换
        """
        if not self.is_active:
            return

        from PySide6.QtGui import QColor

        # 使用 RectSelector 渲染，红色边框
        self.rect_selector.render_overlay(
            painter,
            view_transform,
            QColor(255, 0, 0),  # 红色
            show_handles=True,
            dash_style=True
        )
