"""
测量工具模块

用于测量图像中两点之间的距离和角度
"""

import math


class MeasureTool:
    """
    测量工具类
    
    用于测量图像中两点之间的距离、角度等信息
    """
    
    def __init__(self):
        """初始化测量工具"""
        self.is_measuring: bool = False
        self.start_point: tuple[int, int] | None = None
        self.end_point: tuple[int, int] | None = None
        self.dragging_point: str | None = None  # 'start', 'end', 或 None
        self.hover_point: str | None = None  # 鼠标悬停的端点
    
    def start_measure(self, pixel_x: int, pixel_y: int):
        """
        开始测量
        
        Args:
            pixel_x: 起始点 X 坐标（图像坐标）
            pixel_y: 起始点 Y 坐标（图像坐标）
        """
        self.is_measuring = True
        self.start_point = (pixel_x, pixel_y)
        self.end_point = (pixel_x, pixel_y)
        self.dragging_point = None
    
    def update_measure(self, pixel_x: int, pixel_y: int):
        """
        更新测量终点
        
        Args:
            pixel_x: 当前点 X 坐标（图像坐标）
            pixel_y: 当前点 Y 坐标（图像坐标）
        """
        if self.is_measuring:
            self.end_point = (pixel_x, pixel_y)
    
    def end_measure(self):
        """结束测量"""
        self.is_measuring = False
        self.dragging_point = None
    
    def check_point_hover(self, pixel_x: int, pixel_y: int, threshold: float = 10.0) -> str | None:
        """
        检查鼠标是否悬停在端点附近
        
        Args:
            pixel_x: 鼠标 X 坐标（图像坐标）
            pixel_y: 鼠标 Y 坐标（图像坐标）
            threshold: 检测阈值（像素）
            
        Returns:
            'start', 'end', 或 None
        """
        if self.start_point is None or self.end_point is None:
            return None
        
        # 检查起点
        dx = pixel_x - self.start_point[0]
        dy = pixel_y - self.start_point[1]
        if math.sqrt(dx * dx + dy * dy) <= threshold:
            return 'start'
        
        # 检查终点
        dx = pixel_x - self.end_point[0]
        dy = pixel_y - self.end_point[1]
        if math.sqrt(dx * dx + dy * dy) <= threshold:
            return 'end'
        
        return None
    
    def start_drag_point(self, point_type: str):
        """
        开始拖动端点
        
        Args:
            point_type: 'start' 或 'end'
        """
        self.dragging_point = point_type
    
    def drag_point(self, pixel_x: int, pixel_y: int):
        """
        拖动端点
        
        Args:
            pixel_x: 新位置 X 坐标（图像坐标）
            pixel_y: 新位置 Y 坐标（图像坐标）
        """
        if self.dragging_point == 'start':
            self.start_point = (pixel_x, pixel_y)
        elif self.dragging_point == 'end':
            self.end_point = (pixel_x, pixel_y)
    
    def end_drag_point(self):
        """结束拖动端点"""
        self.dragging_point = None
    
    def get_distance(self) -> float:
        """
        获取测量距离（像素单位）
        
        Returns:
            两点之间的欧几里得距离
        """
        if self.start_point is None or self.end_point is None:
            return 0.0
        
        dx = self.end_point[0] - self.start_point[0]
        dy = self.end_point[1] - self.start_point[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def get_angle(self) -> float:
        """
        获取测量角度（度数）
        
        Returns:
            相对于水平线的角度，范围 [-180, 180]
            0° = 水平向右，90° = 垂直向下，-90° = 垂直向上
        """
        if self.start_point is None or self.end_point is None:
            return 0.0
        
        dx = self.end_point[0] - self.start_point[0]
        dy = self.end_point[1] - self.start_point[1]
        
        if dx == 0 and dy == 0:
            return 0.0
        
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        return angle_deg
    
    def get_delta(self) -> tuple[int, int]:
        """
        获取 X 和 Y 方向的差值
        
        Returns:
            (delta_x, delta_y) 坐标差值
        """
        if self.start_point is None or self.end_point is None:
            return (0, 0)
        
        dx = self.end_point[0] - self.start_point[0]
        dy = self.end_point[1] - self.start_point[1]
        return (dx, dy)
    
    def clear(self):
        """清除测量数据"""
        self.is_measuring = False
        self.start_point = None
        self.end_point = None
        self.dragging_point = None
        self.hover_point = None
