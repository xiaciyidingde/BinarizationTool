"""
笔画插值器模块

提供笔画插值相关的工具函数，用于涂抹类操作。
"""


class StrokeInterpolator:
    """
    笔画插值器工具类
    
    提供静态方法处理涂抹操作中的插值逻辑，
    确保拖动时笔画连续、无断点。
    """
    
    @staticmethod
    def calculate_distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
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
    
    @staticmethod
    def interpolate_points(start: tuple[int, int], 
                          end: tuple[int, int],
                          size: float,
                          spacing: float) -> list[tuple[int, int]]:
        """
        在两点之间插值生成中间点
        
        根据笔刷/选择范围大小和间距因子，在起始点和结束点之间
        插值生成均匀分布的中间点，确保涂抹操作连续无断点。
        
        Args:
            start: 起始点 (x, y)
            end: 结束点 (x, y)
            size: 笔刷/选择范围大小（像素）
            spacing: 间距因子（相对于大小，例如 0.25 表示 25% 间距）
            
        Returns:
            插值点列表（不包含起始点，包含所有中间点）
            如果距离为 0 或不需要插值，返回空列表
        """
        dist = StrokeInterpolator.calculate_distance(start, end)
        
        if dist == 0:
            return []
        
        # 计算间距阈值
        spacing_threshold = size * spacing
        
        # 计算需要插入多少个中间点
        num_steps = max(1, int(dist / spacing_threshold))
        
        points = []
        for i in range(1, num_steps + 1):
            t = i / num_steps
            interp_x = int(start[0] + (end[0] - start[0]) * t)
            interp_y = int(start[1] + (end[1] - start[1]) * t)
            points.append((interp_x, interp_y))
        
        return points
    
    @staticmethod
    def calculate_last_interpolated_position(start: tuple[int, int],
                                            end: tuple[int, int],
                                            size: float,
                                            spacing: float) -> tuple[int, int]:
        """
        计算最后一个插值点的位置（用于精确间距控制）
        
        在某些情况下（如画笔工具），需要将"最后位置"更新为
        最后一个实际插值点，而不是鼠标当前位置，以保持精确的间距。
        
        Args:
            start: 起始点 (x, y)
            end: 结束点 (x, y)
            size: 笔刷/选择范围大小（像素）
            spacing: 间距因子（相对于大小）
            
        Returns:
            最后一个插值点的位置 (x, y)
            如果没有插值点，返回起始点
        """
        dist = StrokeInterpolator.calculate_distance(start, end)
        
        if dist == 0:
            return start
        
        spacing_threshold = size * spacing
        num_steps = int(dist / spacing_threshold)
        
        if num_steps == 0:
            return start
        
        # 计算最后一个插值点的位置
        t = (num_steps * spacing_threshold) / dist
        last_x = int(start[0] + t * (end[0] - start[0]))
        last_y = int(start[1] + t * (end[1] - start[1]))
        
        return (last_x, last_y)
