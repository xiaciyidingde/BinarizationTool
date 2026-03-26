"""
画笔笔画模块

表示一次完整的画笔绘制操作，包含笔画路径和渲染逻辑。
遵循 Photoshop 的画笔行为模式。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .image_data import ImageData


class BrushStroke:
    """
    画笔笔画类

    存储一次完整笔画的所有点，并提供光栅化方法将笔画渲染到图片上。
    使用圆形笔刷印记，支持硬度控制的边缘衰减。
    """

    def __init__(self, size: float, color: int, hardness: float):
        """
        初始化画笔笔画

        Args:
            size: 笔刷直径（像素单位）
            color: 颜色值（0=黑色, 255=白色）
            hardness: 硬度（0.0=完全柔和, 1.0=完全硬边）
        """
        self.size = size
        self.color = color
        self.hardness = max(0.0, min(1.0, hardness))  # 限制在 [0, 1]
        self.points: list[tuple[int, int]] = []

    def add_point(self, x: int, y: int):
        """
        添加笔画点

        Args:
            x: X 坐标（像素）
            y: Y 坐标（像素）
        """
        self.points.append((x, y))

    def rasterize(self, image_data: 'ImageData', start_index: int = 0) -> tuple[int, int, int, int]:
        """
        将笔画光栅化到图片数据

        遍历笔画点，在每个点绘制一个圆形笔刷印记。
        支持增量光栅化以提高性能。

        Args:
            image_data: 目标 ImageData 对象
            start_index: 开始光栅化的点索引（默认0，光栅化所有点）

        Returns:
            脏区域 (x_min, y_min, x_max, y_max)，如果没有点则返回 (0, 0, 0, 0)
        """
        if start_index >= len(self.points):
            return (0, 0, 0, 0)

        radius = self.size / 2.0

        # 计算受影响的区域
        x_min = image_data.width
        y_min = image_data.height
        x_max = 0
        y_max = 0

        for i in range(start_index, len(self.points)):
            x, y = self.points[i]
            self._draw_brush_dab(image_data, x, y)

            # 更新脏区域
            x_min = min(x_min, int(x - radius))
            y_min = min(y_min, int(y - radius))
            x_max = max(x_max, int(x + radius) + 1)
            y_max = max(y_max, int(y + radius) + 1)

        # 限制在图片范围内
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(image_data.width, x_max)
        y_max = min(image_data.height, y_max)

        return (x_min, y_min, x_max, y_max)

    def _draw_brush_dab(self, image_data: 'ImageData', center_x: int, center_y: int):
        """
        绘制单个笔刷印记（圆形）- 使用 NumPy 向量化优化

        硬度控制边缘衰减：
        - hardness = 1.0: 完全硬边（半径内全是目标颜色）
        - hardness < 1.0: 柔和边缘（使用径向渐变）

        Args:
            image_data: 目标 ImageData 对象
            center_x: 笔刷中心 X 坐标
            center_y: 笔刷中心 Y 坐标
        """
        import numpy as np

        radius = self.size / 2.0
        inner_radius = radius * self.hardness  # 硬边缘半径

        # 计算笔刷边界框
        x_min = max(0, int(center_x - radius))
        x_max = min(image_data.width - 1, int(center_x + radius))
        y_min = max(0, int(center_y - radius))
        y_max = min(image_data.height - 1, int(center_y + radius))

        # 如果边界框无效，直接返回
        if x_min > x_max or y_min > y_max:
            return

        # 使用 NumPy 网格一次性计算所有像素的距离
        x_max - x_min + 1
        y_max - y_min + 1

        # 创建坐标网格
        y_coords = np.arange(y_min, y_max + 1)
        x_coords = np.arange(x_min, x_max + 1)
        x_grid, y_grid = np.meshgrid(x_coords, y_coords)

        # 计算到中心的距离（向量化）
        dx = x_grid - center_x
        dy = y_grid - center_y
        dist = np.sqrt(dx * dx + dy * dy)

        # 创建掩码
        if self.hardness >= 0.99:
            # 完全硬边：简单的圆形掩码
            mask = dist <= radius
        else:
            # 柔和边缘：使用 alpha 混合
            mask = dist <= radius
            alpha = np.ones_like(dist)

            # 柔和区域的 alpha 值
            soft_region = (dist > inner_radius) & (dist <= radius)
            alpha[soft_region] = 1.0 - (dist[soft_region] - inner_radius) / (radius - inner_radius)

            # 对于二值化图片，使用阈值
            mask = mask & (alpha > 0.5)

        # 批量设置像素
        if image_data.temp_layer is not None:
            image_data.temp_layer[y_min:y_max+1, x_min:x_max+1][mask] = self.color
            # 同时标记这些像素为已编辑
            if image_data.temp_edit_mask is not None:
                image_data.temp_edit_mask[y_min:y_max+1, x_min:x_max+1][mask] = True
        elif image_data.edit_mask is not None:
            # 如果有编辑掩码，标记这些像素
            image_data.edit_mask[y_min:y_max+1, x_min:x_max+1][mask] = True
            image_data.edit_values[y_min:y_max+1, x_min:x_max+1][mask] = self.color
        else:
            # 直接修改基础层
            image_data.pixels[y_min:y_max+1, x_min:x_max+1][mask] = self.color
