"""
带动画的选项卡组件

自定义的 QTabWidget，支持页面切换时的淡入淡出动画。
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QTabWidget

from ..utils.animations import is_global_animation_enabled


class AnimatedTabWidget(QTabWidget):
    """
    带动画的选项卡组件

    在切换页面时提供淡入淡出效果。
    """

    def __init__(self, parent=None):
        """初始化带动画的选项卡"""
        super().__init__(parent)

        # 为每个页面创建透明度效果
        self._opacity_effects = {}
        self._animations = {}

        # 连接信号
        self.currentChanged.connect(self._on_current_changed)

        # 记录上一个索引
        self._previous_index = -1

    def addTab(self, widget, label):
        """重写 addTab 以添加透明度效果"""
        index = super().addTab(widget, label)

        # 为新页面创建透明度效果
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setOpacity(1.0)
        widget.setGraphicsEffect(opacity_effect)

        self._opacity_effects[index] = opacity_effect

        # 创建动画
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animations[index] = animation

        return index

    def insertTab(self, index, widget, label):
        """重写 insertTab 以添加透明度效果"""
        result = super().insertTab(index, widget, label)

        # 为新页面创建透明度效果
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setOpacity(1.0)
        widget.setGraphicsEffect(opacity_effect)

        # 重新索引所有效果和动画
        self._reindex_effects()

        return result

    def removeTab(self, index):
        """重写 removeTab 以清理透明度效果"""
        super().removeTab(index)

        # 清理效果和动画
        if index in self._opacity_effects:
            del self._opacity_effects[index]
        if index in self._animations:
            del self._animations[index]

        # 重新索引
        self._reindex_effects()

    def _reindex_effects(self):
        """重新索引所有效果和动画"""
        new_effects = {}
        new_animations = {}

        for i in range(self.count()):
            widget = self.widget(i)
            effect = widget.graphicsEffect()
            if effect and isinstance(effect, QGraphicsOpacityEffect):
                new_effects[i] = effect
                # 查找对应的动画
                for anim in self._animations.values():
                    if anim.targetObject() == effect:
                        new_animations[i] = anim
                        break

        self._opacity_effects = new_effects
        self._animations = new_animations

    def _on_current_changed(self, index):
        """页面切换时的处理"""
        if index < 0 or index not in self._opacity_effects:
            return

        if not is_global_animation_enabled():
            # 动画禁用，直接显示
            self._opacity_effects[index].setOpacity(1.0)
            return

        # 停止当前动画
        if index in self._animations:
            self._animations[index].stop()

        # 播放淡入动画
        animation = self._animations[index]
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start()

        # 更新上一个索引
        self._previous_index = index

