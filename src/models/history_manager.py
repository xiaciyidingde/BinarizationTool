"""
历史管理模块

实现撤销/重做功能，管理图片编辑历史状态。
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .image_data import ImageData


class HistoryManager:
    """
    历史管理器类

    使用历史列表和当前位置指针管理编辑历史：
    - history: 存储所有历史状态
    - current_index: 指向当前状态的索引

    当执行新编辑时，清空当前位置之后的所有历史。
    """

    def __init__(self, max_history: int = 50):
        """
        初始化历史管理器

        Args:
            max_history: 最大历史记录数，默认 50
        """
        self.history: list[ImageData] = []
        self.current_index: int = -1  # -1 表示没有历史
        self.max_history = max_history

    def push_state(self, image_data: 'ImageData'):
        """
        保存当前状态到历史

        新编辑操作会清空当前位置之后的所有历史。
        如果历史超过最大限制，移除最旧的状态。

        Args:
            image_data: 要保存的 ImageData 对象（会进行深拷贝）
        """
        # 深拷贝图片数据
        state = image_data.copy()

        # 清空当前位置之后的所有历史（新编辑会使后续历史失效）
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]

        # 添加新状态
        self.history.append(state)
        self.current_index = len(self.history) - 1

        # 限制历史大小
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def undo(self, current_state: 'ImageData') -> Optional['ImageData']:
        """
        撤销操作

        Args:
            current_state: 当前状态（如果当前状态不在历史中，先保存它）

        Returns:
            撤销后的 ImageData 对象，如果无法撤销则返回 None
        """
        if not self.can_undo():
            return None

        # 如果当前索引指向最后一个状态，说明当前状态可能已经被修改
        # 需要先保存当前状态（但不移动索引）
        # 检查当前状态是否与历史中的最后一个状态不同
        # 如果不同，说明有未保存的修改，需要先保存
        if self.current_index == len(self.history) - 1 and not self._states_equal(current_state, self.history[self.current_index]):
            self.history.append(current_state.copy())

        # 向前移动索引
        self.current_index -= 1

        # 返回前一个状态的副本
        return self.history[self.current_index].copy()

    def redo(self) -> Optional['ImageData']:
        """
        重做操作

        Returns:
            重做后的 ImageData 对象，如果无法重做则返回 None
        """
        if not self.can_redo():
            return None

        # 向后移动索引
        self.current_index += 1

        # 返回下一个状态的副本
        return self.history[self.current_index].copy()

    def can_undo(self) -> bool:
        """
        检查是否可以撤销

        Returns:
            True 如果有可撤销的历史，否则 False
        """
        return self.current_index > 0

    def can_redo(self) -> bool:
        """
        检查是否可以重做

        Returns:
            True 如果有可重做的历史，否则 False
        """
        return self.current_index < len(self.history) - 1

    def clear(self):
        """
        清空所有历史记录

        用于加载新图片时重置历史。
        """
        self.history.clear()
        self.current_index = -1

    def get_undo_count(self) -> int:
        """
        获取可撤销的操作数量

        Returns:
            可撤销的步数
        """
        return self.current_index

    def get_redo_count(self) -> int:
        """
        获取可重做的操作数量

        Returns:
            可重做的步数
        """
        return len(self.history) - self.current_index - 1

    def _states_equal(self, state1: 'ImageData', state2: 'ImageData') -> bool:
        """
        比较两个状态是否相等

        Args:
            state1: 第一个状态
            state2: 第二个状态

        Returns:
            True 如果两个状态相等
        """
        import numpy as np
        return np.array_equal(state1.pixels, state2.pixels)
