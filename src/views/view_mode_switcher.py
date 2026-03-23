"""
视图模式切换器

用于在原图、预处理和二值化模式之间切换。
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QFrame
from PySide6.QtCore import Qt, Signal


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
        
        # 当前模式
        self._current_mode = 'binary'
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建按钮组容器（使用专门的样式）
        button_container = QFrame()
        button_container.setObjectName("viewModeSwitcher")
        container_layout = QHBoxLayout(button_container)
        container_layout.setContentsMargins(3, 1, 3, 1)
        container_layout.setSpacing(0)
        
        # 创建按钮组
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        # 创建三个按钮
        self.original_button = QPushButton("原图")
        self.preprocessed_button = QPushButton("预处理")
        self.binary_button = QPushButton("二值化")
        
        # 设置按钮为可选中
        self.original_button.setCheckable(True)
        self.preprocessed_button.setCheckable(True)
        self.binary_button.setCheckable(True)
        
        # 设置按钮 tooltip（显示快捷键）
        self.original_button.setToolTip("切换到原图模式 (Ctrl+1)")
        self.preprocessed_button.setToolTip("切换到预处理模式 (Ctrl+2)")
        self.binary_button.setToolTip("切换到二值化模式 (Ctrl+3)\n\n提示：使用 Tab 键可循环切换视图模式")
        
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
        layout.addWidget(button_container)
    
    def connect_signals(self):
        """连接信号"""
        self.original_button.clicked.connect(lambda: self._on_button_clicked('original'))
        self.preprocessed_button.clicked.connect(lambda: self._on_button_clicked('preprocessed'))
        self.binary_button.clicked.connect(lambda: self._on_button_clicked('binary'))
    
    def _on_button_clicked(self, mode: str):
        """
        按钮点击事件
        
        Args:
            mode: 新的模式
        """
        if self._current_mode != mode:
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
