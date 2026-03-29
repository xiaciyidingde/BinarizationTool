"""
图层面板模块

显示和管理图层的面板组件。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..utils.translation_manager import get_translator
from ..utils.resources import SHOW, HIDE, DELETE


class LayerItemWidget(QWidget):
    """自定义图层项 Widget"""
    
    visibility_toggled = Signal(str, bool)  # layer_id, visible
    delete_clicked = Signal(str)  # layer_id
    
    def __init__(self, layer_id: str, name: str, visible: bool = True, is_root: bool = False, parent=None):
        """
        初始化图层项
        
        Args:
            layer_id: 图层 ID
            name: 图层名称
            visible: 是否可见
            is_root: 是否是根图层
            parent: 父组件
        """
        super().__init__(parent)
        
        self.layer_id = layer_id
        self.is_root = is_root
        self.visible = visible
        
        # 水平布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # 可见性按钮
        self.visibility_button = QPushButton()
        self.visibility_button.setFixedSize(20, 20)
        self.visibility_button.setFlat(True)
        self.visibility_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.2);
                border-radius: 3px;
            }
        """)
        self.visibility_button.setToolTip("显示/隐藏图层")
        self.visibility_button.clicked.connect(self._on_visibility_clicked)
        
        # 根图层的可见性按钮禁用
        if is_root:
            self.visibility_button.setEnabled(False)
        
        layout.addWidget(self.visibility_button)
        
        # 图层名称
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("padding: 2px;")
        layout.addWidget(self.name_label, 1)  # 拉伸因子为1
        
        # 删除按钮（仅用户图层显示）
        if not is_root:
            self.delete_button = QPushButton()
            self.delete_button.setFixedSize(20, 20)
            self.delete_button.setFlat(True)
            self.delete_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(255, 0, 0, 0.2);
                    border-radius: 3px;
                }
            """)
            delete_pixmap = QPixmap()
            delete_pixmap.loadFromData(DELETE)
            self.delete_button.setIcon(QIcon(delete_pixmap))
            self.delete_button.setToolTip("删除图层")
            self.delete_button.clicked.connect(self._on_delete_clicked)
            layout.addWidget(self.delete_button)
        
        # 更新可见性样式
        self._update_visibility_style()
    
    def _on_visibility_clicked(self):
        """可见性按钮被点击"""
        self.visible = not self.visible
        self._update_visibility_style()
        self.visibility_toggled.emit(self.layer_id, self.visible)
    
    def _on_delete_clicked(self):
        """删除按钮被点击"""
        self.delete_clicked.emit(self.layer_id)
    
    def _update_visibility_style(self):
        """更新可见性样式"""
        if self.visible:
            # 可见：显示 SHOW 图标
            pixmap = QPixmap()
            pixmap.loadFromData(SHOW)
            self.visibility_button.setIcon(QIcon(pixmap))
            self.name_label.setStyleSheet("padding: 2px; color: palette(text);")
        else:
            # 隐藏：显示 HIDE 图标，图层名称变灰
            pixmap = QPixmap()
            pixmap.loadFromData(HIDE)
            self.visibility_button.setIcon(QIcon(pixmap))
            self.name_label.setStyleSheet("padding: 2px; color: #999999;")
    
    def set_visible(self, visible: bool):
        """设置可见性"""
        self.visible = visible
        self._update_visibility_style()
    
    def set_name(self, name: str):
        """设置图层名称"""
        self.name_label.setText(name)


class LayersPanel(QWidget):
    """
    图层面板类
    
    显示图层列表，支持选择、显示/隐藏、锁定/解锁、删除等操作。
    """
    
    # 信号
    layer_selected = Signal(str)  # 图层被选中（layer_id）
    layer_visibility_changed = Signal(str, bool)  # 图层可见性改变（layer_id, visible）
    layer_locked_changed = Signal(str, bool)  # 图层锁定状态改变（layer_id, locked）
    layer_deleted = Signal(str)  # 图层被删除（layer_id）
    save_selection_clicked = Signal()  # 保存选区按钮被点击
    merge_layers_clicked = Signal(list)  # 合并图层按钮被点击（layer_ids）
    
    def __init__(self, parent=None):
        """初始化图层面板"""
        super().__init__(parent)
        
        # 获取翻译器
        self.tr = get_translator()
        
        # 设置尺寸策略：水平固定，垂直首选
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置 UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 设置固定宽度
        self.setFixedWidth(220)
        
        # 创建一个容器 QGroupBox 包裹所有内容
        container = QGroupBox()
        container.setObjectName("layersPanelContainer")
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(8)
        
        # 保存选区按钮
        self.save_selection_button = QPushButton(self.tr.tr('layers_panel.save_selection'))
        self.save_selection_button.setMinimumHeight(32)
        self.save_selection_button.setFixedWidth(204)  # 220 - 16 (左右边距)
        container_layout.addWidget(self.save_selection_button)
        
        # 图层列表分组
        layers_group = QGroupBox(self.tr.tr('layers_panel.layers_list'))
        layers_group.setFixedWidth(204)  # 与按钮同宽
        layers_layout = QVBoxLayout()
        layers_layout.setSpacing(8)
        layers_layout.setContentsMargins(8, 8, 8, 8)
        
        # 图层列表控件
        self.layers_list = QListWidget()
        self.layers_list.setMinimumHeight(50)
        self.layers_list.setMaximumHeight(200)
        # 支持多选
        self.layers_list.setSelectionMode(QListWidget.ExtendedSelection)
        layers_layout.addWidget(self.layers_list)
        
        layers_group.setLayout(layers_layout)
        container_layout.addWidget(layers_group)
        
        # 图层操作按钮
        actions_group = QGroupBox(self.tr.tr('layers_panel.layer_operations'))
        actions_group.setFixedWidth(204)  # 与按钮同宽
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        actions_layout.setContentsMargins(8, 8, 8, 8)
        
        # 第一行：合并和删除
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        
        self.merge_button = QPushButton(self.tr.tr('layers_panel.merge'))
        self.merge_button.setEnabled(False)  # 默认禁用
        row1_layout.addWidget(self.merge_button)
        
        self.delete_button = QPushButton(self.tr.tr('layers_panel.delete'))
        self.delete_button.setEnabled(False)  # 默认禁用
        row1_layout.addWidget(self.delete_button)
        
        actions_layout.addLayout(row1_layout)
        
        actions_group.setLayout(actions_layout)
        container_layout.addWidget(actions_group)
        
        # 设置容器布局
        container.setLayout(container_layout)
        main_layout.addWidget(container)
        
        # 不添加弹性空间，让布局紧凑
        
        # 连接信号
        self.save_selection_button.clicked.connect(self._on_save_selection_clicked)
        self.merge_button.clicked.connect(self._on_merge_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.layers_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _on_save_selection_clicked(self):
        """保存选区按钮被点击"""
        self.save_selection_clicked.emit()
    
    def _on_merge_clicked(self):
        """合并按钮被点击"""
        selected_ids = self._get_selected_layer_ids()
        if len(selected_ids) >= 2:
            self.merge_layers_clicked.emit(selected_ids)
    
    def _on_delete_clicked(self):
        """删除按钮被点击"""
        selected_ids = self._get_selected_layer_ids()
        for layer_id in selected_ids:
            self.layer_deleted.emit(layer_id)
    
    def _on_selection_changed(self):
        """列表选择改变"""
        selected_ids = self._get_selected_layer_ids()
        
        # 更新按钮状态
        has_selection = len(selected_ids) > 0
        can_merge = len(selected_ids) >= 2
        
        self.delete_button.setEnabled(has_selection)
        self.merge_button.setEnabled(can_merge)
        
        # 发射选中信号（单选时）
        if len(selected_ids) == 1:
            self.layer_selected.emit(selected_ids[0])
    
    def _get_selected_layer_ids(self) -> list:
        """获取选中的图层 ID 列表"""
        selected_ids = []
        for item in self.layers_list.selectedItems():
            layer_id = item.data(Qt.UserRole)
            if layer_id:
                selected_ids.append(layer_id)
        return selected_ids
    
    def add_layer(self, layer_id: str, name: str, is_root: bool = False, is_out_of_bounds: bool = False, visible: bool = True):
        """
        添加图层到列表
        
        Args:
            layer_id: 图层 ID
            name: 图层名称
            is_root: 是否是根图层
            is_out_of_bounds: 是否超出图像范围（仅用户图层）
            visible: 是否可见
        """
        item = QListWidgetItem()
        item.setData(Qt.UserRole, layer_id)
        
        # 创建自定义 widget
        widget = LayerItemWidget(layer_id, name, visible, is_root)
        
        # 连接信号
        widget.visibility_toggled.connect(self._on_layer_visibility_toggled)
        widget.delete_clicked.connect(self._on_layer_delete_clicked)
        
        # 设置工具提示
        if is_root:
            widget.setToolTip(self.tr.tr('layers_panel.root_layer_tooltip'))
        elif is_out_of_bounds:
            widget.setToolTip(self.tr.tr('layers_panel.out_of_bounds_tooltip'))
        
        # 添加到列表
        self.layers_list.addItem(item)
        self.layers_list.setItemWidget(item, widget)
        
        # 设置项的高度
        item.setSizeHint(widget.sizeHint())
    
    def _on_layer_visibility_toggled(self, layer_id: str, visible: bool):
        """图层可见性被切换"""
        self.layer_visibility_changed.emit(layer_id, visible)
    
    def _on_layer_delete_clicked(self, layer_id: str):
        """图层删除按钮被点击"""
        self.layer_deleted.emit(layer_id)
    
    def remove_layer(self, layer_id: str):
        """
        从列表中移除图层
        
        Args:
            layer_id: 图层 ID
        """
        for i in range(self.layers_list.count()):
            item = self.layers_list.item(i)
            if item.data(Qt.UserRole) == layer_id:
                self.layers_list.takeItem(i)
                break
    
    def clear_layers(self):
        """清空图层列表"""
        self.layers_list.clear()
    
    def set_active_layer(self, layer_id: str):
        """
        设置激活的图层
        
        Args:
            layer_id: 图层 ID
        """
        # 阻止信号，避免触发 _on_selection_changed
        self.layers_list.blockSignals(True)
        
        # 清除当前选择
        self.layers_list.clearSelection()
        
        # 选中指定图层
        for i in range(self.layers_list.count()):
            item = self.layers_list.item(i)
            if item.data(Qt.UserRole) == layer_id:
                item.setSelected(True)
                # 确保可见
                self.layers_list.scrollToItem(item)
                break
        
        # 恢复信号
        self.layers_list.blockSignals(False)
    
    def update_layer_name(self, layer_id: str, name: str):
        """
        更新图层名称
        
        Args:
            layer_id: 图层 ID
            name: 新名称
        """
        for i in range(self.layers_list.count()):
            item = self.layers_list.item(i)
            if item.data(Qt.UserRole) == layer_id:
                widget = self.layers_list.itemWidget(item)
                if widget:
                    widget.set_name(name)
                break
    
    def update_layer_visibility(self, layer_id: str, visible: bool):
        """
        更新图层可见性
        
        Args:
            layer_id: 图层 ID
            visible: 是否可见
        """
        for i in range(self.layers_list.count()):
            item = self.layers_list.item(i)
            if item.data(Qt.UserRole) == layer_id:
                widget = self.layers_list.itemWidget(item)
                if widget:
                    widget.set_visible(visible)
                break
    
    def set_save_button_enabled(self, enabled: bool):
        """
        设置保存选区按钮的启用状态
        
        Args:
            enabled: 是否启用
        """
        self.save_selection_button.setEnabled(enabled)
