"""
视图变换模块

处理像素坐标系统和视图坐标系统之间的转换，支持缩放和平移操作。
"""


class ViewTransform:
    """
    视图变换类，管理缩放和平移操作

    维护两个坐标系统：
    - 像素坐标系统：图片原始分辨率的坐标系统
    - 视图坐标系统：Canvas 显示区域的坐标系统
    """

    def __init__(self, scale: float = 1.0, offset_x: float = 0.0, offset_y: float = 0.0):
        """
        初始化视图变换

        Args:
            scale: 缩放因子，默认 1.0
            offset_x: X 轴偏移，默认 0.0
            offset_y: Y 轴偏移，默认 0.0
        """
        self.scale = scale
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.min_scale = 0.01
        self.max_scale = 32.0

    def pixel_to_view(self, pixel_x: int, pixel_y: int) -> tuple[float, float]:
        """
        将像素坐标转换为视图坐标

        Args:
            pixel_x: 像素 X 坐标
            pixel_y: 像素 Y 坐标

        Returns:
            (view_x, view_y): 视图坐标元组
        """
        view_x = pixel_x * self.scale + self.offset_x
        view_y = pixel_y * self.scale + self.offset_y
        return (view_x, view_y)

    def view_to_pixel(self, view_x: float, view_y: float) -> tuple[int, int]:
        """
        将视图坐标转换为像素坐标

        Args:
            view_x: 视图 X 坐标
            view_y: 视图 Y 坐标

        Returns:
            (pixel_x, pixel_y): 像素坐标元组
        """
        pixel_x = (view_x - self.offset_x) / self.scale
        pixel_y = (view_y - self.offset_y) / self.scale
        return (int(pixel_x), int(pixel_y))

    def zoom_at_point(self, view_x: float, view_y: float, scale_delta: float):
        """
        以指定点为中心进行缩放

        保持该点在缩放前后的像素坐标不变，这样用户感觉是在鼠标位置进行缩放。

        Args:
            view_x: 缩放中心的视图 X 坐标
            view_y: 缩放中心的视图 Y 坐标
            scale_delta: 缩放变化量（乘法因子）
        """
        # 计算缩放前该点对应的像素坐标
        pixel_x, pixel_y = self.view_to_pixel(view_x, view_y)

        # 应用新的缩放因子，限制在范围内
        new_scale = self.scale * scale_delta
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))

        # 计算新的偏移，使得该像素点在新缩放下仍然对应相同的视图坐标
        # view_x = pixel_x * new_scale + new_offset_x
        # new_offset_x = view_x - pixel_x * new_scale
        self.offset_x = view_x - pixel_x * new_scale
        self.offset_y = view_y - pixel_y * new_scale

        self.scale = new_scale

    def set_scale(self, scale: float):
        """
        设置缩放因子（限制在有效范围内）

        Args:
            scale: 新的缩放因子
        """
        self.scale = max(self.min_scale, min(self.max_scale, scale))

    def translate(self, delta_x: float, delta_y: float):
        """
        平移视图

        Args:
            delta_x: X 轴平移量（视图坐标）
            delta_y: Y 轴平移量（视图坐标）
        """
        self.offset_x += delta_x
        self.offset_y += delta_y

    def get_brush_view_size(self, pixel_size: float) -> float:
        """
        将画笔像素大小转换为视图大小

        Args:
            pixel_size: 画笔大小（像素单位）

        Returns:
            画笔大小（视图单位）
        """
        return pixel_size * self.scale
