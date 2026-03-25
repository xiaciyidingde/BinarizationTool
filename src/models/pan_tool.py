"""
抓取工具模块

处理画布平移逻辑
"""

from typing import Optional


class PanTool:
    """
    抓取工具类
    
    用于拖动画布进行平移操作
    """
    
    def __init__(self):
        """初始化抓取工具"""
        self.is_panning: bool = False
        self.last_pos: Optional[tuple[int, int]] = None
    
    def start_pan(self, x: int, y: int):
        """
        开始平移
        
        Args:
            x: 起始 X 坐标
            y: 起始 Y 坐标
        """
        self.is_panning = True
        self.last_pos = (x, y)
    
    def continue_pan(self, x: int, y: int) -> tuple[int, int]:
        """
        继续平移
        
        Args:
            x: 当前 X 坐标
            y: 当前 Y 坐标
            
        Returns:
            (delta_x, delta_y) 平移增量
        """
        if not self.is_panning or self.last_pos is None:
            return (0, 0)
        
        delta_x = x - self.last_pos[0]
        delta_y = y - self.last_pos[1]
        self.last_pos = (x, y)
        
        return (delta_x, delta_y)
    
    def end_pan(self):
        """结束平移"""
        self.is_panning = False
        self.last_pos = None
