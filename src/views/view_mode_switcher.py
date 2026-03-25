"""
视图模式切换器

用于在原图、预处理和二值化模式之间切换。
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QFrame
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from ..utils.translation_manager import get_translator


class ViewModeSwitcher(QWidget):
    """
    视图模式切换器类
    
    提供三种视图模式的切换：原图、预处理、二值化。
    """
    
    # 信号：模式改变 (mode: 'original', 'preprocessed', 'binary')
    mode_changed = Signal(str)
    
    def __init__(self, parent=None):
        """
        初始化视图模式切换器
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        
        # 获取翻译器
        self.tr = get_translator()
        
        # 当前模式
        self._current_mode = 'binary'
        
        # 动画开关（默认启用）
        self._animation_enabled = True
        
        # 动画对象
        self.animation = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建按钮组容器（使用专门的样式）
        self.button_container = QFrame()
        self.button_container.setObjectName("viewModeSwitcher")
        container_layout = QHBoxLayout(self.button_container)
        container_layout.setContentsMargins(3, 1, 3, 1)
        container_layout.setSpacing(0)
        
        # 创建选中指示器（滑动背景）
        self.indicator = QWidget(self.button_container)
        self.indicator.setObjectName("viewModeSwitcherIndicator")
        self.indicator.setStyleSheet("""
            QWidget#viewModeSwitcherIndicator {
                background-color: rgba(74, 134, 232, 0.2);
                border-radius: 4px;
            }
        """)
        self.indicator.lower()  # 放到按钮下方
        
        # 创建按钮组
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        # 创建三个按钮
        self.original_button = QPushButton(self.tr.tr('view_mode.original'))
        self.preprocessed_button = QPushButton(self.tr.tr('view_mode.preprocessed'))
        self.binary_button = QPushButton(self.tr.tr('view_mode.binary'))
        
        # 设置按钮为可选中
        self.original_button.setCheckable(True)
        self.preprocessed_button.setCheckable(True)
        self.binary_button.setCheckable(True)
        
        # 设置按钮 tooltip（显示快捷键）
        self.original_button.setToolTip(self.tr.tr('view_mode.original') + " (Ctrl+1)")
        self.preprocessed_button.setToolTip(self.tr.tr('view_mode.preprocessed') + " (Ctrl+2)")
        self.binary_button.setToolTip(self.tr.tr('view_mode.binary') + " (Ctrl+3)\n\n" + self.tr.tr('view_mode.tab_hint'))
        
        # 设置按钮高度（与工具栏一致）
        for btn in [self.original_button, self.preprocessed_button, self.binary_button]:
            btn.setMinimumHeight(28)
            btn.setMaximumHeight(28)
        
        # 添加到按钮组
        self.button_group.addButton(self.original_button, 0)
        self.button_group.addButton(self.preprocessed_button, 1)
        self.button_group.addButton(self.binary_button, 2)
        
        # 设置默认选中二值化模式
        self.binary_button.setChecked(True)
        
        # 添加按钮到容器
        container_layout.addWidget(self.original_button)
        container_layout.addWidget(self.preprocessed_button)
        container_layout.addWidget(self.binary_button)
        
        # 添加容器到主布局
        layout.addWidget(self.button_container)
        
        # 延迟初始化指示器位置（等待布局完成）
        QTimer.singleShot(0, self._init_indicator_position)
    
    def connect_signals(self):
        """连接信号"""
        self.original_button.clicked.connect(lambda: self._on_button_clicked('original'))
        self.preprocessed_button.clicked.connect(lambda: self._on_button_clicked('preprocessed'))
        self.binary_button.clicked.connect(lambda: self._on_button_clicked('binary'))
    
    def _init_indicator_position(self):
        """初始化指示器位置（在布局完成后调用）"""
        # 根据当前模式设置指示器初始位置
        target_button = self._get_button_by_mode(self._current_mode)
        if target_button:
            self.indicator.setGeometry(target_button.geometry())
    
    def _get_button_by_mode(self, mode: str) -> QPushButton:
        """
        根据模式获取对应的按钮
        
        Args:
            mode: 模式名称
            
        Returns:
            对应的按钮对象
        """
        if mode == 'original':
            return self.original_button
        elif mode == 'preprocessed':
            return self.preprocessed_button
        elif mode == 'binary':
            return self.binary_button
        return None
    
    def _animate_indicator(self, target_button: QPushButton):
        """
        动画化指示器到目标按钮
        
        Args:
            target_button: 目标按钮
        """
        # 检查全局动画开关和局部动画开关
        from ..utils.animations import is_global_animation_enabled
        if not self._animation_enabled or not is_global_animation_enabled():
            # 动画禁用时直接移动
            self.indicator.setGeometry(target_button.geometry())
            return
        
        # 停止正在运行的动画
        if self.animation and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        
        # 创建几何动画
        self.animation = QPropertyAnimation(self.indicator, b"geometry")
        self.animation.setDuration(250)  # 250ms
        self.animation.setStartValue(self.indicator.geometry())
        self.animation.setEndValue(target_button.geometry())
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
    
    def _on_button_clicked(self, mode: str):
        """
        按钮点击事件
        
        Args:
            mode: 新的模式
        """
        if self._current_mode != mode:
            # 获取目标按钮
            target_button = self._get_button_by_mode(mode)
            if target_button:
                # 动画化指示器
                self._animate_indicator(target_button)
            
            # 更新当前模式
            self._current_mode = mode
            self.mode_changed.emit(mode)
    
    def get_current_mode(self) -> str:
        """
        获取当前选中的模式
        
        Returns:
            当前模式: 'original', 'preprocessed', 或 'binary'
        """
        return self._current_mode
    
    def set_mode(self, mode: str):
        """
        设置当前模式（不发射信号）
        
        Args:
            mode: 要设置的模式: 'original', 'preprocessed', 或 'binary'
        """
        if mode not in ['original', 'preprocessed', 'binary']:
            raise ValueError(f"Invalid mode: {mode}")
        
        self._current_mode = mode
        
        # 更新按钮选中状态
        if mode == 'original':
            self.original_button.setChecked(True)
        elif mode == 'preprocessed':
            self.preprocessed_button.setChecked(True)
        elif mode == 'binary':
            self.binary_button.setChecked(True)
        
        # 更新指示器位置（无动画）
        target_button = self._get_button_by_mode(mode)
        if target_button:
            self.indicator.setGeometry(target_button.geometry())
    
    def set_animation_enabled(self, enabled: bool):
        """
        设置是否启用动画
        
        Args:
            enabled: True 启用动画，False 禁用动画
        """
        self._animation_enabled = enabled
    
    def is_animation_enabled(self) -> bool:
        """
        获取动画是否启用
        
        Returns:
            True 表示启用，False 表示禁用
        """
        return self._animation_enabled
