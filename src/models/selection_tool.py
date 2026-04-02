"""
智能选择工具模块

提供类似 Photoshop 的智能选择功能：
- 选择工具（Selection Tool）：点击选择连续的同色区域
- 快速选择工具（Quick Selection）：画刷式智能选择
- 颜色范围选择：全局选择特定颜色
"""

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter

    from .image_data import ImageData

from ..utils.cursor_renderer import CursorRenderer
from ..utils.stroke_interpolator import StrokeInterpolator
from .rect_selector import RectSelector


class SelectionStroke:
    """
    选择笔画类

    类似 BrushStroke，但用于选择操作。
    在笔刷范围内只选择匹配目标颜色的像素。
    """

    def __init__(self, size: float, selection_mode: str, cached_pixels: np.ndarray | None = None):
        """
        初始化选择笔画

        Args:
            size: 笔刷直径（像素单位）
            selection_mode: 选择模式（'add'=添加, 'subtract'=减去）
            cached_pixels: 缓存的像素数据（避免重复合成）
        """
        self.size = size
        self.selection_mode = selection_mode
        self.points: list[tuple[int, int]] = []
        self.cached_pixels = cached_pixels  # 缓存像素数据，避免重复调用 get_current_pixels()

    def add_point(self, x: int, y: int):
        """添加笔画点"""
        self.points.append((x, y))

    def rasterize(self, image_data: 'ImageData', selection_mask: np.ndarray,
                  start_index: int = 0, tolerance: float = 0.71) -> tuple[int, int, int, int]:
        """
        将选择笔画光栅化到选区蒙版

        在笔刷范围内选择匹配目标颜色的像素。

        Args:
            image_data: 图片数据
            selection_mask: 选区蒙版（输出）
            start_index: 开始光栅化的点索引
            tolerance: 像素边缘容差

        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        if start_index >= len(self.points):
            return (0, 0, 0, 0)

        radius = self.size / 2.0
        # 使用缓存的像素数据，避免重复合成（性能优化）
        pixels = self.cached_pixels if self.cached_pixels is not None else image_data.get_current_pixels()

        # 计算受影响的区域
        x_min = image_data.width
        y_min = image_data.height
        x_max = 0
        y_max = 0

        for i in range(start_index, len(self.points)):
            x, y = self.points[i]
            self._select_in_circle(pixels, selection_mask, x, y, radius, tolerance)

            # 更新脏区域
            x_min = min(x_min, int(x - radius - 1))
            y_min = min(y_min, int(y - radius - 1))
            x_max = max(x_max, int(x + radius + 2))
            y_max = max(y_max, int(y + radius + 2))

        # 限制在图片范围内
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(image_data.width, x_max)
        y_max = min(image_data.height, y_max)

        return (x_min, y_min, x_max, y_max)

    def _select_in_circle(self, pixels: np.ndarray, selection_mask: np.ndarray,
                         center_x: int, center_y: int, radius: float, tolerance: float):
        """
        在圆形范围内选择匹配目标颜色的像素（NumPy 向量化）

        Args:
            pixels: 像素数据
            selection_mask: 选区蒙版（输出）
            center_x: 圆心 X 坐标
            center_y: 圆心 Y 坐标
            radius: 半径
            tolerance: 边缘容差
        """
        height, width = pixels.shape

        # 计算边界框（扩大1像素以包含边缘）
        x_min = max(0, int(center_x - radius - 1))
        x_max = min(width - 1, int(center_x + radius + 1))
        y_min = max(0, int(center_y - radius - 1))
        y_max = min(height - 1, int(center_y + radius + 1))

        if x_min > x_max or y_min > y_max:
            return

        # 创建坐标网格
        y_coords = np.arange(y_min, y_max + 1)
        x_coords = np.arange(x_min, x_max + 1)
        x_grid, y_grid = np.meshgrid(x_coords, y_coords)

        # 计算到中心的距离（向量化）
        dx = x_grid - center_x
        dy = y_grid - center_y
        dist = np.sqrt(dx * dx + dy * dy)

        # 圆形掩码（带容差）
        circle_mask = dist <= (radius + tolerance)

        # 最终掩码：圆内所有像素（不再限制颜色）
        final_mask = circle_mask

        # 根据模式更新选区
        if self.selection_mode == 'add':
            selection_mask[y_min:y_max+1, x_min:x_max+1][final_mask] = True
        elif self.selection_mode == 'subtract':
            selection_mask[y_min:y_max+1, x_min:x_max+1][final_mask] = False


class SelectionTool:
    """
    智能选择工具类

    管理选区蒙版和提供多种选择算法。
    复用画笔工具的绘制逻辑，但只选择匹配颜色的像素。
    """

    # 选择模式
    MODE_NEW = 'new'        # 新建选区
    MODE_ADD = 'add'        # 添加到选区
    MODE_SUBTRACT = 'subtract'  # 从选区减去
    MODE_INTERSECT = 'intersect'  # 与选区相交

    def __init__(self):
        """初始化选择工具"""
        self.selection_mask: np.ndarray | None = None  # 选区蒙版 (H, W), dtype=bool
        self.mode: str = self.MODE_NEW
        self.tolerance: int = 0  # 容差（0-255），对二值化图片通常为0
        self.contiguous: bool = True  # 是否只选择连续区域

        # 选择工具参数
        self.size: float = 50.0  # 选择范围大小（像素）
        self.selection_mode: str = 'add'  # 'add'=添加到选区, 'subtract'=从选区减去

        # 光标显示
        self.crosshair_threshold: float = 30.0  # 当圆圈小于此值时显示十字

        # 拖动选择状态（复用画笔逻辑）
        self.is_dragging: bool = False
        self.current_stroke: SelectionStroke | None = None
        self.spacing: float = 0.1  # 间距因子（相对于笔刷大小）- 降低以获得更平滑的曲线
        self.last_point: tuple[int, int] | None = None

        # 矩形框选模式（使用 RectSelector）
        self.rect_select_mode: bool = False  # 是否启用矩形框选模式
        self.rect_selector = RectSelector()

    def has_selection(self) -> bool:
        """
        检查是否有活动选区

        Returns:
            True 如果有选区，否则 False
        """
        return self.selection_mask is not None and self.selection_mask.any()

    def clear_selection(self):
        """清除选区"""
        self.selection_mask = None

    def invert_selection(self, width: int, height: int):
        """
        反选

        Args:
            width: 图片宽度
            height: 图片高度
        """
        if self.selection_mask is None:
            # 如果没有选区，创建全选
            self.selection_mask = np.ones((height, width), dtype=bool)
        elif self.selection_mask.shape != (height, width):
            # 尺寸不匹配（图片被裁剪了），创建全选
            self.selection_mask = np.ones((height, width), dtype=bool)
        else:
            # 反转选区
            self.selection_mask = ~self.selection_mask

    def start_drag_select(self, image_data: 'ImageData', x: int, y: int) -> tuple[int, int, int, int]:
        """
        开始拖动选择（复用画笔逻辑）

        Args:
            image_data: 图片数据
            x: 起始 X 坐标
            y: 起始 Y 坐标

        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        self.is_dragging = True
        self.last_point = (x, y)

        # 缓存像素数据（性能优化：避免在拖动过程中重复合成）
        cached_pixels = image_data.get_current_pixels()

        # 创建新的选择笔画，传入缓存的像素数据
        self.current_stroke = SelectionStroke(self.size, self.selection_mode, cached_pixels)
        self.current_stroke.add_point(x, y)

        # 初始化选区蒙版
        if self.selection_mask is None or self.selection_mask.shape != (image_data.height, image_data.width):
            self.selection_mask = np.zeros((image_data.height, image_data.width), dtype=bool)

        # 光栅化第一个点
        return self.current_stroke.rasterize(image_data, self.selection_mask, 0)

    def continue_drag_select(self, image_data: 'ImageData', x: int, y: int) -> tuple[int, int, int, int]:
        """
        继续拖动选择（带插值，避免断点）

        Args:
            image_data: 图片数据
            x: 当前 X 坐标
            y: 当前 Y 坐标

        Returns:
            脏区域 (x_min, y_min, x_max, y_max)，如果没有更新则返回 (0, 0, 0, 0)
        """
        if not self.is_dragging or self.current_stroke is None or self.last_point is None:
            return (0, 0, 0, 0)

        # 使用 StrokeInterpolator 计算插值点
        interpolated_points = StrokeInterpolator.interpolate_points(
            self.last_point,
            (x, y),
            self.size,
            self.spacing
        )

        # 如果有插值点，添加并光栅化
        if len(interpolated_points) > 0:
            # 记录开始索引
            start_index = len(self.current_stroke.points)

            # 添加所有插值点
            for point in interpolated_points:
                self.current_stroke.add_point(point[0], point[1])

            # 增量光栅化（只处理新点）
            dirty_rect = self.current_stroke.rasterize(image_data, self.selection_mask, start_index)

            # 更新最后位置为当前鼠标位置（简化版本）
            self.last_point = (x, y)

            return dirty_rect

        return (0, 0, 0, 0)

    def end_drag_select(self, image_data: 'ImageData' = None, smart_selection: bool = False):
        """
        结束拖动选择
        
        Args:
            image_data: 图片数据（智能选择需要）
            smart_selection: 是否启用智能选择边界优化
            
        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        self.is_dragging = False
        self.current_stroke = None
        self.last_point = None
        
        # 如果启用智能选择，优化边界
        if smart_selection and image_data is not None and self.has_selection():
            return self.optimize_selection_boundary(image_data)
        
        return (0, 0, 0, 0)

    def start_rect_select(self, x: int, y: int):
        """
        开始矩形框选

        Args:
            x: 起始 X 坐标（像素）
            y: 起始 Y 坐标（像素）
        """
        self.rect_selector.start(x, y)
        self.is_dragging = True

    def continue_rect_select(self, x: int, y: int):
        """
        继续矩形框选

        Args:
            x: 当前 X 坐标（像素）
            y: 当前 Y 坐标（像素）
        """
        if self.is_dragging:
            self.rect_selector.update(x, y)

    def end_rect_select(self, image_data: 'ImageData'):
        """
        结束矩形框选，创建选区

        Args:
            image_data: 图片数据
        """
        if not self.is_dragging or not self.rect_selector.is_active():
            return

        self.is_dragging = False

        # 获取矩形范围
        rect = self.rect_selector.get_rect()
        if rect is None:
            return

        x, y, width, height = rect

        # 限制在图片范围内
        x_min = max(0, x)
        y_min = max(0, y)
        x_max = min(image_data.width, x + width)
        y_max = min(image_data.height, y + height)

        # 创建矩形选区，但只选择匹配目标颜色的像素
        if self.selection_mask is None or self.selection_mask.shape != (image_data.height, image_data.width):
            self.selection_mask = np.zeros((image_data.height, image_data.width), dtype=bool)

        # 获取像素数据
        pixels = image_data.get_current_pixels()

        # 创建矩形区域选区（选择所有像素，不限颜色）
        rect_mask = np.zeros((image_data.height, image_data.width), dtype=bool)
        rect_mask[y_min:y_max, x_min:x_max] = True

        # 根据模式合并选区
        if self.selection_mode == 'add':
            self.selection_mask = self.selection_mask | rect_mask
        elif self.selection_mode == 'subtract':
            self.selection_mask = self.selection_mask & ~rect_mask

        # 清除矩形选择状态
        self.rect_selector.cancel()

    def cancel_rect_select(self):
        """取消矩形框选"""
        self.is_dragging = False
        self.rect_selector.cancel()

    def get_rect_select_rect(self) -> tuple[int, int, int, int] | None:
        """
        获取矩形框选的矩形范围（用于渲染）

        Returns:
            (x, y, width, height) 或 None
        """
        return self.rect_selector.get_rect()

    def select_by_color(self, image_data: 'ImageData', color: int):
        """
        按颜色选择：全局选择特定颜色的所有像素

        Args:
            image_data: 图片数据
            color: 目标颜色（0=黑色, 255=白色）
        """
        pixels = image_data.get_current_pixels()
        height, width = pixels.shape

        # 创建新的选区蒙版
        new_mask = self._global_color_select(pixels,
                                             np.zeros((height, width), dtype=bool),
                                             color)

        # 根据模式合并选区
        self._merge_selection(new_mask, width, height)

    def render_cursor(self, painter: 'QPainter', view_x: float, view_y: float,
                     view_size: float):
        """
        渲染选择工具光标

        绘制圆形外圈显示选择范围。
        外圈颜色表示模式：绿色=添加，红色=删除

        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
            view_size: 选择范围大小（视图坐标）
        """
        from PySide6.QtGui import QColor

        # 根据模式选择外圈颜色
        if self.selection_mode == 'add':
            ring_color = QColor(0, 255, 0)  # 绿色 - 添加
        else:
            ring_color = QColor(255, 0, 0)  # 红色 - 删除

        # 使用 CursorRenderer 渲染光标（不显示中心点）
        CursorRenderer.render_circle_cursor(
            painter, view_x, view_y, view_size,
            ring_color=ring_color,
            center_color=None,  # 不显示中心点
            show_crosshair=True,
            crosshair_threshold=self.crosshair_threshold
        )

    def render_rect_cursor(self, painter: 'QPainter', view_x: float, view_y: float):
        """
        渲染矩形框选模式下的十字光标

        Args:
            painter: Qt QPainter 对象
            view_x: 光标中心 X 坐标（视图坐标）
            view_y: 光标中心 Y 坐标（视图坐标）
        """
        from PySide6.QtGui import QColor

        # 根据模式选择十字颜色
        if self.selection_mode == 'add':
            crosshair_color = QColor(0, 255, 0)  # 绿色 - 添加
        else:
            crosshair_color = QColor(255, 0, 0)  # 红色 - 删除

        # 使用 CursorRenderer 渲染十字光标
        CursorRenderer.render_crosshair_cursor(
            painter, view_x, view_y,
            color=crosshair_color,
            size=20
        )

    def render_rect_select_overlay(self, painter: 'QPainter', view_transform):
        """
        渲染矩形框选覆盖层

        Args:
            painter: Qt QPainter 对象
            view_transform: ViewTransform 对象用于坐标转换
        """
        from PySide6.QtGui import QColor

        # 框线颜色根据模式改变
        if self.selection_mode == 'add':
            border_color = QColor(0, 255, 0)  # 绿色 - 添加
        else:
            border_color = QColor(255, 0, 0)  # 红色 - 删除

        # 使用 RectSelector 渲染覆盖层
        self.rect_selector.render_overlay(
            painter, view_transform,
            border_color=border_color,
            show_handles=True,
            dash_style=True
        )

    def _global_color_select(self, pixels: np.ndarray, mask: np.ndarray,
                            target_color: int) -> np.ndarray:
        """
        全局颜色选择

        Args:
            pixels: 像素数据
            mask: 选区蒙版（输出）
            target_color: 目标颜色

        Returns:
            更新后的蒙版
        """
        # 选择所有颜色相近的像素
        color_diff = np.abs(pixels.astype(int) - int(target_color))
        mask[color_diff <= self.tolerance] = True
        return mask

    def _merge_selection(self, new_mask: np.ndarray, width: int, height: int):
        """
        根据当前模式合并选区

        Args:
            new_mask: 新的选区蒙版
            width: 图片宽度
            height: 图片高度
        """
        if self.mode == self.MODE_NEW:
            # 新建选区
            self.selection_mask = new_mask
        elif self.mode == self.MODE_ADD:
            # 添加到选区
            if self.selection_mask is None or self.selection_mask.shape != new_mask.shape:
                # 如果没有选区或尺寸不匹配（图片被裁剪了），直接使用新选区
                self.selection_mask = new_mask
            else:
                self.selection_mask = self.selection_mask | new_mask
        elif self.mode == self.MODE_SUBTRACT:
            # 从选区减去
            if self.selection_mask is not None:
                if self.selection_mask.shape == new_mask.shape:
                    self.selection_mask = self.selection_mask & ~new_mask
                else:
                    # 尺寸不匹配，清除旧选区
                    self.selection_mask = None
        elif self.mode == self.MODE_INTERSECT:
            # 与选区相交
            if self.selection_mask is None or self.selection_mask.shape != new_mask.shape:
                # 如果没有选区或尺寸不匹配，使用空选区
                self.selection_mask = np.zeros((height, width), dtype=bool)
            else:
                self.selection_mask = self.selection_mask & new_mask

    def optimize_selection_boundary(
        self, 
        image_data: 'ImageData',
        search_radius: int = None,
        edge_threshold1: int = 50,
        edge_threshold2: int = 150
    ) -> tuple[int, int, int, int]:
        """
        优化选区边界，使其吸附到图像边缘
        
        Args:
            image_data: 图片数据
            search_radius: 边缘搜索半径（默认使用 self.size / 2）
            edge_threshold1: Canny 边缘检测低阈值
            edge_threshold2: Canny 边缘检测高阈值
        
        Returns:
            脏区域 (x_min, y_min, x_max, y_max)
        """
        import cv2
        
        
        if not self.has_selection():
            return (0, 0, 0, 0)
        
        if search_radius is None:
            search_radius = max(3, int(self.size / 2))
        
        
        # 保存原始选区用于计算脏区域
        old_mask = self.selection_mask.copy()
        
        try:
            # 1. 连通性分析：只保留最大的连通区域
            main_mask = self._extract_main_connected_region(self.selection_mask)
            
            if main_mask is None or not main_mask.any():
                return (0, 0, 0, 0)
            
            main_pixels = np.sum(main_mask)
            removed_pixels = np.sum(self.selection_mask) - main_pixels
            
            # 2. 提取主区域的外轮廓
            contours = self._extract_outer_contours(main_mask)
            
            if len(contours) == 0:
                return (0, 0, 0, 0)
            
            # 3. 在选区范围内进行边缘检测
            edge_map = self._detect_edges_in_region(
                image_data, 
                main_mask, 
                search_radius,
                edge_threshold1,
                edge_threshold2
            )
            edge_pixels = np.sum(edge_map > 0)
            
            # 4. 优化每个轮廓
            optimized_contours = []
            for i, contour in enumerate(contours):
                if len(contour) < 3:  # 跳过太小的轮廓
                    continue
                
                optimized = self._snap_contour_to_edges(
                    contour, 
                    edge_map, 
                    search_radius
                )
                
                # 平滑轮廓
                optimized = self._smooth_contour(optimized)
                
                optimized_contours.append(optimized)
            
            if len(optimized_contours) == 0:
                return (0, 0, 0, 0)
            
            # 5. 重建选区蒙版
            new_mask = self._rebuild_mask_from_contours(
                optimized_contours, 
                self.selection_mask.shape
            )
            new_pixels = np.sum(new_mask)
            
            # 6. 更新选区
            self.selection_mask = new_mask
            
            # 7. 计算脏区域
            dirty_rect = self._calculate_dirty_rect(old_mask, new_mask)
            
            return dirty_rect
            
        except Exception as e:
            # 如果优化失败，恢复原始选区
            import traceback
            traceback.print_exc()
            self.selection_mask = old_mask
            return (0, 0, 0, 0)

    def _extract_main_connected_region(self, mask: np.ndarray, min_area_ratio: float = 0.05) -> np.ndarray | None:
        """
        提取最大的连通区域，移除小的孤立块（PS风格）
        
        策略：
        1. 先用开运算去除1-3像素的小噪点
        2. 再用闭运算合并用户涂抹的小块
        3. 连通性分析找到最大区域
        4. 只保留最大的1个区域
        
        Args:
            mask: 输入选区蒙版
            min_area_ratio: 最小面积比例（未使用，保留接口兼容性）
        
        Returns:
            只包含最大连通区域的蒙版，如果没有找到则返回 None
        """
        import cv2
        
        mask_uint8 = mask.astype(np.uint8) * 255
        
        # 步骤1: 开运算 - 去除1-3像素的小噪点
        # 使用小核去除细小的孤立点
        small_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        opened_mask = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, small_kernel)
          
        # 步骤2: 闭运算 - 合并用户涂抹的小块
        # 使用大核合并分散的涂抹区域
        large_kernel_size = max(9, int(self.size / 2))  # 增大核尺寸
        large_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (large_kernel_size, large_kernel_size))
        closed_mask = cv2.morphologyEx(opened_mask, cv2.MORPH_CLOSE, large_kernel)
        
        # 步骤3: 连通性分析
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            closed_mask, 
            connectivity=8
        )
        
        if num_labels <= 1:  # 只有背景
            return None
        
        # 步骤4: 只保留最大的1个区域
        areas = stats[1:, cv2.CC_STAT_AREA]
        largest_idx = np.argmax(areas)
        largest_area = areas[largest_idx]
        largest_label = largest_idx + 1
        
        # 只保留最大区域
        main_mask = (labels == largest_label)
        
        return main_mask

    def _extract_outer_contours(self, mask: np.ndarray) -> list:
        """提取选区的外轮廓（只返回最大的1个）"""
        import cv2
        
        mask_uint8 = mask.astype(np.uint8) * 255
        contours, hierarchy = cv2.findContours(
            mask_uint8, 
            cv2.RETR_EXTERNAL,  # 只提取最外层轮廓
            cv2.CHAIN_APPROX_NONE  # 保留所有轮廓点
        )
        
        if len(contours) == 0:
            return []
        
        # PS风格：只返回最大的1个轮廓
        if len(contours) > 1:
            # 按轮廓面积排序
            areas = [cv2.contourArea(c) for c in contours]
            largest_idx = np.argmax(areas)
            return [contours[largest_idx]]
        
        return list(contours)

    def _detect_edges_in_region(
        self, 
        image_data: 'ImageData', 
        mask: np.ndarray,
        margin: int,
        threshold1: int,
        threshold2: int
    ) -> np.ndarray:
        """在选区范围内检测边缘（提高阈值减少噪点）"""
        import cv2
        
        # 获取选区的包围盒
        y_indices, x_indices = np.where(mask)
        if len(y_indices) == 0:
            return np.zeros_like(mask, dtype=np.uint8)
        
        x_min = max(0, x_indices.min() - margin)
        x_max = min(mask.shape[1], x_indices.max() + margin + 1)
        y_min = max(0, y_indices.min() - margin)
        y_max = min(mask.shape[0], y_indices.max() + margin + 1)
        
        # 提取区域图像
        pixels = image_data.get_current_pixels()
        region = pixels[y_min:y_max, x_min:x_max]
        
        if region.size == 0:
            return np.zeros_like(mask, dtype=np.uint8)
        
        # PS风格：提高阈值，只检测强边缘，减少噪点干扰
        # 使用更高的阈值
        high_threshold1 = max(threshold1, 100)
        high_threshold2 = max(threshold2, 200)
        
        
        # Canny 边缘检测
        edges = cv2.Canny(
            region.astype(np.uint8), 
            threshold1=high_threshold1,
            threshold2=high_threshold2,
            apertureSize=3
        )
        
        # 创建完整尺寸的边缘图
        edge_map = np.zeros_like(mask, dtype=np.uint8)
        edge_map[y_min:y_max, x_min:x_max] = edges
        
        return edge_map

    def _snap_contour_to_edges(
        self,
        contour: np.ndarray,
        edge_map: np.ndarray,
        search_radius: int
    ) -> np.ndarray:
        """将轮廓点吸附到最近的边缘"""
        optimized_points = []
        
        for point in contour:
            x, y = point[0]
            
            # 定义搜索窗口
            x_min = max(0, x - search_radius)
            x_max = min(edge_map.shape[1], x + search_radius + 1)
            y_min = max(0, y - search_radius)
            y_max = min(edge_map.shape[0], y + search_radius + 1)
            
            # 在窗口内查找最近的强边缘
            window = edge_map[y_min:y_max, x_min:x_max]
            
            if window.size == 0:
                optimized_points.append([x, y])
                continue
            
            # 找到边缘点
            edge_points = np.argwhere(window > 0)
            
            if len(edge_points) > 0:
                # 计算到所有边缘点的距离
                distances = np.sqrt(
                    (edge_points[:, 1] - (x - x_min))**2 + 
                    (edge_points[:, 0] - (y - y_min))**2
                )
                
                # 找到最近的边缘点
                nearest_idx = np.argmin(distances)
                nearest_dist = distances[nearest_idx]
                
                # 如果距离在搜索半径内，吸附到边缘
                if nearest_dist <= search_radius:
                    new_y = edge_points[nearest_idx][0] + y_min
                    new_x = edge_points[nearest_idx][1] + x_min
                    optimized_points.append([new_x, new_y])
                else:
                    optimized_points.append([x, y])
            else:
                # 没有找到边缘，保持原位置
                optimized_points.append([x, y])
        
        return np.array(optimized_points, dtype=np.int32).reshape(-1, 1, 2)

    def _smooth_contour(self, contour: np.ndarray, epsilon_factor: float = 0.001) -> np.ndarray:
        """平滑轮廓，去除噪点"""
        import cv2
        
        # 计算轮廓周长
        perimeter = cv2.arcLength(contour, True)
        
        # 使用多边形逼近简化轮廓
        epsilon = epsilon_factor * perimeter
        smoothed = cv2.approxPolyDP(contour, epsilon, True)
        
        return smoothed

    def _rebuild_mask_from_contours(
        self,
        contours: list,
        shape: tuple
    ) -> np.ndarray:
        """从优化后的轮廓重建选区蒙版"""
        import cv2
        
        # 创建空白蒙版
        new_mask = np.zeros(shape, dtype=np.uint8)
        
        # 绘制填充的轮廓
        cv2.drawContours(
            new_mask, 
            contours, 
            -1,  # 绘制所有轮廓
            255,  # 颜色
            -1  # 填充
        )
        
        return new_mask.astype(bool)

    def _calculate_dirty_rect(
        self,
        old_mask: np.ndarray,
        new_mask: np.ndarray
    ) -> tuple[int, int, int, int]:
        """计算变化区域"""
        # 找到变化的像素
        diff = np.logical_xor(old_mask, new_mask)
        
        if not diff.any():
            return (0, 0, 0, 0)
        
        y_indices, x_indices = np.where(diff)
        
        return (
            int(x_indices.min()),
            int(y_indices.min()),
            int(x_indices.max() + 1),
            int(y_indices.max() + 1)
        )
