"""
主窗口模块

应用程序的主窗口，包含菜单栏、工具栏和主要布局。
"""

import os
from datetime import datetime

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..models.history_manager import HistoryManager
from ..models.image_data import ImageData
from ..utils.binarization_engine import BinarizationEngine
from ..utils.binarization_worker import BinarizationWorker
from ..utils.config_manager import get_config_manager
from ..utils.file_io import load_image, save_image
from ..utils.preprocess_worker import PreprocessWorker
from ..utils.theme_manager import ThemeManager
from ..utils.translation_manager import get_translator
from .binarization_panel import BinarizationPanel
from .canvas import Canvas
from .shortcut_handler import ShortcutHandler


class MainWindow(QMainWindow):
    """
    主窗口类

    管理应用程序的整体布局和功能集成。
    """

    # 布局常量
    LEFT_PANEL_WIDTH = 300  # 左侧二值化面板宽度
    RIGHT_PANEL_WIDTH = 250  # 右侧属性面板宽度
    CANVAS_MIN_WIDTH = 400  # 画布最小宽度

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 配置管理器
        self.config_manager = get_config_manager()

        # 翻译管理器
        self.tr = get_translator()

        # 主题管理器
        self.theme_manager = ThemeManager()

        # 数据
        self.image_data: ImageData | None = None
        self.history_manager = HistoryManager()
        self.current_file_path: str | None = None
        self.saved_file_path: str | None = None  # 记录已保存的文件路径
        
        # 图层管理
        self.active_layer_id: str = "root"  # 当前激活的图层ID
        
        # 保存上一次的参数值（用于非根图层时恢复）
        self.last_valid_params: dict | None = None

        # 异步二值化
        self.binarization_worker: BinarizationWorker | None = None
        self.pending_binarization_params: tuple | None = None  # (preprocess_params, method, threshold, method_params)
        self.binarization_debounce_timer = QTimer()
        self.binarization_debounce_timer.setSingleShot(True)
        self.binarization_debounce_timer.timeout.connect(self._start_binarization)

        # 异步预处理
        self.preprocess_worker: PreprocessWorker | None = None
        self.pending_preprocess_params: dict | None = None
        self.preprocess_debounce_timer = QTimer()
        self.preprocess_debounce_timer.setSingleShot(True)
        self.preprocess_debounce_timer.timeout.connect(self._start_preprocess)

        # 从配置加载防抖延迟
        debounce_delay = self.config_manager.get('performance', 'debounce_delay', 150)
        self.binarization_debounce_timer.setInterval(debounce_delay)
        self.preprocess_debounce_timer.setInterval(debounce_delay)

        # 设置窗口
        self.setWindowTitle(self.tr.tr('app.title'))
        self.setGeometry(100, 100, 1550, 800)  # 宽度从 1450 增加到 1550
        
        # 应用深色标题栏（Windows 11）
        self._apply_dark_titlebar()

        # 创建 UI
        self.setup_ui()
        self.create_actions()
        self.create_toolbars()
        self.create_statusbar()

        # 设置全局 QToolTip 样式
        self.setStyleSheet("""
            QToolTip {
                background-color: #ffffff;
                color: #212529;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """)

        # 连接信号
        self.connect_signals()

        # 应用配置
        self.apply_config()

        # 初始状态
        self._update_ui_state()

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        # 清理 Canvas 的线程资源
        if hasattr(self, 'canvas') and self.canvas is not None:
            self.canvas.cleanup()
        
        # 停止防抖定时器
        if self.binarization_debounce_timer.isActive():
            self.binarization_debounce_timer.stop()
        if self.preprocess_debounce_timer.isActive():
            self.preprocess_debounce_timer.stop()

        # 取消并等待后台线程完成
        if self.binarization_worker is not None and self.binarization_worker.isRunning():
            self.binarization_worker.cancel()
            self.binarization_worker.wait(1000)  # 最多等待1秒

        if self.preprocess_worker is not None and self.preprocess_worker.isRunning():
            self.preprocess_worker.cancel()
            self.preprocess_worker.wait(1000)  # 最多等待1秒

        # 接受关闭事件
        event.accept()

    def _apply_dark_titlebar(self):
        """应用深色标题栏（Windows 11）"""
        import sys
        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes import wintypes
                
                # 获取当前主题
                theme = self.config_manager.get('interface', 'theme', 'light')
                
                # 如果是跟随系统，检测系统主题
                if theme == 'system':
                    from ..utils.theme_manager import ThemeManager
                    theme_manager = ThemeManager()
                    theme = theme_manager._detect_system_theme()
                
                # Windows 11 标题栏颜色
                hwnd = int(self.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                
                # 根据主题设置标题栏颜色：1 = 深色, 0 = 浅色
                value = ctypes.c_int(1 if theme == 'dark' else 0)
                
                # 尝试调用 DwmSetWindowAttribute
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_USE_IMMERSIVE_DARK_MODE,
                        ctypes.byref(value),
                        ctypes.sizeof(value)
                    )
                except Exception:
                    pass  # 如果失败（比如 Windows 10），静默忽略
            except Exception:
                pass  # 非 Windows 系统或其他错误，静默忽略

    def _apply_dark_titlebar_to_dialog(self, dialog):
        """为对话框应用标题栏颜色（Windows 11）"""
        import sys
        if sys.platform == 'win32':
            try:
                import ctypes
                
                # 获取当前主题
                theme = self.config_manager.get('interface', 'theme', 'light')
                
                # 如果是跟随系统，检测系统主题
                if theme == 'system':
                    from ..utils.theme_manager import ThemeManager
                    theme_manager = ThemeManager()
                    theme = theme_manager._detect_system_theme()
                
                # 确保对话框已经创建窗口句柄
                dialog.show()
                dialog.hide()
                
                hwnd = int(dialog.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                # 根据主题设置标题栏颜色：1 = 深色, 0 = 浅色
                value = ctypes.c_int(1 if theme == 'dark' else 0)
                
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_USE_IMMERSIVE_DARK_MODE,
                        ctypes.byref(value),
                        ctypes.sizeof(value)
                    )
                except Exception:
                    pass
            except Exception:
                pass

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
        main_splitter.setHandleWidth(0)  # 设置分隔条宽度为 0
        main_splitter.setChildrenCollapsible(False)  # 禁止折叠

        # 左侧：二值化面板
        self.binarization_panel = BinarizationPanel(panel_width=self.LEFT_PANEL_WIDTH)
        self.binarization_panel.setMinimumWidth(self.LEFT_PANEL_WIDTH)
        self.binarization_panel.setMaximumWidth(self.LEFT_PANEL_WIDTH)
        main_splitter.addWidget(self.binarization_panel)

        # 中右部分：Canvas + 属性面板
        center_right_splitter = QSplitter(Qt.Horizontal)
        center_right_splitter.setHandleWidth(1)  # 设置分隔条宽度
        center_right_splitter.setChildrenCollapsible(False)

        # 中间：Canvas
        self.canvas = Canvas()
        self.canvas.setMinimumWidth(self.CANVAS_MIN_WIDTH)
        center_right_splitter.addWidget(self.canvas)

        # 右侧：属性面板
        # 右侧：属性面板
        from .properties_panel import PropertiesPanel
        self.properties_panel = PropertiesPanel()
        self.properties_panel.setMinimumWidth(self.RIGHT_PANEL_WIDTH)
        self.properties_panel.setMaximumWidth(self.RIGHT_PANEL_WIDTH)
        center_right_splitter.addWidget(self.properties_panel)
        # 设置中右分割器比例（重要：让画布优先占用空间）
        center_right_splitter.setStretchFactor(0, 3)  # Canvas 高优先级伸缩
        center_right_splitter.setStretchFactor(1, 0)  # 属性面板固定

        main_splitter.addWidget(center_right_splitter)

        # 设置主分割器比例
        main_splitter.setStretchFactor(0, 0)  # 左侧面板固定
        main_splitter.setStretchFactor(1, 4)  # 中右部分高优先级伸缩

        # 设置初始大小比例
        main_splitter.setSizes([self.LEFT_PANEL_WIDTH, 1000])

        # 禁用左侧面板的拖动（通过设置固定宽度已经实现）
        main_splitter.handle(1).setEnabled(False)  # 禁用第一个分隔条

        main_layout.addWidget(main_splitter)

    def create_actions(self):
        """创建动作"""
        # 文件菜单动作
        self.open_action = QAction(self.tr.tr('toolbar.open'), self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setToolTip(self.tr.tr('tooltip.open'))
        self.open_action.triggered.connect(self._open_file)
        self.addAction(self.open_action)

        self.save_action = QAction(self.tr.tr('toolbar.save'), self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setToolTip(self.tr.tr('tooltip.save'))
        self.save_action.triggered.connect(self._save_file)
        self.addAction(self.save_action)

        self.save_as_action = QAction(self.tr.tr('menu.save_as'), self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.setToolTip(self.tr.tr('tooltip.save_as'))
        self.save_as_action.triggered.connect(self._save_file_as)
        self.addAction(self.save_as_action)

        self.exit_action = QAction(self.tr.tr('menu.exit'), self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setToolTip(self.tr.tr('tooltip.exit'))
        self.exit_action.triggered.connect(self.close)
        self.addAction(self.exit_action)

        # 编辑菜单动作
        self.undo_action = QAction(self.tr.tr('toolbar.undo'), self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setToolTip(self.tr.tr('tooltip.undo'))
        self.undo_action.triggered.connect(self._undo)
        self.addAction(self.undo_action)

        self.redo_action = QAction(self.tr.tr('toolbar.redo'), self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setToolTip(self.tr.tr('tooltip.redo'))
        self.redo_action.triggered.connect(self._redo)
        self.addAction(self.redo_action)

        self.reset_action = QAction(self.tr.tr('toolbar.reset'), self)
        self.reset_action.setShortcut("Ctrl+R")
        self.reset_action.setToolTip(self.tr.tr('tooltip.reset'))
        self.reset_action.triggered.connect(self._reset_to_initial)
        self.addAction(self.reset_action)

        # 工具动作 - 创建自定义按钮以支持悬浮事件
        self.brush_button = QPushButton(self.tr.tr('toolbar.brush'))
        self.brush_button.setCheckable(True)
        self.brush_button.setFlat(True)
        self.brush_button.setToolTip(self.tr.tr('tooltip.brush_tool'))
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)

        # 为画笔按钮添加快捷键
        self.brush_shortcut = QAction(self)
        self.brush_shortcut.setShortcut("B")
        self.brush_shortcut.triggered.connect(self._select_brush_tool)
        self.addAction(self.brush_shortcut)

        # 初始化快捷键处理器
        self.shortcut_handler = ShortcutHandler(self)

        # 抓取工具动作
        self.pan_action = QAction(self.tr.tr('toolbar.pan'), self)
        self.pan_action.setShortcut("H")
        self.pan_action.setCheckable(True)
        self.pan_action.setToolTip(self.tr.tr('tooltip.pan_tool'))
        self.pan_action.triggered.connect(self._select_pan_tool)
        self.addAction(self.pan_action)

        self.crop_action = QAction(self.tr.tr('toolbar.crop'), self)
        self.crop_action.setShortcut("C")
        self.crop_action.setCheckable(True)
        self.crop_action.setToolTip(self.tr.tr('tooltip.crop_tool'))
        self.crop_action.triggered.connect(self._select_crop_tool)
        self.addAction(self.crop_action)

        # 选择工具动作
        self.selection_tool_action = QAction(self.tr.tr('toolbar.selection'), self)
        self.selection_tool_action.setShortcut("W")
        self.selection_tool_action.setCheckable(True)
        self.selection_tool_action.setToolTip(self.tr.tr('tooltip.selection_tool'))
        self.selection_tool_action.triggered.connect(self._select_selection_tool)
        self.addAction(self.selection_tool_action)

        # 选区菜单动作
        self.deselect_action = QAction(self.tr.tr('tooltip.deselect'), self)
        self.deselect_action.setShortcut("Ctrl+D")
        self.deselect_action.triggered.connect(self._deselect)
        self.addAction(self.deselect_action)

        self.invert_selection_action = QAction(self.tr.tr('tooltip.invert_selection'), self)
        self.invert_selection_action.setShortcut("Ctrl+Shift+I")
        self.invert_selection_action.triggered.connect(self._invert_selection)
        self.addAction(self.invert_selection_action)

        self.select_black_action = QAction(self.tr.tr('menu.select_black'), self)
        self.select_black_action.triggered.connect(lambda: self._select_by_color(0))

        self.select_white_action = QAction(self.tr.tr('menu.select_white'), self)
        self.select_white_action.triggered.connect(lambda: self._select_by_color(255))

    def create_toolbars(self):
        """创建工具栏"""
        self.toolbar = QToolBar(self.tr.tr('toolbar.title'))
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)  # 禁用右键菜单

        # 创建工具栏容器
        toolbar_container = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(8)

        # 创建按钮辅助函数
        def create_toolbar_button(text, tooltip, checkable=False):
            btn = QPushButton(text)
            btn.setCheckable(checkable)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(28)
            btn.setMaximumHeight(28)
            return btn

        # 创建按钮组容器辅助函数
        def create_button_group():
            group = QFrame()
            group.setObjectName("toolbarButtonGroup")
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(3, 1, 3, 1)
            group_layout.setSpacing(0)
            return group, group_layout
            group_layout.setSpacing(0)
            return group, group_layout

        # 文件操作组
        file_group, file_layout = create_button_group()
        open_btn = create_toolbar_button(self.tr.tr('toolbar.open'), self.tr.tr('tooltip.open'))
        open_btn.clicked.connect(self._open_file)
        file_layout.addWidget(open_btn)

        save_btn = create_toolbar_button(self.tr.tr('toolbar.save'), self.tr.tr('tooltip.save'))
        save_btn.clicked.connect(self._save_file)
        file_layout.addWidget(save_btn)
        self.save_action_btn = save_btn
        toolbar_layout.addWidget(file_group)

        # 编辑操作组
        edit_group, edit_layout = create_button_group()
        undo_btn = create_toolbar_button(self.tr.tr('toolbar.undo'), self.tr.tr('tooltip.undo'))
        undo_btn.clicked.connect(self._undo)
        edit_layout.addWidget(undo_btn)
        self.undo_action_btn = undo_btn

        redo_btn = create_toolbar_button(self.tr.tr('toolbar.redo'), self.tr.tr('tooltip.redo'))
        redo_btn.clicked.connect(self._redo)
        edit_layout.addWidget(redo_btn)
        self.redo_action_btn = redo_btn

        reset_btn = create_toolbar_button(self.tr.tr('toolbar.reset'), self.tr.tr('tooltip.reset'))
        reset_btn.clicked.connect(self._reset_to_initial)
        edit_layout.addWidget(reset_btn)
        self.reset_action_btn = reset_btn
        toolbar_layout.addWidget(edit_group)

        # 工具选择组
        tool_group, tool_layout = create_button_group()
        self.pan_button = create_toolbar_button(self.tr.tr('toolbar.pan'), self.tr.tr('tooltip.pan_tool'), checkable=True)
        self.pan_button.clicked.connect(self._select_pan_tool)
        tool_layout.addWidget(self.pan_button)

        self.brush_button = create_toolbar_button(self.tr.tr('toolbar.brush'), self.tr.tr('tooltip.brush_tool'), checkable=True)
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)
        tool_layout.addWidget(self.brush_button)

        self.crop_button = create_toolbar_button(self.tr.tr('toolbar.crop'), self.tr.tr('tooltip.crop_tool'), checkable=True)
        self.crop_button.clicked.connect(self._select_crop_tool)
        tool_layout.addWidget(self.crop_button)

        self.selection_tool_button = create_toolbar_button(self.tr.tr('toolbar.selection'), self.tr.tr('tooltip.selection_tool'), checkable=True)
        self.selection_tool_button.setEnabled(False)
        self.selection_tool_button.clicked.connect(self._select_selection_tool)
        self.selection_tool_button.installEventFilter(self)
        tool_layout.addWidget(self.selection_tool_button)
        toolbar_layout.addWidget(tool_group)

        # 添加弹性空间
        toolbar_layout.addStretch()

        # 应用操作组（设置、关于）
        app_group, app_layout = create_button_group()
        settings_btn = create_toolbar_button(self.tr.tr('toolbar.settings'), self.tr.tr('settings.title'))
        settings_btn.clicked.connect(self._show_settings)
        app_layout.addWidget(settings_btn)

        about_btn = create_toolbar_button(self.tr.tr('toolbar.about'), self.tr.tr('about.title', app_name='BinarizationTool'))
        about_btn.clicked.connect(self._show_about)
        app_layout.addWidget(about_btn)
        toolbar_layout.addWidget(app_group)

        # 当前工具显示
        self.current_tool_label = QLabel(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
        self.current_tool_label.setObjectName("currentToolLabel")
        self.current_tool_label.setStyleSheet("padding: 0 10px; font-size: 14px; font-weight: 500;")
        toolbar_layout.addWidget(self.current_tool_label)

        # 将容器添加到工具栏
        self.addToolBar(self.toolbar)
        self.toolbar.addWidget(toolbar_container)

    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(self.tr.tr('app.ready'))

        # 创建菜单栏（但隐藏，功能通过工具栏和快捷键访问）
        self._create_menus()
        self.menuBar().hide()  # 隐藏菜单栏

    def connect_signals(self):
        """连接信号"""
        # 二值化参数改变
        self.binarization_panel.parameters_changed.connect(self._on_parameters_changed)

        # 视图模式切换
        self.binarization_panel.view_mode_changed.connect(self._on_view_mode_changed)

        # Canvas 图片修改
        self.canvas.image_modified.connect(self._on_image_modified)

        # Canvas 文件拖放
        self.canvas.file_dropped.connect(self._load_file_from_path)

        # Canvas 缩放变化
        self.canvas.zoom_changed.connect(self.properties_panel.set_zoom_level)

        # 属性面板工具设置信号
        self._connect_tool_settings()
        
        # 图层面板信号
        self.properties_panel.layers_panel.layer_selected.connect(self._on_layer_selected)
        self.properties_panel.layers_panel.save_selection_clicked.connect(self._on_save_selection_as_layer)
        self.properties_panel.layers_panel.layer_deleted.connect(self._on_layer_deleted)
        self.properties_panel.layers_panel.merge_layers_clicked.connect(self._on_merge_layers)
    
    def _on_layer_selected(self, layer_id: str):
        """
        图层被选中
        
        Args:
            layer_id: 图层ID
        """
        self.active_layer_id = layer_id
        
        # 清除当前选区
        if self.image_data is not None:
            self.image_data.clear_selection()
        
        # 如果选中的是用户图层，只显示该图层的选中区域
        if layer_id != "root" and self.image_data is not None:
            # 查找对应的图层
            for layer in self.image_data.user_layers:
                if layer.id == layer_id:
                    # 创建灰色背景（128），表示未选中区域
                    composited = np.full(
                        (self.image_data.height, self.image_data.width),
                        128,  # 灰色背景
                        dtype=np.uint8
                    )
                    
                    # 只在选中区域显示图层内容
                    x, y, w, h = layer.bbox
                    composited[y:y+h, x:x+w][layer.mask] = layer.pixels[layer.mask]
                    
                    # 更新画布显示 - 强制清除缓存
                    self.canvas.tile_cache.clear()
                    self.canvas.tile_cache.set_image(composited, None)
                    
                    # 更新二值化面板显示当前图层
                    self.binarization_panel.set_current_layer(layer.name)
                    
                    # 加载该图层的二值化参数
                    if layer.binarization_params:
                        self.binarization_panel.load_params(layer.binarization_params)
                    
                    self.statusbar.showMessage(f"已切换到图层: {layer.name}")
                    break
        else:
            # 根图层，合成显示根图层 + 编辑层 + 所有用户图层
            if self.image_data is not None:
                composited_pixels = self._composite_layers()
                self.canvas.tile_cache.set_image(
                    composited_pixels,
                    self.image_data.selection_mask
                )
            
            # 更新二值化面板显示根图层
            self.binarization_panel.set_current_layer(
                self.tr.tr('binarization_panel.root_layer')
            )
            
            # 加载根图层的参数（当前参数）
            # 根图层使用全局参数，不需要特别加载
            
            self.statusbar.showMessage("已切换到根图层")
        
        # 更新工具状态（非根图层禁用编辑工具）
        self._update_tool_states()
        
        # 更新画布显示
        self.canvas.update()
    
    def _on_save_selection_as_layer(self):
        """保存选区为图层"""
        if self.image_data is None:
            return
        
        # 检查是否有选区
        if not self.image_data.has_selection():
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.warning'),
                self.tr.tr('layers_panel.no_selection_warning')
            )
            return
        
        try:
            # 提取选区数据
            layer_data = self._extract_layer_from_selection()
            
            # 获取当前二值化参数
            current_params = self.binarization_panel.get_all_params()
            
            # 创建图层对象
            from src.models.user_layer import UserLayer
            layer_count = len(self.image_data.user_layers) + 1
            layer_name = self.tr.tr('layers_panel.layer_name_default', number=layer_count)
            
            layer = UserLayer(
                name=layer_name,
                pixels=layer_data['pixels'],
                mask=layer_data['mask'],
                bbox=layer_data['bbox'],
                binarization_params=current_params,  # 保存二值化参数
                original_region=layer_data['original_region']  # 保存原图区域
            )
            
            # 添加到图层列表
            self.image_data.user_layers.append(layer)
            
            # 更新UI
            self.properties_panel.layers_panel.add_layer(layer.id, layer.name)
            
            # 清除选区（包括红色覆盖层）
            self.image_data.clear_selection()
            self.canvas.selection_tool.clear_selection()
            
            # 更新 tile cache 以清除红色选区显示
            self._safe_update_tile_cache(None)
            
            # 保存到历史
            self.history_manager.push_state(self.image_data)
            
            # 更新 UI 状态
            self._update_ui_state()
            
            # 显示成功消息
            self.statusbar.showMessage(self.tr.tr('layers_panel.layer_saved', name=layer_name))
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr.tr('dialog.error'),
                f"保存图层失败：{str(e)}"
            )
    
    def _on_layer_deleted(self, layer_id: str):
        """
        删除图层
        
        Args:
            layer_id: 要删除的图层ID
        """
        if self.image_data is None:
            return
        
        # 不能删除根图层
        if layer_id == "root":
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.warning'),
                self.tr.tr('layers_panel.cannot_delete_root')
            )
            return
        
        # 查找并删除图层
        layer_to_delete = None
        for i, layer in enumerate(self.image_data.user_layers):
            if layer.id == layer_id:
                layer_to_delete = layer
                del self.image_data.user_layers[i]
                break
        
        if layer_to_delete is None:
            return
        
        # 从UI中移除
        self.properties_panel.layers_panel.remove_layer(layer_id)
        
        # 如果删除的是当前激活的图层，切换到根图层
        if self.active_layer_id == layer_id:
            self.active_layer_id = "root"
            self.properties_panel.layers_panel.set_active_layer("root")
            self._on_layer_selected("root")
        else:
            # 更新显示（如果在根图层，需要重新合成）
            if self.active_layer_id == "root":
                self._safe_update_tile_cache(self.image_data.selection_mask)
        
        # 保存到历史
        self.history_manager.push_state(self.image_data)
        
        # 显示成功消息
        self.statusbar.showMessage(self.tr.tr('layers_panel.layer_deleted', name=layer_to_delete.name))
    
    def _on_merge_layers(self, layer_ids: list):
        """
        合并多个图层
        
        Args:
            layer_ids: 要合并的图层ID列表
        """
        if self.image_data is None or len(layer_ids) < 2:
            return
        
        # 过滤掉根图层
        user_layer_ids = [lid for lid in layer_ids if lid != "root"]
        if len(user_layer_ids) < 2:
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.warning'),
                self.tr.tr('layers_panel.need_two_layers')
            )
            return
        
        try:
            # 查找要合并的图层
            layers_to_merge = []
            for layer in self.image_data.user_layers:
                if layer.id in user_layer_ids:
                    layers_to_merge.append(layer)
            
            if len(layers_to_merge) < 2:
                return
            
            # 提取图层名称中的最小编号
            import re
            min_number = None
            for layer in layers_to_merge:
                # 尝试从图层名称中提取数字（如"图层 1" -> 1）
                match = re.search(r'\d+', layer.name)
                if match:
                    number = int(match.group())
                    if min_number is None or number < min_number:
                        min_number = number
            
            # 如果没有找到编号，使用当前图层总数+1
            if min_number is None:
                min_number = len(self.image_data.user_layers) - len(layers_to_merge) + 1
            
            # 生成合并后的图层名称
            merged_layer_name = self.tr.tr('layers_panel.layer_name_default', number=min_number)
            
            # 计算合并后的边界框
            min_x = min(layer.bbox[0] for layer in layers_to_merge)
            min_y = min(layer.bbox[1] for layer in layers_to_merge)
            max_x = max(layer.bbox[0] + layer.bbox[2] for layer in layers_to_merge)
            max_y = max(layer.bbox[1] + layer.bbox[3] for layer in layers_to_merge)
            
            merged_width = max_x - min_x
            merged_height = max_y - min_y
            merged_bbox = (min_x, min_y, merged_width, merged_height)
            
            # 创建合并后的像素和掩码
            merged_pixels = np.full((merged_height, merged_width), 255, dtype=np.uint8)
            merged_mask = np.zeros((merged_height, merged_width), dtype=bool)
            
            # 按顺序叠加所有图层
            for layer in layers_to_merge:
                x, y, w, h = layer.bbox
                # 计算在合并图层中的相对位置
                rel_x = x - min_x
                rel_y = y - min_y
                
                # 复制黑色像素
                black_mask = layer.mask & (layer.pixels == 0)
                merged_pixels[rel_y:rel_y+h, rel_x:rel_x+w][black_mask] = 0
                
                # 更新掩码
                merged_mask[rel_y:rel_y+h, rel_x:rel_x+w] |= layer.mask
            
            # 创建新图层
            from src.models.user_layer import UserLayer
            merged_layer = UserLayer(
                name=merged_layer_name,
                pixels=merged_pixels,
                mask=merged_mask,
                bbox=merged_bbox
            )
            
            # 删除原图层
            for layer in layers_to_merge:
                self.image_data.user_layers.remove(layer)
                self.properties_panel.layers_panel.remove_layer(layer.id)
            
            # 添加合并后的图层
            self.image_data.user_layers.append(merged_layer)
            self.properties_panel.layers_panel.add_layer(merged_layer.id, merged_layer.name)
            
            # 切换到合并后的图层
            self.active_layer_id = merged_layer.id
            self.properties_panel.layers_panel.set_active_layer(merged_layer.id)
            self._on_layer_selected(merged_layer.id)
            
            # 保存到历史
            self.history_manager.push_state(self.image_data)
            
            # 显示成功消息
            self.statusbar.showMessage(self.tr.tr('layers_panel.layers_merged'))
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr.tr('dialog.error'),
                f"合并图层失败：{str(e)}"
            )
    
    def _extract_layer_from_selection(self) -> dict:
        """
        从选区提取图层数据
        
        只保存选中的像素，未选中的区域不存储（通过mask控制）
        同时保存原图对应区域，用于重新二值化
        
        Returns:
            包含 pixels, mask, bbox, original_region 的字典
        """
        # 获取选区掩码
        selection_mask = self.image_data.selection_mask
        
        # 获取当前合成后的像素（包括根图层+编辑层+所有用户图层）
        composited_pixels = self._composite_layers()
        
        # 计算边界框
        y_indices, x_indices = np.where(selection_mask)
        if len(y_indices) == 0 or len(x_indices) == 0:
            raise ValueError("选区为空")
        
        x_min, x_max = x_indices.min(), x_indices.max()
        y_min, y_max = y_indices.min(), y_indices.max()
        bbox = (int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1))
        
        # 裁剪到边界框
        layer_mask = selection_mask[y_min:y_max+1, x_min:x_max+1].copy()
        
        # 只复制选中区域的像素，未选中区域填充白色（255，表示透明）
        # 合成时白色像素不会覆盖底层
        layer_pixels = np.full((y_max - y_min + 1, x_max - x_min + 1), 255, dtype=np.uint8)
        layer_pixels[layer_mask] = composited_pixels[y_min:y_max+1, x_min:x_max+1][layer_mask]
        
        # 提取原图对应区域（用于重新二值化）
        original_region = self.image_data.original_pixels[y_min:y_max+1, x_min:x_max+1].copy()
        
        return {
            'pixels': layer_pixels,
            'mask': layer_mask,  # mask标记哪些像素是有效的
            'bbox': bbox,
            'original_region': original_region  # 原图区域
        }
    
    def _composite_layers(self) -> np.ndarray:
        """
        合成根图层、编辑层和所有用户图层
        
        Returns:
            合成后的像素数据
        """
        # 从根图层开始（当前二值化结果）
        composited = self.image_data.pixels.copy()
        
        # 应用编辑层（画笔痕迹）
        if self.image_data.edit_mask is not None and self.image_data.edit_mask.any():
            composited[self.image_data.edit_mask] = self.image_data.edit_values[self.image_data.edit_mask]
        
        # 按顺序叠加所有用户图层
        for layer in self.image_data.user_layers:
            if not layer.visible:
                continue
            
            # 获取图层的边界框
            x, y, w, h = layer.bbox
            
            # 获取图层的像素和掩码
            layer_pixels = layer.pixels
            layer_mask = layer.mask
            
            # 只覆盖mask为True的像素（选中的区域）
            # 未选中的区域（mask为False）保持透明，不覆盖底层
            composited[y:y+h, x:x+w][layer_mask] = layer_pixels[layer_mask]
        
        return composited

    def _create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu(self.tr.tr('menu.file'))
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu(self.tr.tr('menu.edit'))
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        # 选择菜单
        select_menu = menubar.addMenu(self.tr.tr('menu.select'))
        select_menu.addAction(self.deselect_action)
        select_menu.addAction(self.invert_selection_action)
        select_menu.addSeparator()
        select_menu.addAction(self.select_black_action)
        select_menu.addAction(self.select_white_action)

    def _select_pan_tool(self):
        """选择抓取工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return

        self.canvas.set_tool(self.canvas.pan_tool)
        self.pan_button.setChecked(True)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.pan')))
        self.statusbar.showMessage(self.tr.tr('message.pan_activated'))

        # 隐藏所有工具设置（抓取工具没有设置）
        self.properties_panel.hide_all_tool_settings()

        # 确保 Canvas 获得焦点
        self.canvas.setFocus()

    def _select_brush_tool(self):
        """选择画笔工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return

        self.canvas.set_tool(self.canvas.brush_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(True)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.brush')))
        self.statusbar.showMessage(self.tr.tr('message.brush_activated'))

        # 显示画笔工具设置
        self.properties_panel.show_brush_settings()

        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()

    def _select_crop_tool(self):
        """选择裁剪工具"""
        if self.image_data is None:
            return

        self.canvas.set_tool(self.canvas.crop_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(True)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.crop')))
        self.statusbar.showMessage(self.tr.tr('message.crop_activated'))

        # 隐藏所有工具设置（裁剪工具没有设置）
        self.properties_panel.hide_all_tool_settings()

    def _select_selection_tool(self):
        """选择选择工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return

        self.canvas.set_tool(self.canvas.selection_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(True)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.selection')))
        mode_text = self.tr.tr('mode.add') if self.canvas.selection_tool.selection_mode == 'add' else self.tr.tr('mode.subtract')
        self.statusbar.showMessage(self.tr.tr('message.selection_activated', mode=mode_text))

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
        self._safe_update_tile_cache(None)
        
        # 清除轮廓显示
        self.canvas.selection_border_renderer.update_contours(
            None,
            dirty_rect=None,
            view_scale=self.canvas.view_transform.scale
        )

        # 保存到历史管理器
        self.history_manager.push_state(self.image_data)

        self._update_ui_state()  # 更新 UI 状态
        self.canvas.update()  # 触发重绘
        self.statusbar.showMessage(self.tr.tr('message.deselected'))

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
        self._safe_update_tile_cache(self.image_data.selection_mask)
        
        # 更新轮廓显示
        self.canvas.selection_border_renderer.update_contours(
            self.image_data.selection_mask,
            dirty_rect=None,
            view_scale=self.canvas.view_transform.scale
        )

        # 保存到历史管理器（重要！）
        self.history_manager.push_state(self.image_data)

        self._update_ui_state()  # 更新 UI 状态
        self.canvas.update()  # 触发重绘
        self.statusbar.showMessage(self.tr.tr('message.inverted'))

    def _select_by_color(self, color: int):
        """按颜色选择"""
        if self.image_data is None:
            return

        self.canvas.selection_tool.select_by_color(self.image_data, color)
        self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
        # 更新分块缓存以显示选区
        self._safe_update_tile_cache(self.image_data.selection_mask)
        
        # 更新轮廓显示
        self.canvas.selection_border_renderer.update_contours(
            self.image_data.selection_mask,
            dirty_rect=None,
            view_scale=self.canvas.view_transform.scale
        )

        # 保存到历史管理器（重要！）
        self.history_manager.push_state(self.image_data)

        self._update_ui_state()  # 更新 UI 状态
        self.canvas.update()  # 触发重绘
        color_name = self.tr.tr('color.black') if color == 0 else self.tr.tr('color.white')
        self.statusbar.showMessage(self.tr.tr('message.selected_color', color=color_name))

    def _open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr.tr('file_dialog.open_image'),
            "",
            self.tr.tr('file_dialog.image_files')
        )

        if file_path:
            self._load_file_from_path(file_path)

    def _load_file_from_path(self, file_path: str):
        """从文件路径加载图片（支持打开文件和拖放）"""
        # 显示处理中状态
        self.canvas.set_processing(True)
        self.statusbar.showMessage(self.tr.tr('app.processing'))

        # 使用 QTimer 延迟加载，确保 UI 有时间更新
        QTimer.singleShot(50, lambda: self._do_load_file(file_path))

    def _do_load_file(self, file_path: str):
        """实际执行文件加载（延迟调用）"""
        try:
            # 先检查图像尺寸，避免加载过大的图像
            max_size = self.config_manager.get('performance', 'max_image_size', 20000)

            # 使用 PIL 快速读取图像尺寸（不加载完整图像数据）
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size

            # 检查是否超出限制
            if width > max_size or height > max_size:
                self.canvas.set_processing(False)
                QMessageBox.warning(
                    self,
                    self.tr.tr('dialog.warning'),
                    self.tr.tr('message.image_too_large', width=width, height=height, max_size=max_size)
                )
                self.statusbar.showMessage(self.tr.tr('message.load_cancelled'))
                return

            # 加载图片（不自动二值化）
            self.image_data = load_image(file_path, binarize=False)

            # 设置初始视图模式为二值化
            self.image_data.set_view_mode('binary')
            self.binarization_panel.view_mode_switcher.set_mode('binary')

            # 获取二值化参数
            preprocess_params = self.binarization_panel.get_preprocess_params()
            method = self.binarization_panel.get_method()
            threshold = self.binarization_panel.get_threshold()
            method_params = self.binarization_panel.get_method_params()

            # 使用异步工作线程进行二值化
            self.binarization_worker = BinarizationWorker(
                self.image_data.original_pixels,
                preprocess_params,
                method,
                threshold,
                method_params
            )

            # 连接信号
            self.binarization_worker.finished.connect(
                lambda binary_pixels: self._on_initial_binarization_finished(
                    binary_pixels, file_path
                )
            )
            self.binarization_worker.error.connect(self._on_binarization_error)

            # 启动工作线程
            self.binarization_worker.start()

        except Exception as e:
            # 隐藏处理中状态
            self.canvas.set_processing(False)
            QMessageBox.critical(self, self.tr.tr('error.title'),
                               self.tr.tr('error.load_failed', error=str(e)))

    def _on_initial_binarization_finished(self, binary_pixels: np.ndarray, file_path: str):
        """初始二值化完成的回调"""
        try:
            # 更新图片数据
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
            
            # 初始化图层面板
            self._initialize_layers_panel(file_path)
            
            # 初始化参数保存（用于非根图层时恢复）
            self.last_valid_params = {
                'preprocess_params': self.binarization_panel.get_preprocess_params().copy(),
                'method': self.binarization_panel.get_method(),
                'threshold': self.binarization_panel.get_threshold(),
                'method_params': self.binarization_panel.get_method_params().copy()
            }

            # 隐藏处理中状态
            self.canvas.set_processing(False)

            # 更新状态
            self.statusbar.showMessage(self.tr.tr('message.loaded', path=file_path))
            self._update_ui_state()

        except Exception as e:
            self.canvas.set_processing(False)
            QMessageBox.critical(self, self.tr.tr('error.title'), str(e))
    
    def _initialize_layers_panel(self, file_path: str):
        """
        初始化图层面板
        
        Args:
            file_path: 图片文件路径
        """
        # 清空现有图层
        self.properties_panel.layers_panel.clear_layers()
        
        # 添加根图层
        import os
        filename = os.path.basename(file_path)
        root_layer_name = f"🖼️ {filename}"  # 使用图片图标和文件名
        
        self.properties_panel.layers_panel.add_layer(
            layer_id="root",
            name=root_layer_name,
            is_root=True
        )
        
        # 设置根图层为激活状态（UI和内部状态）
        self.properties_panel.layers_panel.set_active_layer("root")
        self.active_layer_id = "root"

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
            self.tr.tr('file_dialog.save_as'),
            default_name,
            self.tr.tr('file_dialog.png_files')
        )

        if file_path:
            self._save_to_file(file_path)
            self.saved_file_path = file_path  # 更新保存路径

    def _generate_default_save_name(self) -> str:
        """
        根据配置生成默认保存文件名

        Returns:
            默认文件名路径
        """
        # 获取文件名格式配置
        filename_format = self.config_manager.get('file', 'filename_format', 'timestamp')

        if self.current_file_path:
            # 获取原文件信息
            dir_path = os.path.dirname(self.current_file_path)
            file_name = os.path.basename(self.current_file_path)
            name_without_ext, ext = os.path.splitext(file_name)

            # 根据配置生成文件名
            if filename_format == 'timestamp':
                # 原名_时间戳
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{name_without_ext}_{timestamp}{ext}"
            elif filename_format == 'copy':
                # 原名_副本
                new_name = f"{name_without_ext}_副本{ext}"
            else:  # custom
                # 自定义前缀/后缀
                prefix = self.config_manager.get('file', 'custom_prefix', '')
                suffix = self.config_manager.get('file', 'custom_suffix', '')
                new_name = f"{prefix}{name_without_ext}{suffix}{ext}"

            return os.path.join(dir_path, new_name)
        else:
            # 如果没有原文件路径，使用默认名称
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"image_{timestamp}.png"

    def _save_to_file(self, file_path: str):
        """保存到文件"""
        try:
            # 获取保存格式配置
            save_format_config = self.config_manager.get('file', 'default_save_format', 'follow_original')

            # 确定实际保存格式
            if save_format_config == 'follow_original':
                # 跟随用户选择的文件扩展名
                format_str = None
            else:
                # 使用配置的格式
                format_map = {
                    'png': 'PNG',
                    'jpg': 'JPEG',
                    'bmp': 'BMP',
                    'webp': 'WEBP'
                }
                format_str = format_map.get(save_format_config)

            save_image(self.image_data, file_path, format=format_str)
            self.current_file_path = file_path
            self.statusbar.showMessage(self.tr.tr('message.saved', path=file_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr.tr('dialog.error'), self.tr.tr('dialog.save_error', error=str(e)))

    def _undo(self):
        """撤销"""
        if self.image_data is None:
            return

        if self.history_manager.can_undo():
            self.image_data = self.history_manager.undo(self.image_data)
            self.canvas.set_image(self.image_data)

            # 同步选择工具的选区状态
            if self.canvas.selection_tool:
                self.canvas.selection_tool.selection_mask = self.image_data.selection_mask

            self.statusbar.showMessage(self.tr.tr('message.undone'))
            self._update_ui_state()
            # 更新属性面板（撤销可能恢复裁剪前的尺寸）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)

    def _redo(self):
        """重做"""
        if self.image_data is None:
            return

        if self.history_manager.can_redo():
            self.image_data = self.history_manager.redo()
            self.canvas.set_image(self.image_data)

            # 同步选择工具的选区状态
            if self.canvas.selection_tool:
                self.canvas.selection_tool.selection_mask = self.image_data.selection_mask

            self.statusbar.showMessage(self.tr.tr('message.redone'))
            self._update_ui_state()
            # 更新属性面板（重做可能改变尺寸）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)

    def _reset_to_initial(self):
        """重置到初始状态"""
        if self.image_data is None:
            return

        # 检查是否有编辑内容
        if not self._has_edits():
            self.statusbar.showMessage(self.tr.tr('message.no_edits'))
            return

        # 弹窗确认
        reply = QMessageBox.question(
            self,
            self.tr.tr('dialog.confirm'),
            self.tr.tr('dialog.reset_confirm'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 重新加载图片（最简单可靠的方式）
            if self.current_file_path:
                self._load_file_from_path(self.current_file_path)
                self.statusbar.showMessage(self.tr.tr('message.reset'))
            else:
                self.statusbar.showMessage(self.tr.tr('dialog.reset_no_file'))

    def _has_edits(self) -> bool:
        """
        检查是否有编辑内容

        Returns:
            True 如果有编辑内容（画笔编辑或裁剪），否则 False
        """
        if self.image_data is None:
            return False

        # 检查是否有画笔编辑（转换为 Python bool）
        has_brush_edits = (self.image_data.edit_mask is not None and
                          bool(self.image_data.edit_mask.any()))

        # 检查是否有裁剪（通过比较当前尺寸和原始尺寸）
        has_crop = (self.image_data.pixels.shape !=
                   self.image_data.original_pixels.shape)

        return has_brush_edits or has_crop

    def _on_parameters_changed(self, preprocess_params: dict, method: int, threshold: int):
        """参数改变（预处理或二值化）- 根据当前模式决定是否重新计算"""
        if self.image_data is None:
            return
        
        # 检查当前激活的图层
        if self.active_layer_id != "root":
            # 不是根图层，显示提示信息并恢复参数
            self.statusbar.showMessage(self.tr.tr('layers_panel.not_root_layer'))
            QMessageBox.information(
                self,
                self.tr.tr('dialog.info'),
                self.tr.tr('layers_panel.switch_to_root_warning')
            )
            
            # 恢复上一次的有效参数
            if self.last_valid_params is not None:
                self._restore_parameters(self.last_valid_params)
            
            return
        
        # 保存当前参数作为有效参数
        self.last_valid_params = {
            'preprocess_params': preprocess_params.copy(),
            'method': method,
            'threshold': threshold,
            'method_params': self.binarization_panel.get_method_params().copy()
        }

        mode = self.image_data.view_mode

        # 根据模式决定是否重新计算
        if mode == 'original':
            # 原图模式：只使缓存失效，不重新计算
            self.image_data.invalidate_preprocessed_cache()
            return

        elif mode == 'preprocessed':
            # 预处理模式：使用防抖 + 异步处理
            self.image_data.invalidate_preprocessed_cache()

            # 保存待处理的参数
            self.pending_preprocess_params = preprocess_params

            # 重启防抖定时器
            self.preprocess_debounce_timer.start()

            # 显示处理中状态
            self.canvas.set_processing(True)
            self.statusbar.showMessage(self.tr.tr('app.processing'))

        elif mode == 'binary':
            # 二值化模式：使缓存失效并重新计算二值化结果
            self.image_data.invalidate_preprocessed_cache()

            # 获取方法特定参数
            method_params = self.binarization_panel.get_method_params()

            # 保存待处理的参数
            self.pending_binarization_params = (preprocess_params, method, threshold, method_params)

            # 重启防抖定时器
            self.binarization_debounce_timer.start()

            # 显示处理中状态
            self.canvas.set_processing(True)
            self.statusbar.showMessage(self.tr.tr('app.processing'))
    
    def _restore_parameters(self, params: dict):
        """
        恢复参数到面板
        
        Args:
            params: 包含 preprocess_params, method, threshold, method_params 的字典
        """
        # 临时断开信号，避免触发参数改变事件
        self.binarization_panel.blockSignals(True)
        
        try:
            # 恢复预处理参数
            preprocess_params = params['preprocess_params']
            self.binarization_panel.exposure_slider.setValue(preprocess_params['exposure'])
            self.binarization_panel.contrast_slider.setValue(preprocess_params['contrast'])
            self.binarization_panel.sharpen_slider.setValue(preprocess_params['sharpen'])
            self.binarization_panel.gamma_slider.setValue(int(preprocess_params['gamma'] * 100))
            self.binarization_panel.smooth_slider.setValue(preprocess_params['smooth'])
            
            # 恢复 RGB 通道
            self.binarization_panel.red_channel_slider.setValue(preprocess_params['red_channel'])
            self.binarization_panel.green_channel_slider.setValue(preprocess_params['green_channel'])
            self.binarization_panel.blue_channel_slider.setValue(preprocess_params['blue_channel'])
            
            # 恢复边缘检测
            edge_mode_map = {0: 'off', 1: 'canny', 2: 'enhance', 3: 'contour'}
            edge_mode = edge_mode_map.get(preprocess_params['edge_mode'], 'off')
            self.binarization_panel.edge_mode_combo.setCurrentText(
                self.tr.tr(f'edge_mode.{edge_mode}')
            )
            self.binarization_panel.edge_strength_slider.setValue(preprocess_params['edge_strength'])
            self.binarization_panel.edge_threshold_slider.setValue(preprocess_params['edge_threshold'])
            
            # 恢复降噪
            denoise_method_map = {0: 'none', 1: 'gaussian', 2: 'median', 3: 'bilateral', 
                                 4: 'nlmeans', 5: 'morph_open', 6: 'morph_close'}
            denoise_method = denoise_method_map.get(preprocess_params['denoise_method'], 'none')
            self.binarization_panel.denoise_method_combo.setCurrentText(
                self.tr.tr(f'denoise_method.{denoise_method}')
            )
            self.binarization_panel.denoise_slider.setValue(preprocess_params['denoise'])
            
            # 恢复二值化方法和阈值
            self.binarization_panel.method_combo.setCurrentIndex(params['method'])
            self.binarization_panel.threshold_slider.setValue(params['threshold'])
            
            # 恢复方法特定参数
            method_params = params['method_params']
            method = params['method']
            
            # 根据方法恢复对应的参数
            if method == 1:  # 自适应阈值
                if 'block_size' in method_params:
                    self.binarization_panel.adaptive_block_size_slider.setValue(method_params['block_size'])
            elif method == 3:  # Sauvola
                if 'window_size' in method_params:
                    self.binarization_panel.sauvola_window_slider.setValue(method_params['window_size'])
                if 'k' in method_params:
                    self.binarization_panel.sauvola_k_slider.setValue(int(method_params['k'] * 100))
                if 'r' in method_params:
                    self.binarization_panel.sauvola_r_slider.setValue(method_params['r'])
            elif method == 4:  # Wolf
                if 'window_size' in method_params:
                    self.binarization_panel.wolf_window_slider.setValue(method_params['window_size'])
                if 'k' in method_params:
                    self.binarization_panel.wolf_k_slider.setValue(int(method_params['k'] * 100))
            elif method == 5:  # Nick
                if 'window_size' in method_params:
                    self.binarization_panel.nick_window_slider.setValue(method_params['window_size'])
                if 'k' in method_params:
                    self.binarization_panel.nick_k_slider.setValue(int(method_params['k'] * 100))
            elif method == 6:  # Bernsen
                if 'window_size' in method_params:
                    self.binarization_panel.bernsen_window_slider.setValue(method_params['window_size'])
                if 'contrast_threshold' in method_params:
                    self.binarization_panel.bernsen_contrast_slider.setValue(method_params['contrast_threshold'])
            elif method in [7, 8, 9]:  # 抖动算法
                if 'strength' in method_params:
                    self.binarization_panel.dither_strength_slider.setValue(method_params['strength'])
                if 'matrix_size' in method_params:
                    # matrix_size 是实际值（2, 4, 8, 16），需要转换为滑块值
                    self.binarization_panel.dither_matrix_size_slider.setValue(method_params['matrix_size'])
        
        finally:
            # 恢复信号
            self.binarization_panel.blockSignals(False)

    def _start_preprocess(self):
        """启动异步预处理"""
        if self.image_data is None or self.pending_preprocess_params is None:
            return

        # 取消之前的工作线程
        if self.preprocess_worker is not None and self.preprocess_worker.isRunning():
            self.preprocess_worker.cancel()
            self.preprocess_worker.wait()

        # 获取参数
        preprocess_params = self.pending_preprocess_params

        # 创建新的工作线程
        self.preprocess_worker = PreprocessWorker(
            self.image_data.original_pixels,
            preprocess_params
        )

        # 连接信号
        self.preprocess_worker.finished.connect(self._on_preprocess_finished)
        self.preprocess_worker.error.connect(self._on_preprocess_error)

        # 设置画布处理状态
        self.canvas.set_processing(True)

        # 启动线程
        self.preprocess_worker.start()

    def _on_preprocess_finished(self, preprocessed_pixels):
        """预处理完成"""
        # 清除画布处理状态
        self.canvas.set_processing(False)

        if self.image_data is None:
            return

        try:
            # 更新预处理缓存
            self.image_data.set_preprocessed_pixels(preprocessed_pixels)

            # 更新显示
            self._update_canvas_display()

            self.statusbar.showMessage(self.tr.tr('app.processing_complete'))

        except Exception as e:
            QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('dialog.update_error', error=str(e)))

    def _on_preprocess_error(self, error_message: str):
        """预处理出错"""
        # 清除画布处理状态
        self.canvas.set_processing(False)

        QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('app.processing_failed') + f":\n{error_message}")
        self.statusbar.showMessage(self.tr.tr('app.processing_failed'))

    def _start_binarization(self):
        """启动异步二值化处理"""
        if self.image_data is None or self.pending_binarization_params is None:
            return

        # 取消之前的工作线程
        if self.binarization_worker is not None and self.binarization_worker.isRunning():
            self.binarization_worker.cancel()
            self.binarization_worker.wait()

        # 获取参数
        preprocess_params, method, threshold, method_params = self.pending_binarization_params

        # 创建新的工作线程
        self.binarization_worker = BinarizationWorker(
            self.image_data.original_pixels,
            preprocess_params,
            method,
            threshold,
            method_params
        )

        # 连接信号
        self.binarization_worker.finished.connect(self._on_binarization_finished)
        self.binarization_worker.error.connect(self._on_binarization_error)

        # 设置画布处理状态
        self.canvas.set_processing(True)

        # 启动线程
        self.binarization_worker.start()

    def _on_binarization_finished(self, binary_pixels):
        """二值化完成"""
        # 清除画布处理状态
        self.canvas.set_processing(False)

        if self.image_data is None:
            return

        try:
            # 只更新基础图层，保留编辑图层
            self.image_data.update_base_layer(binary_pixels)

            # 更新分块缓存
            self._safe_update_tile_cache(self.image_data.selection_mask)

            self.statusbar.showMessage(self.tr.tr('app.processing_complete'))

        except Exception as e:
            QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('dialog.update_error', error=str(e)))

    def _on_binarization_error(self, error_message: str):
        """二值化出错"""
        # 清除画布处理状态
        self.canvas.set_processing(False)

        QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('app.processing_failed') + f":\n{error_message}")
        self.statusbar.showMessage(self.tr.tr('app.processing_failed'))

    def _on_image_modified(self):
        """图片被修改"""
        if self.image_data is not None:
            # 使预处理缓存失效（裁剪等操作会修改原图）
            self.image_data.invalidate_preprocessed_cache()

            # 保存到历史
            self.history_manager.push_state(self.image_data)
            self._update_ui_state()

            # 更新属性面板（裁剪后尺寸会变化）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)

    def _update_ui_state(self):
        """更新 UI 状态"""
        has_image = self.image_data is not None

        # 文件操作
        self.save_action_btn.setEnabled(has_image)

        # 编辑操作
        self.undo_action_btn.setEnabled(self.history_manager.can_undo())
        self.redo_action_btn.setEnabled(self.history_manager.can_redo())
        self.reset_action_btn.setEnabled(has_image and self._has_edits())

        # 工具
        self.pan_button.setEnabled(has_image)
        self.brush_button.setEnabled(has_image)
        self.crop_button.setEnabled(has_image)
        self.selection_tool_button.setEnabled(has_image)

        # 选区操作（保留 action 引用用于快捷键）
        has_selection = (self.image_data is not None and
                        self.image_data.selection_mask is not None and
                        bool(self.image_data.selection_mask.any()))  # 转换为 Python bool
        self.deselect_action.setEnabled(has_selection)
        self.invert_selection_action.setEnabled(has_image)
        self.select_black_action.setEnabled(has_image)
        self.select_white_action.setEnabled(has_image)

    def _fill_selection(self, color: int):
        """
        填充选区（使用画笔批量填充逻辑）

        直接修改像素，不使用复杂的图层系统，保持性能一致。

        Args:
            color: 填充颜色（0=黑色, 255=白色）
        """
        if self.image_data is None:
            return

        # 检查是否有选区
        if not self.canvas.selection_tool.has_selection():
            self.statusbar.showMessage(self.tr.tr('message.no_selection'))
            return

        # 获取选区蒙版
        selection_mask = self.canvas.selection_tool.selection_mask

        # 检查选区尺寸是否匹配
        if selection_mask.shape != (self.image_data.height, self.image_data.width):
            self.statusbar.showMessage(self.tr.tr('message.selection_size_mismatch'))
            self.canvas.selection_tool.clear_selection()
            self.image_data.selection_mask = None
            self._safe_update_tile_cache(None)
            return

        # 使用画笔批量填充逻辑：直接修改像素数据
        import numpy as np

        # 初始化编辑掩码（如果不存在）
        if self.image_data.edit_mask is None:
            self.image_data.edit_mask = np.zeros((self.image_data.height, self.image_data.width), dtype=bool)
            self.image_data.edit_values = np.zeros((self.image_data.height, self.image_data.width), dtype=np.uint8)

        # 批量填充：直接设置编辑掩码和值
        self.image_data.edit_mask[selection_mask] = True
        self.image_data.edit_values[selection_mask] = color

        # 清除选区（这样才能看到填充效果）
        self.canvas.selection_tool.clear_selection()
        self.image_data.selection_mask = None

        # 更新分块缓存（不显示选区）
        self._safe_update_tile_cache(None)

        # 保存到历史管理器（支持撤销/重做）
        self.history_manager.push_state(self.image_data)

        # 更新 UI 状态
        self._update_ui_state()

        # 更新显示
        self.canvas.update()

        # 显示提示
        color_name = self.tr.tr('color.black') if color == 0 else self.tr.tr('color.white')
        self.statusbar.showMessage(self.tr.tr('message.filled', color=color_name))

    def _fill_selection_holes(self):
        """
        填充选区内部的空洞
        
        使用形态学闭运算或洪水填充算法填充选区内的空洞，使选区变为实心。
        """
        if self.image_data is None:
            return
        
        # 检查是否有选区
        if not self.canvas.selection_tool.has_selection():
            self.statusbar.showMessage(self.tr.tr('message.no_selection'))
            return
        
        # 获取选区蒙版
        selection_mask = self.canvas.selection_tool.selection_mask
        
        # 检查选区尺寸是否匹配
        if selection_mask.shape != (self.image_data.height, self.image_data.width):
            self.statusbar.showMessage(self.tr.tr('message.selection_size_mismatch'))
            self.canvas.selection_tool.clear_selection()
            self.image_data.selection_mask = None
            self._safe_update_tile_cache(None)
            return
        
        try:
            import cv2
            import numpy as np
            
            # 将布尔蒙版转换为 uint8
            mask_uint8 = selection_mask.astype(np.uint8) * 255
            
            # 使用形态学闭运算填充小空洞
            # 闭运算 = 先膨胀后腐蚀，可以填充小的空洞
            kernel_size = max(3, int(self.canvas.selection_tool.size / 10))  # 根据笔刷大小动态调整
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            closed = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
            
            # 使用洪水填充来填充更大的空洞
            # 从边缘开始洪水填充背景（反向思路）
            filled = closed.copy()
            h, w = filled.shape
            flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            
            # 从四个角开始洪水填充背景
            cv2.floodFill(filled, flood_mask, (0, 0), 255)
            
            # 反转得到填充后的选区（背景外的都是选区）
            filled_inverted = cv2.bitwise_not(filled)
            
            # 与闭运算结果合并
            final_mask = cv2.bitwise_or(closed, filled_inverted)
            
            # 转换回布尔蒙版
            self.canvas.selection_tool.selection_mask = (final_mask > 0)
            self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
            
            # 更新轮廓显示
            self.canvas._request_contour_update(
                self.canvas.selection_tool.selection_mask, 
                dirty_rect=None, 
                immediate=True
            )
            
            # 更新分块缓存
            self._safe_update_tile_cache(self.canvas.selection_tool.selection_mask)
            
            # 更新显示
            self.canvas.update()
            
            # 显示提示
            self.statusbar.showMessage(self.tr.tr('message.selection_filled'))
            
        except ImportError:
            # 如果没有 cv2，使用简单的 scipy 方法
            try:
                from scipy import ndimage
                import numpy as np
                
                # 使用 binary_fill_holes 填充空洞
                filled_mask = ndimage.binary_fill_holes(selection_mask)
                
                # 更新选区
                self.canvas.selection_tool.selection_mask = filled_mask
                self.image_data.selection_mask = filled_mask
                
                # 更新轮廓显示
                self.canvas._request_contour_update(
                    self.canvas.selection_tool.selection_mask, 
                    dirty_rect=None, 
                    immediate=True
                )
                
                # 更新分块缓存
                self._safe_update_tile_cache(self.canvas.selection_tool.selection_mask)
                
                # 更新显示
                self.canvas.update()
                
                # 显示提示
                self.statusbar.showMessage(self.tr.tr('message.selection_filled'))
                
            except ImportError:
                self.statusbar.showMessage(self.tr.tr('message.feature_unavailable'))

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
        self.properties_panel.selection_method_group.buttonClicked.connect(
            self._on_selection_method_changed_panel
        )
        # 填充按钮
        self.properties_panel.fill_black_button.clicked.connect(
            lambda: self._fill_selection(0)
        )
        self.properties_panel.fill_white_button.clicked.connect(
            lambda: self._fill_selection(255)
        )
        self.properties_panel.deselect_button.clicked.connect(self._deselect)
        self.properties_panel.invert_button.clicked.connect(self._invert_selection)
        # 填充选区空洞按钮
        self.properties_panel.fill_selection_holes_button.clicked.connect(
            self._fill_selection_holes
        )

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

    def _on_selection_method_changed_panel(self):
        """属性面板：选择方式改变（涂抹/框选）"""
        button_id = self.properties_panel.selection_method_group.checkedId()
        is_rect_mode = (button_id == 1)  # 0=涂抹, 1=框选
        self.canvas.selection_tool.rect_select_mode = is_rect_mode

        # 更新光标（无论哪种模式都隐藏系统光标，显示自定义光标）
        self.canvas.setCursor(Qt.BlankCursor)

        if is_rect_mode:
            self.statusbar.showMessage(self.tr.tr('message.rect_select_mode'))
        else:
            self.statusbar.showMessage(self.tr.tr('message.paint_select_mode'))

        self.canvas.update()

    def _on_view_mode_changed(self, mode: str):
        """
        处理视图模式切换

        Args:
            mode: 新的视图模式 ('original', 'preprocessed', 'binary')
        """
        if self.image_data is None:
            return

        # 更新 ImageData 的视图模式
        self.image_data.set_view_mode(mode)

        # 根据模式更新显示
        if mode == 'original':
            # 显示原图
            self._update_canvas_display()

        elif mode == 'preprocessed':
            # 显示预处理结果
            if self.image_data.preprocessed_pixels is None:
                # 缓存不存在，计算预处理结果
                self._compute_preprocessed_pixels()
            self._update_canvas_display()

        elif mode == 'binary':
            # 显示二值化结果
            self._update_canvas_display()

        # 更新工具状态
        self._update_tool_states()

        mode_name = self.tr.tr(f'view_mode.{mode}')
        self.statusbar.showMessage(self.tr.tr('message.view_mode_changed', mode=mode_name))

    def _compute_preprocessed_pixels(self):
        """计算并缓存预处理结果"""
        if self.image_data is None:
            return

        try:
            preprocess_params = self.binarization_panel.get_preprocess_params()
            preprocessed = BinarizationEngine.apply_preprocess(
                self.image_data.original_pixels.copy(),
                **preprocess_params
            )
            self.image_data.set_preprocessed_pixels(preprocessed)
        except MemoryError:
            QMessageBox.critical(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('dialog.memory_error')
            )
            self.image_data.invalidate_preprocessed_cache()
            # 切换回原图模式
            self.image_data.set_view_mode('original')
            self.binarization_panel.view_mode_switcher.set_mode('original')
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('dialog.preprocess_error', error=str(e))
            )
            # 保持当前模式不变
            self.binarization_panel.view_mode_switcher.set_mode(self.image_data.view_mode)

    def _update_canvas_display(self):
        """更新 Canvas 显示"""
        if self.image_data is None:
            return

        self._safe_update_tile_cache(self.image_data.selection_mask)

    def _safe_update_tile_cache(self, selection_mask=None):
        """
        安全地更新 tile_cache

        Args:
            selection_mask: 选区蒙版（可选）
        """
        if self.image_data is None:
            return

        # 根据当前激活的图层决定显示内容
        if self.active_layer_id == "root":
            # 根图层：合成显示所有层
            pixels = self._composite_layers()
        else:
            # 用户图层：显示根图层 + 编辑层 + 该图层（未选中区域为白色）
            pixels = None
            for layer in self.image_data.user_layers:
                if layer.id == self.active_layer_id:
                    # 创建白色背景
                    pixels = np.full(
                        (self.image_data.height, self.image_data.width),
                        255,  # 白色背景
                        dtype=np.uint8
                    )
                    
                    # 在图层的掩码区域，先应用根图层和编辑层
                    x, y, w, h = layer.bbox
                    
                    # 获取图层区域的根图层像素
                    base_region = self.image_data.pixels[y:y+h, x:x+w].copy()
                    
                    # 应用编辑层到该区域
                    if self.image_data.edit_mask is not None:
                        edit_region = self.image_data.edit_mask[y:y+h, x:x+w]
                        if edit_region.any():
                            base_region[edit_region] = self.image_data.edit_values[y:y+h, x:x+w][edit_region]
                    
                    # 将基础层放到合成结果中（只在掩码区域）
                    pixels[y:y+h, x:x+w][layer.mask] = base_region[layer.mask]
                    
                    # 应用该图层的黑色像素
                    black_mask = layer.mask & (layer.pixels == 0)
                    pixels[y:y+h, x:x+w][black_mask] = 0
                    break
            
            # 如果找不到图层，回退到根图层
            if pixels is None:
                pixels = self._composite_layers()

        # 注意：不再强制转换为灰度图，TileCache 现在支持彩色图像

        self.canvas.tile_cache.set_image(pixels, selection_mask)
        self.canvas.update()

    def _update_tool_states(self):
        """根据当前视图模式和图层状态更新工具状态"""
        if self.image_data is None:
            # 没有图片时，所有工具都不可用
            self.pan_button.setEnabled(False)
            self.brush_button.setEnabled(False)
            self.crop_button.setEnabled(False)
            self.selection_tool_button.setEnabled(False)
            return

        mode = self.image_data.view_mode
        is_root_layer = (self.active_layer_id == "root")

        # 抓取工具：在所有模式和图层下可用
        self.pan_button.setEnabled(True)

        # 裁剪工具：仅在根图层可用
        crop_enabled = is_root_layer
        self.crop_button.setEnabled(crop_enabled)
        if not crop_enabled and self.canvas.current_tool == self.canvas.crop_tool:
            self.canvas.set_tool(None)
            self.crop_button.setChecked(False)
            self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
            # 隐藏工具设置
            self.properties_panel.hide_all_tool_settings()

        # 画笔工具：仅在二值化模式且根图层可用
        brush_enabled = (mode == 'binary' and is_root_layer)
        self.brush_button.setEnabled(brush_enabled)
        if not brush_enabled and self.canvas.current_tool == self.canvas.brush_tool:
            self.canvas.set_tool(None)
            self.brush_button.setChecked(False)
            self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
            # 隐藏工具设置
            self.properties_panel.hide_all_tool_settings()

        # 选择工具：仅在二值化模式且根图层可用
        selection_enabled = (mode == 'binary' and is_root_layer)
        self.selection_tool_button.setEnabled(selection_enabled)
        if not selection_enabled and self.canvas.current_tool == self.canvas.selection_tool:
            self.canvas.set_tool(None)
            self.selection_tool_button.setChecked(False)
            self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
            # 隐藏工具设置
            self.properties_panel.hide_all_tool_settings()

    def _get_mode_display_name(self, mode: str) -> str:
        """获取模式的显示名称"""
        names = {
            'original': '原图',
            'preprocessed': '预处理',
            'binary': '二值化'
        }
        return names.get(mode, mode)

    def _show_settings(self):
        """显示设置对话框"""
        from src.views.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        if dialog.exec():
            # 设置已保存，立即应用新配置
            self.apply_config()
            self.statusbar.showMessage(self.tr.tr('message.settings_applied'), 3000)

    def apply_config(self):
        """应用配置到各个组件"""
        config = self.config_manager

        # 0. 界面设置
        # 主题设置
        theme = config.get('interface', 'theme', 'light')
        from ..utils.theme_manager import ThemeManager
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QIcon, QPixmap
        from ..utils.resources import APP_ICON_BYTES, APP_ICON_BYTES_DARK
        
        theme_manager = ThemeManager()
        theme_manager.apply_theme(QApplication.instance(), theme)
        
        # 应用深色标题栏（主题切换后立即更新）
        self._apply_dark_titlebar()
        
        # 更新应用程序图标
        if theme == 'system':
            detected_theme = theme_manager._detect_system_theme()
        else:
            detected_theme = theme
        
        icon_bytes = APP_ICON_BYTES_DARK if detected_theme == 'dark' else APP_ICON_BYTES
        pixmap = QPixmap()
        pixmap.loadFromData(icon_bytes)
        icon = QIcon(pixmap)
        QApplication.instance().setWindowIcon(icon)
        
        # 动画开关
        animations_enabled = config.get('interface', 'animations_enabled', True)
        from ..utils.animations import set_global_animation_enabled
        set_global_animation_enabled(animations_enabled)

        # 1. 编辑器设置
        # 画笔默认大小
        default_brush_size = config.get('editor', 'default_brush_size', 20)
        self.canvas.brush_tool.size = default_brush_size
        # 更新属性面板 UI
        self.properties_panel.brush_size_spinbox.setValue(default_brush_size)

        # 选择工具默认大小
        default_selection_size = config.get('editor', 'default_selection_size', 50)
        self.canvas.selection_tool.size = default_selection_size
        # 更新属性面板 UI
        self.properties_panel.selection_size_spinbox.setValue(default_selection_size)

        # 撤销历史限制
        undo_limit = config.get('editor', 'undo_history_limit', 50)
        self.history_manager.max_history = undo_limit

        # 2. 性能设置
        # Tile 缓存大小
        tile_cache_size = config.get('performance', 'tile_cache_size', 1000)
        self.canvas.tile_cache.max_tiles = tile_cache_size

        # 二值化防抖延迟
        debounce_delay = config.get('performance', 'debounce_delay', 150)
        self.binarization_debounce_timer.setInterval(debounce_delay)
        self.preprocess_debounce_timer.setInterval(debounce_delay)

        # 3. 文件设置（暂时不需要应用，在保存时使用）

        # 刷新画布以应用新设置
        if self.image_data is not None:
            self.canvas.update()

    def _show_about(self):
        """显示关于对话框"""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QHBoxLayout
        from PySide6.QtGui import QPixmap, QImage
        from PySide6.QtCore import Qt

        from src.__version__ import __app_name__, __author__, __release_date__, __version__
        from ..utils.resources import APP_ICON_BYTES, APP_ICON_BYTES_DARK

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr.tr('about.title', app_name=__app_name__))
        dialog.setMinimumWidth(450)
        dialog.setMinimumHeight(350)
        
        # 应用深色标题栏
        self._apply_dark_titlebar_to_dialog(dialog)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 顶部布局：应用名称 + 图标
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        # 左侧信息布局
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # 应用名称
        app_name_label = QLabel(__app_name__)
        app_name_label.setObjectName("aboutAppName")
        app_name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        info_layout.addWidget(app_name_label)

        # 版本号
        version_label = QLabel(self.tr.tr('about.version', version=__version__))
        version_label.setObjectName("aboutVersion")
        version_label.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(version_label)

        # 发布日期
        date_label = QLabel(self.tr.tr('about.release_date', date=__release_date__))
        date_label.setObjectName("aboutDate")
        date_label.setStyleSheet("font-size: 14px;")
        info_layout.addWidget(date_label)
        
        info_layout.addStretch()
        top_layout.addLayout(info_layout)
        
        # 应用图标（右侧）- 根据主题选择图标
        theme = self.config_manager.get('interface', 'theme', 'light')
        if theme == 'system':
            from ..utils.theme_manager import ThemeManager
            theme_manager = ThemeManager()
            theme = theme_manager._detect_system_theme()
        
        icon_bytes = APP_ICON_BYTES_DARK if theme == 'dark' else APP_ICON_BYTES
        icon_label = QLabel()
        icon_pixmap = QPixmap.fromImage(QImage.fromData(icon_bytes))
        icon_label.setPixmap(icon_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setFixedSize(100, 100)
        top_layout.addWidget(icon_label)
        
        layout.addLayout(top_layout)

        # 分隔线
        separator = QLabel()
        separator.setObjectName("aboutSeparator")
        separator.setStyleSheet("margin: 10px 0;")
        layout.addWidget(separator)

        # 描述
        desc_label = QLabel(self.tr.tr('about.description'))
        desc_label.setObjectName("aboutDesc")
        desc_label.setStyleSheet("font-size: 14px; line-height: 1.6;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 作者
        author_label = QLabel(self.tr.tr('about.author', author=__author__))
        author_label.setObjectName("aboutAuthor")
        author_label.setStyleSheet("font-size: 14px; margin-top: 10px;")
        layout.addWidget(author_label)

        # 版权
        copyright_label = QLabel(self.tr.tr('about.copyright'))
        copyright_label.setObjectName("aboutCopyright")
        copyright_label.setStyleSheet("font-size: 12px; margin-top: 5px;")
        layout.addWidget(copyright_label)

        # 许可证
        license_label = QLabel(self.tr.tr('about.license'))
        license_label.setObjectName("aboutLicense")
        license_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(license_label)

        # 添加弹性空间
        layout.addStretch()

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec()
