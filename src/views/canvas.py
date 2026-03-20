"""
Canvas 画布组件

负责图片显示、用户交互和工具渲染。
"""

from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint, QUrl
from PySide6.QtGui import QPainter, QPixmap, QImage, QPaintEvent, QMouseEvent, QWheelEvent, QDragEnterEvent, QDropEvent

from ..models.view_transform import ViewTransform
from ..models.image_data import ImageData
from ..models.brush_tool import BrushTool
from ..models.crop_tool import CropTool


class Canvas(QWidget):
    """
    Canvas 画布类
    
    显示图片并处理用户交互（鼠标、滚轮）。
    支持缩放、平移、画笔绘制和裁剪工具。
    """
    
    # 信号
    image_modified = Signal()  # 图片被修改时发射
    file_dropped = Signal(str)  # 文件拖放时发射，传递文件路径
    
    def __init__(self, parent=None):
        """
        初始化 Canvas
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        
        # 数据
        self.image_data: Optional[ImageData] = None
        self.view_transform = ViewTransform()
        
        # 工具
        self.current_tool: Optional[BrushTool | CropTool] = None
        self.brush_tool = BrushTool()
        self.crop_tool = CropTool()
        
        # 渲染缓存
        self.pixmap_cache: Optional[QPixmap] = None
        self.cache_valid = False
        
        # 交互状态
        self.mouse_pos: Optional[QPoint] = None
        self.is_panning = False
        self.pan_start_pos: Optional[QPoint] = None
        self.space_pressed = False
        
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
        self.cache_valid = False
        
        # 自动适配缩放
        self._fit_image_to_view()
        
        self.update()
    
    def set_tool(self, tool: Optional[BrushTool | CropTool]):
        """
        设置当前工具
        
        Args:
            tool: 工具对象（BrushTool 或 CropTool）
        """
        self.current_tool = tool
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
        
        if self.image_data is None:
            return
        
        # 渲染图片
        self._render_image(painter)
        
        # 渲染工具覆盖层
        if isinstance(self.current_tool, CropTool):
            self.current_tool.render_overlay(painter, self.view_transform)
        
        # 渲染画笔光标
        if isinstance(self.current_tool, BrushTool) and self.mouse_pos is not None:
            view_size = self.view_transform.get_brush_view_size(self.current_tool.size)
            self.current_tool.render_cursor(
                painter, 
                self.mouse_pos.x(), 
                self.mouse_pos.y(), 
                view_size
            )
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            if self.space_pressed or event.button() == Qt.MiddleButton:
                # 开始平移
                self.is_panning = True
                self.pan_start_pos = event.pos()
            elif self.image_data is not None and self.current_tool is not None:
                # 工具操作
                pixel_x, pixel_y = self.view_transform.view_to_pixel(
                    event.pos().x(), event.pos().y()
                )
                
                if isinstance(self.current_tool, BrushTool):
                    # 开始画笔笔画
                    self.image_data.start_temp_layer()
                    stroke = self.current_tool.start_stroke(pixel_x, pixel_y)
                    stroke.rasterize(self.image_data)
                    self.cache_valid = False
                    self.update()
                
                elif isinstance(self.current_tool, CropTool):
                    # 开始裁剪选择
                    self.current_tool.start_selection(pixel_x, pixel_y)
                    self.update()
        
        elif event.button() == Qt.MiddleButton:
            # 中键平移
            self.is_panning = True
            self.pan_start_pos = event.pos()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        self.mouse_pos = event.pos()
        
        if self.is_panning and self.pan_start_pos is not None:
            # 平移视图
            delta_x = event.pos().x() - self.pan_start_pos.x()
            delta_y = event.pos().y() - self.pan_start_pos.y()
            self.view_transform.translate(delta_x, delta_y)
            self.pan_start_pos = event.pos()
            self.cache_valid = False
            self.update()
        
        elif self.image_data is not None and self.current_tool is not None:
            pixel_x, pixel_y = self.view_transform.view_to_pixel(
                event.pos().x(), event.pos().y()
            )
            
            if isinstance(self.current_tool, BrushTool) and self.current_tool.is_drawing:
                # 继续画笔笔画
                self.current_tool.continue_stroke(pixel_x, pixel_y)
                if self.current_tool.current_stroke is not None:
                    # 只光栅化新添加的点
                    self.current_tool.current_stroke.rasterize(self.image_data)
                self.cache_valid = False
                self.update()
            
            elif isinstance(self.current_tool, CropTool) and self.current_tool.is_dragging:
                # 更新裁剪选择
                self.current_tool.update_selection(pixel_x, pixel_y)
                self.update()
            
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
            
            elif self.image_data is not None and self.current_tool is not None:
                if isinstance(self.current_tool, BrushTool) and self.current_tool.is_drawing:
                    # 结束画笔笔画
                    self.current_tool.end_stroke()
                    self.image_data.commit_temp_layer()
                    self.cache_valid = False
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
                            
                            # 通知图片已修改
                            self.cache_valid = False
                            self.image_modified.emit()
                            self.update()
        
        elif event.button() == Qt.MiddleButton:
            # 结束中键平移
            self.is_panning = False
            self.pan_start_pos = None
    
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
        
        self.cache_valid = False
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
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    # 发射信号通知主窗口加载文件
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def _render_image(self, painter: QPainter):
        """
        渲染图片到画布
        
        使用缓存提高性能。
        """
        if not self.cache_valid:
            self._update_cache()
        
        if self.pixmap_cache is not None:
            # 计算图片在视图中的位置
            view_x, view_y = self.view_transform.pixel_to_view(0, 0)
            painter.drawPixmap(int(view_x), int(view_y), self.pixmap_cache)
    
    def _update_cache(self):
        """更新渲染缓存"""
        if self.image_data is None:
            return
        
        # 获取当前像素数据
        pixels = self.image_data.get_current_pixels()
        
        # 转换为 QImage
        height, width = pixels.shape
        bytes_per_line = width
        qimage = QImage(pixels.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        
        # 缩放到视图大小
        scaled_width = int(width * self.view_transform.scale)
        scaled_height = int(height * self.view_transform.scale)
        
        # 创建 QPixmap 缓存
        self.pixmap_cache = QPixmap.fromImage(qimage).scaled(
            scaled_width, scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation if self.view_transform.scale < 1.0 else Qt.FastTransformation
        )
        
        self.cache_valid = True
    
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
