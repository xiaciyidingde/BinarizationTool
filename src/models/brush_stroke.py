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
    
    def rasterize(self, image_data: 'ImageData'):
        """
        将笔画光栅化到图片数据
        
        遍历所有笔画点，在每个点绘制一个圆形笔刷印记。
        
        Args:
            image_data: 目标 ImageData 对象
        """
        for x, y in self.points:
            self._draw_brush_dab(image_data, x, y)
    
    def _draw_brush_dab(self, image_data: 'ImageData', center_x: int, center_y: int):
        """
        绘制单个笔刷印记（圆形）
        
        硬度控制边缘衰减：
        - hardness = 1.0: 完全硬边（半径内全是目标颜色）
        - hardness < 1.0: 柔和边缘（使用径向渐变）
        
        算法：
        1. 计算笔刷半径
        2. 计算硬边缘半径 = 半径 * 硬度
        3. 遍历笔刷边界框内的所有像素
        4. 对于每个像素：
           - 如果距离 <= 硬边缘半径：完全不透明（设为目标颜色）
           - 如果硬边缘半径 < 距离 <= 半径：线性衰减
           - 如果距离 > 半径：不绘制
        
        Args:
            image_data: 目标 ImageData 对象
            center_x: 笔刷中心 X 坐标
            center_y: 笔刷中心 Y 坐标
        """
        radius = self.size / 2.0
        inner_radius = radius * self.hardness  # 硬边缘半径
        
        # 计算笔刷边界框
        x_min = int(center_x - radius)
        x_max = int(center_x + radius) + 1
        y_min = int(center_y - radius)
        y_max = int(center_y + radius) + 1
        
        # 遍历边界框内的所有像素
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                # 检查坐标是否有效
                if not image_data.is_valid_coord(x, y):
                    continue
                
                # 计算到中心的距离
                dx = x - center_x
                dy = y - center_y
                dist = (dx * dx + dy * dy) ** 0.5
                
                if dist <= inner_radius:
                    # 硬边缘区域：完全不透明
                    image_data.set_pixel(x, y, self.color)
                elif dist <= radius:
                    # 柔和边缘区域：线性衰减
                    # alpha = 1.0 在 inner_radius，0.0 在 radius
                    alpha = 1.0 - (dist - inner_radius) / (radius - inner_radius)
                    
                    # 对于二值化图片，使用阈值决定是否绘制
                    # 阈值可以调整以获得更好的视觉效果
                    if alpha > 0.5:
                        image_data.set_pixel(x, y, self.color)
                    # 如果需要更平滑的边缘，可以使用混合：
                    # current_value = image_data.get_pixel(x, y)
                    # new_value = int(current_value * (1 - alpha) + self.color * alpha)
                    # image_data.set_pixel(x, y, new_value)
