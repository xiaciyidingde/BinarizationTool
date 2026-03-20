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
from ..models.image_data import ImageData
from ..models.history_manager import HistoryManager
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
        self.setGeometry(100, 100, 1200, 800)
        
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
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：二值化面板
        self.binarization_panel = BinarizationPanel()
        self.binarization_panel.setMaximumWidth(300)
        self.binarization_panel.setMinimumWidth(200)
        splitter.addWidget(self.binarization_panel)
        
        # 右侧：Canvas
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Canvas
        self.canvas = Canvas()
        right_layout.addWidget(self.canvas)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
    
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
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)
        
        # 为画笔按钮添加快捷键
        self.brush_shortcut = QAction(self)
        self.brush_shortcut.setShortcut("B")
        self.brush_shortcut.triggered.connect(self._select_brush_tool)
        self.addAction(self.brush_shortcut)
        
        self.crop_action = QAction("裁剪工具 (C)", self)
        self.crop_action.setShortcut("C")
        self.crop_action.setCheckable(True)
        self.crop_action.triggered.connect(self._select_crop_tool)
    
    def create_toolbars(self):
        """创建工具栏"""
        self.toolbar = QToolBar("工具")
        self.toolbar.setMovable(False)
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
        
        # 添加弹性空间，将后续内容推到右边
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # 当前工具显示（右对齐）
        self.current_tool_label = QLabel("当前工具：无")
        self.current_tool_label.setStyleSheet("padding: 0 10px; color: #666;")
        self.toolbar.addWidget(self.current_tool_label)
        
        # 创建画笔设置面板（初始隐藏）
        self._create_brush_settings_panel()
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
    
    def connect_signals(self):
        """连接信号"""
        # 二值化参数改变
        self.binarization_panel.parameters_changed.connect(self._on_parameters_changed)
        
        # Canvas 图片修改
        self.canvas.image_modified.connect(self._on_image_modified)
        
        # Canvas 文件拖放
        self.canvas.file_dropped.connect(self._load_file_from_path)
    
    def _select_brush_tool(self):
        """选择画笔工具"""
        if self.image_data is None:
            self.statusbar.showMessage("请先加载图片")
            return
        
        self.canvas.set_tool(self.canvas.brush_tool)
        self.brush_button.setChecked(True)
        self.crop_action.setChecked(False)
        self.current_tool_label.setText("当前工具：画笔")
        self.statusbar.showMessage("画笔工具已激活")
        
        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()
    
    def _select_crop_tool(self):
        """选择裁剪工具"""
        if self.image_data is None:
            return
        
        self.canvas.set_tool(self.canvas.crop_tool)
        self.brush_button.setChecked(False)
        self.crop_action.setChecked(True)
        self.current_tool_label.setText("当前工具：裁剪")
        self.statusbar.showMessage("裁剪工具已激活")
        
        # 隐藏画笔设置面板
        if hasattr(self, 'brush_settings_panel'):
            self.brush_settings_panel.hide()
    
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
    
    def _create_brush_settings_panel(self):
        """创建画笔设置面板"""
        self.brush_settings_panel = QFrame(self)
        self.brush_settings_panel.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.brush_settings_panel.setAttribute(Qt.WA_TranslucentBackground, False)
        self.brush_settings_panel.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QLabel {
                color: #333;
                font-size: 12px;
                padding: 2px;
                background: transparent;
                border: none;
            }
            QSpinBox {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                min-width: 80px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border: none;
                background-color: #e0e0e0;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #d0d0d0;
            }
            QRadioButton {
                color: #333;
                font-size: 12px;
                spacing: 6px;
                background: transparent;
                border: none;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        # 安装事件过滤器以检测鼠标离开
        self.brush_settings_panel.installEventFilter(self)
        
        layout = QVBoxLayout(self.brush_settings_panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # 大小设置
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel("大小:")
        size_label.setMinimumWidth(40)
        self.brush_size_spinbox = QSpinBox()
        self.brush_size_spinbox.setRange(1, 500)
        self.brush_size_spinbox.setValue(int(self.canvas.brush_tool.size))
        self.brush_size_spinbox.valueChanged.connect(self._on_brush_size_changed)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.brush_size_spinbox)
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        # 颜色设置 - 标题和选项在同一行
        color_layout = QHBoxLayout()
        color_layout.setSpacing(12)
        color_label = QLabel("颜色:")
        color_label.setMinimumWidth(40)
        color_layout.addWidget(color_label)
        
        self.color_button_group = QButtonGroup(self)
        
        self.black_radio = QRadioButton("黑色")
        self.white_radio = QRadioButton("白色")
        
        self.color_button_group.addButton(self.black_radio, 0)
        self.color_button_group.addButton(self.white_radio, 255)
        
        # 设置初始选中状态
        if self.canvas.brush_tool.color == 0:
            self.black_radio.setChecked(True)
        else:
            self.white_radio.setChecked(True)
        
        self.color_button_group.buttonClicked.connect(self._on_brush_color_changed)
        
        color_layout.addWidget(self.black_radio)
        color_layout.addWidget(self.white_radio)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        self.brush_settings_panel.setLayout(layout)
        self.brush_settings_panel.hide()
    
    def _on_brush_size_changed(self, value: int):
        """画笔大小改变"""
        self.canvas.brush_tool.size = float(value)
    
    def _on_brush_color_changed(self):
        """画笔颜色改变"""
        color = self.color_button_group.checkedId()
        self.canvas.brush_tool.color = color
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理画笔按钮和设置面板的悬浮事件"""
        if obj == self.brush_button:
            event_type = event.type()
            
            # 不拦截鼠标点击事件，让按钮正常处理
            if event_type == event.Type.Enter:
                # 鼠标进入画笔按钮 - 延迟显示设置面板，避免干扰点击
                from PySide6.QtCore import QTimer
                if not hasattr(self, '_show_timer'):
                    self._show_timer = QTimer()
                    self._show_timer.setSingleShot(True)
                    self._show_timer.timeout.connect(self._show_brush_settings)
                self._show_timer.start(500)  # 延迟500ms显示
                return False
            elif event_type == event.Type.Leave:
                # 鼠标离开画笔按钮
                if hasattr(self, '_show_timer'):
                    self._show_timer.stop()
                # 延迟检查是否需要隐藏
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._check_hide_brush_settings)
                return False
        
        elif obj == self.brush_settings_panel:
            if event.type() == event.Type.Leave:
                # 鼠标离开设置面板，延迟检查是否需要隐藏
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._check_hide_brush_settings)
                return False
        
        return super().eventFilter(obj, event)
    
    def _check_hide_brush_settings(self):
        """检查是否需要隐藏画笔设置面板"""
        if not hasattr(self, 'brush_settings_panel'):
            return
        
        # 获取鼠标全局位置
        from PySide6.QtGui import QCursor
        mouse_pos = QCursor.pos()
        
        # 检查鼠标是否在按钮或面板区域内
        button_rect = self.brush_button.rect()
        button_global_rect = button_rect.translated(self.brush_button.mapToGlobal(QPoint(0, 0)))
        
        panel_rect = self.brush_settings_panel.rect()
        panel_global_rect = panel_rect.translated(self.brush_settings_panel.pos())
        
        # 如果鼠标不在按钮或面板内，隐藏面板
        if not button_global_rect.contains(mouse_pos) and not panel_global_rect.contains(mouse_pos):
            self.brush_settings_panel.hide()
    
    def _show_brush_settings(self):
        """显示画笔设置面板"""
        if self.image_data is None:
            return
        
        # 更新设置值
        self.brush_size_spinbox.setValue(int(self.canvas.brush_tool.size))
        if self.canvas.brush_tool.color == 0:
            self.black_radio.setChecked(True)
        else:
            self.white_radio.setChecked(True)
        
        # 计算位置（在画笔按钮下方）
        button_pos = self.brush_button.mapToGlobal(QPoint(0, 0))
        panel_x = button_pos.x()
        panel_y = button_pos.y() + self.brush_button.height()
        
        self.brush_settings_panel.move(panel_x, panel_y)
        self.brush_settings_panel.show()
