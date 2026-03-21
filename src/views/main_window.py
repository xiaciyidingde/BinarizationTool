"""
主窗口模块

应用程序的主窗口，包含菜单栏、工具栏和主要布局。
"""

from typing import Optional
import os
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                QSplitter, QToolBar, QFileDialog, QMessageBox,
                                QPushButton, QLabel, QStatusBar, QSizePolicy,
                                QSpinBox, QRadioButton, QButtonGroup, QFrame)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QIcon, QEnterEvent

from .canvas import Canvas
from .binarization_panel import BinarizationPanel
from .shortcut_handler import ShortcutHandler
from ..models.image_data import ImageData
from ..models.history_manager import HistoryManager
from ..models.brush_tool import BrushTool
from ..models.selection_tool import SelectionTool
from ..utils.file_io import load_image, save_image
from ..utils.binarization_engine import BinarizationEngine


class MainWindow(QMainWindow):
    """
    主窗口类
    
    管理应用程序的整体布局和功能集成。
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 数据
        self.image_data: Optional[ImageData] = None
        self.history_manager = HistoryManager()
        self.current_file_path: Optional[str] = None
        self.saved_file_path: Optional[str] = None  # 记录已保存的文件路径
        
        # 设置窗口
        self.setWindowTitle("BinarizationTool - 二值化图片编辑器")
        self.setGeometry(100, 100, 1400, 800)
        
        # 创建 UI
        self.setup_ui()
        self.create_actions()
        self.create_toolbars()
        self.create_statusbar()
        
        # 连接信号
        self.connect_signals()
        
        # 初始状态
        self._update_ui_state()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建主分割器（左侧面板 + 中右部分）
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：二值化面板
        self.binarization_panel = BinarizationPanel()
        self.binarization_panel.setMaximumWidth(300)
        self.binarization_panel.setMinimumWidth(200)
        main_splitter.addWidget(self.binarization_panel)
        
        # 中右部分：Canvas + 属性面板
        center_right_splitter = QSplitter(Qt.Horizontal)
        
        # 中间：Canvas
        self.canvas = Canvas()
        center_right_splitter.addWidget(self.canvas)
        
        # 右侧：属性面板
        from .properties_panel import PropertiesPanel
        self.properties_panel = PropertiesPanel()
        center_right_splitter.addWidget(self.properties_panel)
        
        # 设置中右分割器比例
        center_right_splitter.setStretchFactor(0, 1)  # Canvas 可伸缩
        center_right_splitter.setStretchFactor(1, 0)  # 属性面板固定
        
        main_splitter.addWidget(center_right_splitter)
        
        # 设置主分割器比例
        main_splitter.setStretchFactor(0, 0)  # 左侧面板固定
        main_splitter.setStretchFactor(1, 1)  # 中右部分可伸缩
        
        main_layout.addWidget(main_splitter)
    
    def create_actions(self):
        """创建动作"""
        # 文件菜单动作
        self.open_action = QAction("打开 (Ctrl+O)", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._open_file)
        
        self.save_action = QAction("保存 (Ctrl+S)", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_file)
        
        self.save_as_action = QAction("另存为 (Ctrl+Shift+S)", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self._save_file_as)
        
        self.exit_action = QAction("退出 (Ctrl+Q)", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # 编辑菜单动作
        self.undo_action = QAction("后退 (Ctrl+Z)", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setToolTip("后退到上一步 (Ctrl+Z)")
        self.undo_action.triggered.connect(self._undo)
        
        self.redo_action = QAction("前进 (Ctrl+Y)", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setToolTip("前进到下一步 (Ctrl+Y)")
        self.redo_action.triggered.connect(self._redo)
        
        # 工具动作 - 创建自定义按钮以支持悬浮事件
        self.brush_button = QPushButton("画笔工具 (B)")
        self.brush_button.setCheckable(True)
        self.brush_button.setFlat(True)  # 扁平样式，类似 QAction
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)
        
        # 为画笔按钮添加快捷键
        self.brush_shortcut = QAction(self)
        self.brush_shortcut.setShortcut("B")
        self.brush_shortcut.triggered.connect(self._select_brush_tool)
        self.addAction(self.brush_shortcut)
        
        # 初始化快捷键处理器（统一管理工具快捷键）
        self.shortcut_handler = ShortcutHandler(self)
        
        self.crop_action = QAction("裁剪工具 (C)", self)
        self.crop_action.setShortcut("C")
        self.crop_action.setCheckable(True)
        self.crop_action.triggered.connect(self._select_crop_tool)
        
        # 选择工具动作
        self.selection_tool_action = QAction("选择工具 (W)", self)
        self.selection_tool_action.setShortcut("W")
        self.selection_tool_action.setCheckable(True)
        self.selection_tool_action.triggered.connect(self._select_selection_tool)
        self.addAction(self.selection_tool_action)  # 添加到主窗口以启用快捷键
        
        # 选区菜单动作
        self.deselect_action = QAction("取消选择 (Ctrl+D)", self)
        self.deselect_action.setShortcut("Ctrl+D")
        self.deselect_action.triggered.connect(self._deselect)
        
        self.invert_selection_action = QAction("反选 (Ctrl+Shift+I)", self)
        self.invert_selection_action.setShortcut("Ctrl+Shift+I")
        self.invert_selection_action.triggered.connect(self._invert_selection)
        
        self.select_black_action = QAction("选择黑色", self)
        self.select_black_action.triggered.connect(lambda: self._select_by_color(0))
        
        self.select_white_action = QAction("选择白色", self)
        self.select_white_action.triggered.connect(lambda: self._select_by_color(255))
    
    def create_toolbars(self):
        """创建工具栏"""
        self.toolbar = QToolBar("工具")
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)  # 禁用右键菜单
        self.addToolBar(self.toolbar)
        
        # 文件操作
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addSeparator()
        
        # 编辑操作 - 后退/前进
        self.toolbar.addAction(self.undo_action)
        self.toolbar.addAction(self.redo_action)
        self.toolbar.addSeparator()
        
        # 工具选择 - 使用自定义按钮
        self.toolbar.addWidget(self.brush_button)
        self.toolbar.addAction(self.crop_action)
        
        # 选择工具按钮（自定义以支持悬浮面板）
        self.selection_tool_button = QPushButton("选择工具 (W)")
        self.selection_tool_button.setCheckable(True)
        self.selection_tool_button.setFlat(True)  # 扁平样式，类似 QAction
        self.selection_tool_button.setEnabled(False)  # 初始状态为禁用
        self.selection_tool_button.clicked.connect(self._select_selection_tool)
        self.selection_tool_button.installEventFilter(self)
        self.toolbar.addWidget(self.selection_tool_button)
        
        # 添加弹性空间，将后续内容推到右边
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # 当前工具显示（右对齐）
        self.current_tool_label = QLabel("当前工具：无")
        self.current_tool_label.setStyleSheet("padding: 0 10px; color: #666;")
        self.toolbar.addWidget(self.current_tool_label)
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
        
        # 创建菜单栏（但隐藏，功能通过工具栏和快捷键访问）
        self._create_menus()
        self.menuBar().hide()  # 隐藏菜单栏
    
    def connect_signals(self):
        """连接信号"""
        # 二值化参数改变
        self.binarization_panel.parameters_changed.connect(self._on_parameters_changed)
        
        # Canvas 图片修改
        self.canvas.image_modified.connect(self._on_image_modified)
        
        # Canvas 文件拖放
        self.canvas.file_dropped.connect(self._load_file_from_path)
        
        # Canvas 缩放变化
        self.canvas.zoom_changed.connect(self.properties_panel.set_zoom_level)
        
        # 属性面板工具设置信号
        self._connect_tool_settings()
    
    def _create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        # 选择菜单
        select_menu = menubar.addMenu("选择")
        select_menu.addAction(self.deselect_action)
        select_menu.addAction(self.invert_selection_action)
        select_menu.addSeparator()
        select_menu.addAction(self.select_black_action)
        select_menu.addAction(self.select_white_action)
    
    def _select_brush_tool(self):
        """选择画笔工具"""
        if self.image_data is None:
            self.statusbar.showMessage("请先加载图片")
            return
        
        self.canvas.set_tool(self.canvas.brush_tool)
        self.brush_button.setChecked(True)
        self.crop_action.setChecked(False)
        self.selection_tool_action.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText("当前工具：画笔")
        self.statusbar.showMessage("画笔工具已激活")
        
        # 显示画笔工具设置
        self.properties_panel.show_brush_settings()
        
        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()
    
    def _select_crop_tool(self):
        """选择裁剪工具"""
        if self.image_data is None:
            return
        
        self.canvas.set_tool(self.canvas.crop_tool)
        self.brush_button.setChecked(False)
        self.crop_action.setChecked(True)
        self.selection_tool_action.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText("当前工具：裁剪")
        self.statusbar.showMessage("裁剪工具已激活")
        
        # 隐藏所有工具设置（裁剪工具没有设置）
        self.properties_panel.hide_all_tool_settings()
    
    def _select_selection_tool(self):
        """选择选择工具"""
        if self.image_data is None:
            self.statusbar.showMessage("请先加载图片")
            return
        
        self.canvas.set_tool(self.canvas.selection_tool)
        self.brush_button.setChecked(False)
        self.crop_action.setChecked(False)
        self.selection_tool_action.setChecked(False)
        self.selection_tool_button.setChecked(True)
        self.current_tool_label.setText("当前工具：选择")
        mode_text = "添加" if self.canvas.selection_tool.selection_mode == 'add' else "删除"
        self.statusbar.showMessage(f"选择工具已激活 - 模式：{mode_text}")
        
        # 显示选择工具设置
        self.properties_panel.show_selection_settings()
        
        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()
    
    def _deselect(self):
        """取消选择"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.clear_selection()
        self.image_data.selection_mask = None
        # 更新分块缓存以清除选区
        pixels = self.image_data.get_current_pixels()
        self.canvas.tile_cache.set_image(pixels, None)
        self.canvas.update()
        self._update_ui_state()  # 更新 UI 状态
        self.statusbar.showMessage("已取消选择")
    
    def _invert_selection(self):
        """反选"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.selection_mask = self.image_data.selection_mask
        self.canvas.selection_tool.invert_selection(
            self.image_data.width,
            self.image_data.height
        )
        self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
        # 更新分块缓存以显示选区
        pixels = self.image_data.get_current_pixels()
        self.canvas.tile_cache.set_image(pixels, self.image_data.selection_mask)
        self.canvas.update()
        self._update_ui_state()  # 更新 UI 状态
        self.statusbar.showMessage("已反选")
    
    def _select_by_color(self, color: int):
        """按颜色选择"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.select_by_color(self.image_data, color)
        self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
        # 更新分块缓存以显示选区
        pixels = self.image_data.get_current_pixels()
        self.canvas.tile_cache.set_image(pixels, self.image_data.selection_mask)
        self.canvas.update()
        self._update_ui_state()  # 更新 UI 状态
        color_name = "黑色" if color == 0 else "白色"
        self.statusbar.showMessage(f"已选择所有{color_name}像素")
    
    def _open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*.*)"
        )
        
        if file_path:
            self._load_file_from_path(file_path)
    
    def _load_file_from_path(self, file_path: str):
        """从文件路径加载图片（支持打开文件和拖放）"""
        try:
            # 加载图片（不自动二值化）
            self.image_data = load_image(file_path, binarize=False)
            
            # 应用预处理和二值化
            preprocess_params = self.binarization_panel.get_preprocess_params()
            method = self.binarization_panel.get_method()
            threshold = self.binarization_panel.get_threshold()
            
            # 预处理
            preprocessed = BinarizationEngine.apply_preprocess(
                self.image_data.original_pixels.copy(),
                **preprocess_params
            )
            
            # 二值化
            binary_pixels = BinarizationEngine.apply_threshold(
                preprocessed, method, threshold
            )
            
            self.image_data.pixels = binary_pixels
            
            # 设置到 Canvas
            self.canvas.set_image(self.image_data)
            
            # 清除历史并保存初始状态
            self.history_manager.clear()
            self.history_manager.push_state(self.image_data)
            
            # 保存文件路径
            self.current_file_path = file_path
            self.saved_file_path = None  # 重置保存路径，新文件需要重新保存
            
            # 更新属性面板
            self.properties_panel.set_image_info(self.image_data, file_path)
            
            # 更新状态
            self.statusbar.showMessage(f"已加载: {file_path}")
            self._update_ui_state()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载图片:\n{str(e)}")
    
    def _save_file(self):
        """保存文件（第一次另存为，之后覆盖）"""
        if self.image_data is None:
            return
        
        # 如果已经保存过，直接覆盖
        if self.saved_file_path:
            self._save_to_file(self.saved_file_path)
            return
        
        # 第一次保存：生成默认文件名并弹出对话框
        default_name = self._generate_default_save_name()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            default_name,
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.saved_file_path = file_path  # 记录保存路径
    
    def _save_file_as(self):
        """另存为（总是弹出对话框）"""
        if self.image_data is None:
            return
        
        # 生成默认文件名
        default_name = self._generate_default_save_name()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            default_name,
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.saved_file_path = file_path  # 更新保存路径
    
    def _generate_default_save_name(self) -> str:
        """
        生成默认保存文件名（原名_时间戳）
        
        Returns:
            默认文件名路径
        """
        if self.current_file_path:
            # 获取原文件信息
            dir_path = os.path.dirname(self.current_file_path)
            file_name = os.path.basename(self.current_file_path)
            name_without_ext, ext = os.path.splitext(file_name)
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 组合新文件名
            new_name = f"{name_without_ext}_{timestamp}{ext}"
            return os.path.join(dir_path, new_name)
        else:
            # 如果没有原文件路径，使用默认名称
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"image_{timestamp}.png"
    
    def _save_to_file(self, file_path: str):
        """保存到文件"""
        try:
            save_image(self.image_data, file_path)
            self.current_file_path = file_path
            self.statusbar.showMessage(f"已保存: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存图片:\n{str(e)}")
    
    def _undo(self):
        """撤销"""
        if self.image_data is None:
            return
        
        if self.history_manager.can_undo():
            self.image_data = self.history_manager.undo(self.image_data)
            self.canvas.set_image(self.image_data)
            self.statusbar.showMessage("已撤销")
            self._update_ui_state()
    
    def _redo(self):
        """重做"""
        if self.image_data is None:
            return
        
        if self.history_manager.can_redo():
            self.image_data = self.history_manager.redo()
            self.canvas.set_image(self.image_data)
            self.statusbar.showMessage("已重做")
            self._update_ui_state()
    
    def _on_parameters_changed(self, preprocess_params: dict, method: int, threshold: int):
        """参数改变（预处理或二值化）"""
        if self.image_data is None:
            return
        
        try:
            # 先应用预处理
            preprocessed = BinarizationEngine.apply_preprocess(
                self.image_data.original_pixels.copy(),
                **preprocess_params
            )
            
            # 再应用二值化
            binary_pixels = BinarizationEngine.apply_threshold(
                preprocessed, method, threshold
            )
            
            # 只更新基础图层，保留编辑图层
            self.image_data.update_base_layer(binary_pixels)
            
            # 更新分块缓存
            pixels = self.image_data.get_current_pixels()
            self.canvas.tile_cache.set_image(pixels)
            
            self.canvas.update()
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"图像处理失败:\n{str(e)}")
    
    def _on_image_modified(self):
        """图片被修改"""
        if self.image_data is not None:
            # 保存到历史
            self.history_manager.push_state(self.image_data)
            self._update_ui_state()
    
    def _update_ui_state(self):
        """更新 UI 状态"""
        has_image = self.image_data is not None
        
        # 文件操作
        self.save_action.setEnabled(has_image)
        self.save_as_action.setEnabled(has_image)
        
        # 编辑操作
        self.undo_action.setEnabled(self.history_manager.can_undo())
        self.redo_action.setEnabled(self.history_manager.can_redo())
        
        # 工具
        self.brush_button.setEnabled(has_image)
        self.crop_action.setEnabled(has_image)
        self.selection_tool_action.setEnabled(has_image)
        self.selection_tool_button.setEnabled(has_image)  # 同步选择按钮状态
        
        # 选区操作
        has_selection = (self.image_data is not None and 
                        self.image_data.selection_mask is not None and
                        bool(self.image_data.selection_mask.any()))  # 转换为 Python bool
        self.deselect_action.setEnabled(has_selection)
        self.invert_selection_action.setEnabled(has_image)
        self.select_black_action.setEnabled(has_image)
        self.select_white_action.setEnabled(has_image)
    
    def _fill_selection(self, color: int):
        """
        填充选区
        
        Args:
            color: 填充颜色（0=黑色, 255=白色）
        """
        if self.image_data is None:
            return
        
        # 检查是否有选区
        if not self.canvas.selection_tool.has_selection():
            self.statusbar.showMessage("没有选区，无法填充")
            return
        
        # 获取选区蒙版
        selection_mask = self.canvas.selection_tool.selection_mask
        
        # 检查选区尺寸是否匹配
        if selection_mask.shape != (self.image_data.height, self.image_data.width):
            self.statusbar.showMessage("选区尺寸不匹配，已清除选区")
            self.canvas.selection_tool.clear_selection()
            self.image_data.selection_mask = None
            self.canvas.tile_cache.set_image(self.image_data.get_current_pixels(), None)
            self.canvas.update()
            return
        
        # 开始临时图层（用于编辑）
        self.image_data.start_temp_layer()
        
        # 填充选区到临时图层
        self.image_data.temp_layer[selection_mask] = color
        
        # 标记这些像素为已编辑（关键！）
        self.image_data.temp_edit_mask[selection_mask] = True
        
        # 提交修改到编辑图层
        self.image_data.commit_temp_layer()
        
        # 清除选区（这样才能看到填充效果）
        self.canvas.selection_tool.clear_selection()
        self.image_data.selection_mask = None
        
        # 更新分块缓存（不显示选区）
        pixels = self.image_data.get_current_pixels()
        self.canvas.tile_cache.set_image(pixels, None)
        
        # 保存到历史管理器（支持撤销/重做）
        self.history_manager.push_state(self.image_data)
        
        # 更新 UI 状态
        self._update_ui_state()
        
        # 更新显示
        self.canvas.update()
        
        # 显示提示
        color_name = "黑色" if color == 0 else "白色"
        self.statusbar.showMessage(f"已用{color_name}填充选区")
    
    def _fill_selection_opposite_color(self):
        """
        填充选区为相反颜色
        
        如果目标颜色是黑色（选择黑色区域），则填充白色
        如果目标颜色是白色（选择白色区域），则填充黑色
        """
        target_color = self.canvas.selection_tool.target_color
        # 填充相反的颜色
        fill_color = 255 if target_color == 0 else 0
        self._fill_selection(fill_color)
   
    def _connect_tool_settings(self):
        """连接属性面板中的工具设置信号"""
        # 画笔工具设置
        self.properties_panel.brush_size_spinbox.valueChanged.connect(
            lambda v: setattr(self.canvas.brush_tool, 'size', float(v))
        )
        self.properties_panel.brush_color_group.buttonClicked.connect(
            lambda: setattr(self.canvas.brush_tool, 'color', 
                          self.properties_panel.brush_color_group.checkedId())
        )
        
        # 选择工具设置
        self.properties_panel.selection_size_spinbox.valueChanged.connect(
            self._on_selection_size_changed_panel
        )
        self.properties_panel.selection_mode_group.buttonClicked.connect(
            self._on_selection_mode_changed_panel
        )
        self.properties_panel.selection_color_group.buttonClicked.connect(
            self._on_selection_color_changed_panel
        )
        self.properties_panel.fill_button.clicked.connect(
            self._fill_selection_opposite_color
        )
        self.properties_panel.deselect_button.clicked.connect(self._deselect)
        self.properties_panel.invert_button.clicked.connect(self._invert_selection)
    
    def _on_selection_size_changed_panel(self, value: int):
        """属性面板：选择范围改变"""
        self.canvas.selection_tool.size = float(value)
        self.canvas.update()
    
    def _on_selection_mode_changed_panel(self):
        """属性面板：选择模式改变"""
        button_id = self.properties_panel.selection_mode_group.checkedId()
        mode = 'add' if button_id == 0 else 'subtract'
        self.canvas.selection_tool.selection_mode = mode
        self.canvas.update()
    
    def _on_selection_color_changed_panel(self):
        """属性面板：选择目标颜色改变"""
        button_id = self.properties_panel.selection_color_group.checkedId()
        self.canvas.selection_tool.target_color = button_id
        # 更新填充按钮文本
        if button_id == 0:
            self.properties_panel.fill_button.setText("填充白色")
        else:
            self.properties_panel.fill_button.setText("填充黑色")
        self.canvas.update()