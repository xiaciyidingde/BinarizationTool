"""
主窗口模块

应用程序的主窗口，包含菜单栏、工具栏和主要布局。
"""

from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                QSplitter, QToolBar, QFileDialog, QMessageBox,
                                QPushButton, QLabel, QStatusBar, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

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
        
        # 模式状态
        self.is_edit_mode = False
        
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
        self.open_action = QAction("打开...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._open_file)
        
        self.save_action = QAction("保存", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_file)
        
        self.save_as_action = QAction("另存为...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self._save_file_as)
        
        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # 编辑菜单动作
        self.undo_action = QAction("← 后退", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setToolTip("后退到上一步 (Ctrl+Z)")
        self.undo_action.triggered.connect(self._undo)
        
        self.redo_action = QAction("前进 →", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setToolTip("前进到下一步 (Ctrl+Y)")
        self.redo_action.triggered.connect(self._redo)
        
        # 工具动作
        self.brush_action = QAction("画笔工具", self)
        self.brush_action.setShortcut("B")
        self.brush_action.setCheckable(True)
        self.brush_action.triggered.connect(self._select_brush_tool)
        
        self.crop_action = QAction("裁剪工具", self)
        self.crop_action.setShortcut("C")
        self.crop_action.setCheckable(True)
        self.crop_action.triggered.connect(self._select_crop_tool)
    
    def create_toolbars(self):
        """创建工具栏"""
        toolbar = QToolBar("工具")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 文件操作
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        
        # 编辑操作 - 后退/前进
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        
        # 工具选择
        toolbar.addAction(self.brush_action)
        toolbar.addAction(self.crop_action)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # 模式切换按钮和标签
        self.mode_label = QLabel("当前模式: 预览模式")
        self.mode_label.setStyleSheet("padding: 0 10px;")
        toolbar.addWidget(self.mode_label)
        
        self.mode_button = QPushButton("进入编辑模式")
        self.mode_button.setCheckable(True)
        self.mode_button.clicked.connect(self._toggle_mode)
        toolbar.addWidget(self.mode_button)
    
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
    
    def _toggle_mode(self):
        """切换预览/编辑模式"""
        self.is_edit_mode = not self.is_edit_mode
        
        if self.is_edit_mode:
            # 进入编辑模式
            self.mode_button.setText("退出编辑模式")
            self.mode_label.setText("当前模式: 编辑模式")
            self.binarization_panel.set_enabled(False)
            
            # 默认选择画笔工具
            self._select_brush_tool()
        else:
            # 返回预览模式
            self.mode_button.setText("进入编辑模式")
            self.mode_label.setText("当前模式: 预览模式")
            self.binarization_panel.set_enabled(True)
            
            # 取消工具选择
            self.canvas.set_tool(None)
            self.brush_action.setChecked(False)
            self.crop_action.setChecked(False)
        
        self._update_ui_state()
    
    def _select_brush_tool(self):
        """选择画笔工具"""
        if not self.is_edit_mode:
            return
        
        self.canvas.set_tool(self.canvas.brush_tool)
        self.brush_action.setChecked(True)
        self.crop_action.setChecked(False)
        self.statusbar.showMessage("画笔工具已激活")
    
    def _select_crop_tool(self):
        """选择裁剪工具"""
        if not self.is_edit_mode:
            return
        
        self.canvas.set_tool(self.canvas.crop_tool)
        self.brush_action.setChecked(False)
        self.crop_action.setChecked(True)
        self.statusbar.showMessage("裁剪工具已激活")
    
    def _open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*.*)"
        )
        
        if file_path:
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
                
                # 更新状态
                self.statusbar.showMessage(f"已加载: {file_path}")
                self._update_ui_state()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载图片:\n{str(e)}")
    
    def _save_file(self):
        """保存文件"""
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        """另存为"""
        if self.image_data is None:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            "",
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        
        if file_path:
            self._save_to_file(file_path)
    
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
        if self.image_data is None or self.is_edit_mode:
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
            
            # 更新图片数据
            self.image_data.pixels = binary_pixels
            self.canvas.cache_valid = False
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
        
        # 模式切换
        self.mode_button.setEnabled(has_image)
        
        # 工具
        self.brush_action.setEnabled(has_image and self.is_edit_mode)
        self.crop_action.setEnabled(has_image and self.is_edit_mode)
