"""
Canvas 画布组件

负责图片显示、用户交互和工具渲染。
"""

from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint, QUrl, QTimer
from PySide6.QtGui import QPainter, QPixmap, QImage, QPaintEvent, QMouseEvent, QWheelEvent, QDragEnterEvent, QDropEvent
import numpy as np

from ..models.view_transform import ViewTransform
from ..models.image_data import ImageData
from ..models.brush_tool import BrushTool
from ..models.crop_tool import CropTool
from ..models.selection_tool import SelectionTool
from ..models.pan_tool import PanTool
from ..models.tile_cache import TileCache
from ..utils.translation_manager import get_translator


class Canvas(QWidget):
    """
    Canvas 画布类
    
    显示图片并处理用户交互（鼠标、滚轮）。
    支持缩放、平移、画笔绘制和裁剪工具。
    """
    
    # 信号
    image_modified = Signal()  # 图片被修改时发射
    file_dropped = Signal(str)  # 文件拖放时发射，传递文件路径
    zoom_changed = Signal(float)  # 缩放比例变化时发射
    
    def __init__(self, parent=None):
        """
        初始化 Canvas
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        
        # 翻译器
        self.tr = get_translator()
        
        # 数据
        self.image_data: Optional[ImageData] = None
        self.view_transform = ViewTransform()
        
        # 工具
        self.current_tool: Optional[BrushTool | CropTool | SelectionTool | PanTool] = None
        self.pan_tool = PanTool()
        self.brush_tool = BrushTool()
        self.crop_tool = CropTool()
        self.selection_tool = SelectionTool()
        
        # 分块渲染缓存
        # 提高缓存数量以支持大缩放时的流畅绘制
        # 在 10x 缩放时，一个 1920x1080 的视口大约需要 80-100 个 tiles
        # 设置为 1000 可以支持更大的图片和更流畅的拖动/缩放
        # 内存占用约 250MB（每个 tile 约 250KB）
        self.tile_cache = TileCache(tile_size=256, max_tiles=1000)
        
        # 拖动节流定时器（用于优化大图拖动性能）
        self.pan_update_timer = QTimer()
        self.pan_update_timer.setSingleShot(True)
        self.pan_update_timer.timeout.connect(self._do_pan_update)
        self.pan_throttle_interval = 16  # 16ms = 60fps
        self.pending_pan_update = False
        
        # 选择工具更新节流定时器（优化选择工具性能）
        self.selection_update_timer = QTimer()
        self.selection_update_timer.setSingleShot(True)
        self.selection_update_timer.timeout.connect(self._do_selection_update)
        self.selection_throttle_interval = 16  # 16ms = 60fps
        self.pending_selection_dirty_rect = (0, 0, 0, 0)
        
        # 交互状态
        self.mouse_pos: Optional[QPoint] = None
        self.is_panning = False
        self.pan_start_pos: Optional[QPoint] = None
        self.space_pressed = False
        
        # 画笔绘制优化：记录已光栅化的点数
        self.rasterized_point_count = 0
        
        # 处理状态
        self.is_processing = False
        
        # 设置
        self.setMouseTracking(True)  # 启用鼠标跟踪
        self.setFocusPolicy(Qt.StrongFocus)  # 接收键盘事件
        self.setAcceptDrops(True)  # 启用拖放功能
    
    def set_image(self, image_data: ImageData):
        """
        设置要显示的图片
        
        Args:
            image_data: ImageData 对象
        """
        self.image_data = image_data
        
        # 更新分块缓存
        pixels = image_data.get_current_pixels()
        
        # 注意：不再强制转换为灰度图，TileCache 现在支持彩色图像
        
        selection_mask = image_data.selection_mask if hasattr(image_data, 'selection_mask') else None
        self.tile_cache.set_image(pixels, selection_mask)
        
        # 自动适配缩放
        self._fit_image_to_view()
        
        self.update()
    
    def set_tool(self, tool: Optional[BrushTool | CropTool | SelectionTool | PanTool]):
        """
        设置当前工具
        
        Args:
            tool: 工具对象（BrushTool、CropTool、SelectionTool 或 PanTool）
        """
        self.current_tool = tool
        
        # 根据工具类型设置光标
        if isinstance(tool, PanTool):
            # 抓取工具：显示张开的手
            self.setCursor(Qt.OpenHandCursor)
        elif isinstance(tool, BrushTool):
            # 画笔工具：隐藏系统光标
            self.setCursor(Qt.BlankCursor)
        elif isinstance(tool, CropTool):
            # 裁剪工具：隐藏系统光标（显示自定义红色十字）
            self.setCursor(Qt.BlankCursor)
        elif isinstance(tool, SelectionTool):
            # 选择工具：隐藏系统光标（无论哪种模式都显示自定义光标）
            self.setCursor(Qt.BlankCursor)
        else:
            # 其他工具或无工具：恢复默认光标
            self.setCursor(Qt.ArrowCursor)
        
        self.update()
    
    def set_processing(self, is_processing: bool):
        """
        设置处理状态
        
        Args:
            is_processing: 是否正在处理
        """
        self.is_processing = is_processing
        self.update()
    
    def paintEvent(self, event: QPaintEvent):
        """
        绘制事件处理
        
        渲染图片、工具覆盖层和画笔光标。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 填充背景
        painter.fillRect(self.rect(), Qt.gray)
        
        # 渲染处理中提示（在检查 image_data 之前，这样加载时也能显示）
        if self.is_processing:
            self._render_processing_indicator(painter)
        
        if self.image_data is None:
            return
        
        # 渲染图片
        self._render_image(painter)
        
        # 渲染工具覆盖层
        if isinstance(self.current_tool, CropTool):
            self.current_tool.render_overlay(painter, self.view_transform)
            # 渲染裁剪工具的红色十字光标
            if self.mouse_pos is not None:
                self.current_tool.render_cursor(
                    painter,
                    self.mouse_pos.x(),
                    self.mouse_pos.y()
                )
        
        # 渲染选择工具的矩形框选覆盖层和十字光标
        if isinstance(self.current_tool, SelectionTool) and self.current_tool.rect_select_mode:
            self.current_tool.render_rect_select_overlay(painter, self.view_transform)
            # 在矩形框选模式下显示十字光标
            if self.mouse_pos is not None:
                self.current_tool.render_rect_cursor(
                    painter,
                    self.mouse_pos.x(),
                    self.mouse_pos.y()
                )
        
        # 渲染画笔光标
        if isinstance(self.current_tool, BrushTool) and self.mouse_pos is not None:
            view_size = self.view_transform.get_brush_view_size(self.current_tool.size)
            self.current_tool.render_cursor(
                painter, 
                self.mouse_pos.x(), 
                self.mouse_pos.y(), 
                view_size
            )
        
        # 渲染选择工具光标（只在非矩形框选模式下显示）
        if isinstance(self.current_tool, SelectionTool) and self.mouse_pos is not None and not self.current_tool.rect_select_mode:
            view_size = self.view_transform.get_brush_view_size(self.current_tool.size)
            self.current_tool.render_cursor(
                painter,
                self.mouse_pos.x(),
                self.mouse_pos.y(),
                view_size
            )
    
    def _render_processing_indicator(self, painter: QPainter):
        """
        渲染处理中提示
        
        在画布顶部居中显示小巧的"处理中"提示。
        """
        # 设置字体（小号）
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        # 文本内容
        text = self.tr.tr('app.processing')
        
        # 计算文本尺寸
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        
        # 计算位置（顶部居中，距离顶部 20px）
        padding = 8
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        box_x = (self.width() - box_width) / 2
        box_y = 20
        
        # 绘制半透明背景
        from PySide6.QtGui import QColor
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 230))  # 白色半透明
        painter.drawRoundedRect(int(box_x), int(box_y), int(box_width), int(box_height), 4, 4)
        
        # 绘制边框
        painter.setPen(QColor(200, 200, 200))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(int(box_x), int(box_y), int(box_width), int(box_height), 4, 4)
        
        # 绘制文本
        painter.setPen(QColor(100, 100, 100))  # 深灰色文字
        text_x = box_x + padding
        text_y = box_y + padding + metrics.ascent()
        painter.drawText(int(text_x), int(text_y), text)
        
        painter.restore()
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            if self.space_pressed or event.button() == Qt.MiddleButton:
                # 开始平移
                self.is_panning = True
                self.pan_start_pos = event.pos()
            elif isinstance(self.current_tool, PanTool):
                # 抓取工具：开始平移
                self.current_tool.start_pan(event.pos().x(), event.pos().y())
                self.setCursor(Qt.ClosedHandCursor)
            elif self.image_data is not None and self.current_tool is not None:
                # 工具操作
                pixel_x, pixel_y = self.view_transform.view_to_pixel(
                    event.pos().x(), event.pos().y()
                )
                
                if isinstance(self.current_tool, BrushTool):
                    # 开始画笔笔画
                    self.image_data.start_temp_layer()
                    stroke = self.current_tool.start_stroke(pixel_x, pixel_y)
                    dirty_rect = stroke.rasterize(self.image_data)
                    self.rasterized_point_count = len(stroke.points)
                    # 更新分块缓存
                    self._update_tile_cache()
                    self.update()
                
                elif isinstance(self.current_tool, CropTool):
                    # 开始裁剪选择
                    self.current_tool.start_selection(pixel_x, pixel_y)
                    self.update()
                
                elif isinstance(self.current_tool, SelectionTool):
                    # 检查是否是矩形框选模式
                    if self.current_tool.rect_select_mode:
                        # 开始矩形框选
                        self.current_tool.start_rect_select(pixel_x, pixel_y)
                        self.update()
                    else:
                        # 开始拖动选择
                        dirty_rect = self.current_tool.start_drag_select(self.image_data, pixel_x, pixel_y)
                        # 将选区同步到 image_data
                        self.image_data.selection_mask = self.current_tool.selection_mask
                        # 直接更新 tile_cache 的选区引用（避免复制整个图像）
                        self.tile_cache.selection_mask = self.current_tool.selection_mask
                        # 使脏区域失效
                        if dirty_rect[2] > dirty_rect[0] and dirty_rect[3] > dirty_rect[1]:
                            self.tile_cache.invalidate_region(
                                dirty_rect[0], dirty_rect[1],
                                dirty_rect[2] - dirty_rect[0],
                                dirty_rect[3] - dirty_rect[1]
                            )
                        self.update()
        
        elif event.button() == Qt.MiddleButton:
            # 中键平移
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)  # 设置为抓取光标
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        self.mouse_pos = event.pos()
        
        if self.is_panning and self.pan_start_pos is not None:
            # 平移视图
            delta_x = event.pos().x() - self.pan_start_pos.x()
            delta_y = event.pos().y() - self.pan_start_pos.y()
            self.view_transform.translate(delta_x, delta_y)
            self.pan_start_pos = event.pos()
            
            # 使用节流优化：不立即更新，而是标记需要更新
            self.pending_pan_update = True
            if not self.pan_update_timer.isActive():
                # 立即更新第一次，然后启动定时器
                self.update()
                self.pan_update_timer.start(self.pan_throttle_interval)
        
        elif isinstance(self.current_tool, PanTool) and self.current_tool.is_panning:
            # 抓取工具平移
            delta_x, delta_y = self.current_tool.continue_pan(event.pos().x(), event.pos().y())
            self.view_transform.translate(delta_x, delta_y)
            
            # 使用节流优化
            self.pending_pan_update = True
            if not self.pan_update_timer.isActive():
                self.update()
                self.pan_update_timer.start(self.pan_throttle_interval)
        
        elif self.image_data is not None and self.current_tool is not None:
            pixel_x, pixel_y = self.view_transform.view_to_pixel(
                event.pos().x(), event.pos().y()
            )
            
            if isinstance(self.current_tool, BrushTool) and self.current_tool.is_drawing:
                # 继续画笔笔画
                old_point_count = self.rasterized_point_count
                self.current_tool.continue_stroke(pixel_x, pixel_y)
                if self.current_tool.current_stroke is not None:
                    # 只光栅化新添加的点（增量更新）
                    dirty_rect = self.current_tool.current_stroke.rasterize(self.image_data, old_point_count)
                    self.rasterized_point_count = len(self.current_tool.current_stroke.points)
                    
                    # 更新图片数据并使脏区域失效
                    if dirty_rect[2] > dirty_rect[0] and dirty_rect[3] > dirty_rect[1]:
                        pixels = self.image_data.get_current_pixels()
                        selection_mask = self.image_data.selection_mask if hasattr(self.image_data, 'selection_mask') else None
                        self.tile_cache.update_image(pixels, selection_mask)
                        self.tile_cache.invalidate_region(
                            dirty_rect[0], dirty_rect[1], 
                            dirty_rect[2] - dirty_rect[0], 
                            dirty_rect[3] - dirty_rect[1]
                        )
                    
                    self.update()
            
            elif isinstance(self.current_tool, CropTool) and self.current_tool.is_dragging:
                # 更新裁剪选择
                self.current_tool.update_selection(pixel_x, pixel_y)
                self.update()
            
            elif isinstance(self.current_tool, SelectionTool) and self.current_tool.is_dragging:
                # 检查是否是矩形框选模式
                if self.current_tool.rect_select_mode:
                    # 更新矩形框选
                    self.current_tool.continue_rect_select(pixel_x, pixel_y)
                    self.update()
                else:
                    # 继续拖动选择（优化版本）
                    dirty_rect = self.current_tool.continue_drag_select(self.image_data, pixel_x, pixel_y)
                    
                    # 只在有实际更新时处理
                    if dirty_rect[2] > dirty_rect[0] and dirty_rect[3] > dirty_rect[1]:
                        # 将选区同步到 image_data（引用，不复制）
                        self.image_data.selection_mask = self.current_tool.selection_mask
                        # 直接更新 tile_cache 的选区引用（避免复制整个图像）
                        self.tile_cache.selection_mask = self.current_tool.selection_mask
                        
                        # 累积脏区域用于批量失效
                        if self.pending_selection_dirty_rect[2] > self.pending_selection_dirty_rect[0]:
                            # 合并脏区域
                            old_rect = self.pending_selection_dirty_rect
                            self.pending_selection_dirty_rect = (
                                min(old_rect[0], dirty_rect[0]),
                                min(old_rect[1], dirty_rect[1]),
                                max(old_rect[2], dirty_rect[2]),
                                max(old_rect[3], dirty_rect[3])
                            )
                        else:
                            self.pending_selection_dirty_rect = dirty_rect
                        
                        # 立即触发重绘（保持流畅），但延迟失效瓦片（减少计算）
                        self.update()
                        
                        # 使用节流来批量失效瓦片
                        if not self.selection_update_timer.isActive():
                            self.selection_update_timer.start(self.selection_throttle_interval)
            
            else:
                # 更新光标显示
                self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            if self.is_panning:
                # 结束平移
                self.is_panning = False
                self.pan_start_pos = None
                
                # 停止节流定时器并执行最后一次更新
                if self.pan_update_timer.isActive():
                    self.pan_update_timer.stop()
                if self.pending_pan_update:
                    self.pending_pan_update = False
                    self.update()
                
                # 恢复工具光标
                if self.current_tool is not None:
                    self.set_tool(self.current_tool)
                else:
                    self.setCursor(Qt.ArrowCursor)
            
            elif isinstance(self.current_tool, PanTool) and self.current_tool.is_panning:
                # 结束抓取工具平移
                self.current_tool.end_pan()
                
                # 停止节流定时器并执行最后一次更新
                if self.pan_update_timer.isActive():
                    self.pan_update_timer.stop()
                if self.pending_pan_update:
                    self.pending_pan_update = False
                    self.update()
                
                # 恢复张开的手光标
                self.setCursor(Qt.OpenHandCursor)
            
            elif self.image_data is not None and self.current_tool is not None:
                if isinstance(self.current_tool, BrushTool) and self.current_tool.is_drawing:
                    # 结束画笔笔画
                    self.current_tool.end_stroke()
                    self.image_data.commit_temp_layer()
                    self.rasterized_point_count = 0
                    # 完全更新分块缓存
                    self._update_tile_cache()
                    self.image_modified.emit()
                    self.update()
                
                elif isinstance(self.current_tool, CropTool):
                    # 结束裁剪选择并立即执行裁剪
                    self.current_tool.end_selection()
                    
                    # 立即执行裁剪
                    if self.current_tool.confirm_crop():
                        crop_rect = self.current_tool.get_crop_rect()
                        if crop_rect is not None:
                            # 执行裁剪
                            x, y, width, height = crop_rect
                            self.image_data.crop_in_place(x, y, width, height)
                            
                            # 取消选择
                            self.current_tool.cancel_selection()
                            
                            # 重新适配视图
                            self._fit_image_to_view()
                            
                            # 更新分块缓存
                            pixels = self.image_data.get_current_pixels()
                            
                            # 注意：不再强制转换为灰度图，TileCache 现在支持彩色图像
                            
                            selection_mask = self.image_data.selection_mask if hasattr(self.image_data, 'selection_mask') else None
                            self.tile_cache.set_image(pixels, selection_mask)
                            
                            # 通知图片已修改
                            self.image_modified.emit()
                            self.update()
                
                elif isinstance(self.current_tool, SelectionTool) and self.current_tool.is_dragging:
                    # 检查是否是矩形框选模式
                    if self.current_tool.rect_select_mode:
                        # 结束矩形框选
                        self.current_tool.end_rect_select(self.image_data)
                        # 将选区同步到 image_data
                        self.image_data.selection_mask = self.current_tool.selection_mask
                        # 更新 tile_cache 的选区引用
                        self.tile_cache.selection_mask = self.current_tool.selection_mask
                        # 使整个选区失效以触发重新渲染
                        if self.current_tool.selection_mask is not None and self.current_tool.selection_mask.any():
                            rows, cols = np.where(self.current_tool.selection_mask)
                            if len(rows) > 0:
                                self.tile_cache.invalidate_region(
                                    cols.min(), rows.min(),
                                    cols.max() - cols.min() + 1,
                                    rows.max() - rows.min() + 1
                                )
                        # 通知选区已修改
                        self.image_modified.emit()
                        self.update()
                    else:
                        # 结束拖动选择
                        self.current_tool.end_drag_select()
                        
                        # 停止节流定时器并执行最后一次失效
                        if self.selection_update_timer.isActive():
                            self.selection_update_timer.stop()
                        # 失效最后的累积区域
                        if self.pending_selection_dirty_rect[2] > self.pending_selection_dirty_rect[0]:
                            self._do_selection_update()
                        
                        # 将选区同步到 image_data（引用，不复制）
                        self.image_data.selection_mask = self.current_tool.selection_mask
                        # 确保 tile_cache 引用最新的选区
                        self.tile_cache.selection_mask = self.current_tool.selection_mask
                        
                        # 通知选区已修改（用于更新 UI 状态）
                        self.image_modified.emit()
                        self.update()
        
        elif event.button() == Qt.MiddleButton:
            # 结束中键平移
            self.is_panning = False
            self.pan_start_pos = None
            
            # 停止节流定时器并执行最后一次更新
            if self.pan_update_timer.isActive():
                self.pan_update_timer.stop()
            if self.pending_pan_update:
                self.pending_pan_update = False
                self.update()
            
            # 恢复工具光标
            if self.current_tool is not None:
                self.set_tool(self.current_tool)
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def _do_pan_update(self):
        """节流定时器回调：执行延迟的平移更新"""
        if self.pending_pan_update:
            self.pending_pan_update = False
            self.update()
            
            # 如果还在拖动，继续定时器
            if self.is_panning:
                self.pan_update_timer.start(self.pan_throttle_interval)
    
    def _do_selection_update(self):
        """节流定时器回调：批量失效累积的脏区域"""
        if self.pending_selection_dirty_rect[2] > self.pending_selection_dirty_rect[0]:
            # 使累积的脏区域失效
            dirty_rect = self.pending_selection_dirty_rect
            self.tile_cache.invalidate_region(
                dirty_rect[0], dirty_rect[1],
                dirty_rect[2] - dirty_rect[0],
                dirty_rect[3] - dirty_rect[1]
            )
            # 重置脏区域
            self.pending_selection_dirty_rect = (0, 0, 0, 0)
    
    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件 - 缩放"""
        if self.image_data is None:
            return
        
        # 计算缩放因子
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9
        
        # 以鼠标位置为中心缩放
        self.view_transform.zoom_at_point(
            event.position().x(),
            event.position().y(),
            scale_factor
        )
        
        # 发射缩放变化信号
        self.zoom_changed.emit(self.view_transform.scale)
        
        self.update()
    
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_Space:
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
    
    def keyReleaseEvent(self, event):
        """键盘释放事件"""
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            self.setCursor(Qt.ArrowCursor)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖动进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否包含图片文件
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    # 发射信号通知主窗口加载文件
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def _render_image(self, painter: QPainter):
        """
        渲染图片到画布（使用分块渲染）
        
        只渲染视口内可见的块，大幅提升性能。
        """
        if self.image_data is None:
            return
        
        # 更新缩放级别
        self.tile_cache.set_scale(self.view_transform.scale)
        
        # 获取视口内的所有块
        view_x, view_y = self.view_transform.pixel_to_view(0, 0)
        tiles = self.tile_cache.get_tiles_in_viewport(
            view_x, view_y,
            self.width(), self.height()
        )
        
        # 绘制所有块
        for tile_x, tile_y, draw_x, draw_y, draw_width, draw_height, pixmap in tiles:
            painter.drawPixmap(int(draw_x), int(draw_y), pixmap)
    
    def _update_tile_cache(self):
        """更新分块缓存的图片数据"""
        if self.image_data is None:
            return
        
        pixels = self.image_data.get_current_pixels()
        
        # 注意：不再强制转换为灰度图，TileCache 现在支持彩色图像
        
        selection_mask = self.image_data.selection_mask if hasattr(self.image_data, 'selection_mask') else None
        self.tile_cache.set_image(pixels, selection_mask)
    
    def _fit_image_to_view(self):
        """自动适配图片到视图"""
        if self.image_data is None:
            return
        
        canvas_width = self.width()
        canvas_height = self.height()
        
        if canvas_width <= 0 or canvas_height <= 0:
            return
        
        # 计算适配缩放
        scale_x = canvas_width / self.image_data.width
        scale_y = canvas_height / self.image_data.height
        scale = min(scale_x, scale_y) * 0.9  # 留 10% 边距
        
        self.view_transform.set_scale(scale)
        
        # 居中图片
        view_width = self.image_data.width * scale
        view_height = self.image_data.height * scale
        self.view_transform.offset_x = (canvas_width - view_width) / 2
        self.view_transform.offset_y = (canvas_height - view_height) / 2
        
        # 发射缩放变化信号
        self.zoom_changed.emit(self.view_transform.scale)
