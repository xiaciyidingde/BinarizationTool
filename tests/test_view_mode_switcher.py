"""
视图模式切换器测试

包括单元测试和基于属性的测试（Hypothesis）
"""

import pytest
from hypothesis import given, strategies as st
from PySide6.QtWidgets import QApplication
from src.views.view_mode_switcher import ViewModeSwitcher


# 确保 QApplication 实例存在
@pytest.fixture(scope="module")
def qapp():
    """创建 QApplication 实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ============================================================================
# 单元测试
# ============================================================================

def test_view_mode_switcher_initialization(qapp):
    """测试视图模式切换器初始化"""
    switcher = ViewModeSwitcher()
    
    # 默认应该是二值化模式
    assert switcher.get_current_mode() == 'binary'
    assert switcher.binary_button.isChecked()


def test_set_mode_original(qapp):
    """测试设置原图模式"""
    switcher = ViewModeSwitcher()
    
    switcher.set_mode('original')
    
    assert switcher.get_current_mode() == 'original'
    assert switcher.original_button.isChecked()
    assert not switcher.preprocessed_button.isChecked()
    assert not switcher.binary_button.isChecked()


def test_set_mode_preprocessed(qapp):
    """测试设置预处理模式"""
    switcher = ViewModeSwitcher()
    
    switcher.set_mode('preprocessed')
    
    assert switcher.get_current_mode() == 'preprocessed'
    assert not switcher.original_button.isChecked()
    assert switcher.preprocessed_button.isChecked()
    assert not switcher.binary_button.isChecked()


def test_set_mode_binary(qapp):
    """测试设置二值化模式"""
    switcher = ViewModeSwitcher()
    switcher.set_mode('original')  # 先切换到其他模式
    
    switcher.set_mode('binary')
    
    assert switcher.get_current_mode() == 'binary'
    assert not switcher.original_button.isChecked()
    assert not switcher.preprocessed_button.isChecked()
    assert switcher.binary_button.isChecked()


def test_set_mode_invalid(qapp):
    """测试设置无效模式"""
    switcher = ViewModeSwitcher()
    
    with pytest.raises(ValueError):
        switcher.set_mode('invalid_mode')


def test_button_click_emits_signal(qapp):
    """测试按钮点击发射信号"""
    switcher = ViewModeSwitcher()
    
    # 记录信号
    signals_received = []
    switcher.mode_changed.connect(lambda mode: signals_received.append(mode))
    
    # 点击原图按钮
    switcher.original_button.click()
    
    assert len(signals_received) == 1
    assert signals_received[0] == 'original'
    assert switcher.get_current_mode() == 'original'


def test_button_click_same_mode_no_signal(qapp):
    """测试点击当前模式按钮不发射信号"""
    switcher = ViewModeSwitcher()
    
    # 记录信号
    signals_received = []
    switcher.mode_changed.connect(lambda mode: signals_received.append(mode))
    
    # 点击已选中的二值化按钮
    switcher.binary_button.click()
    
    # 不应该发射信号
    assert len(signals_received) == 0


def test_mode_switching_sequence(qapp):
    """测试模式切换序列"""
    switcher = ViewModeSwitcher()
    
    signals_received = []
    switcher.mode_changed.connect(lambda mode: signals_received.append(mode))
    
    # 切换序列：binary -> original -> preprocessed -> binary
    switcher.original_button.click()
    switcher.preprocessed_button.click()
    switcher.binary_button.click()
    
    assert signals_received == ['original', 'preprocessed', 'binary']
    assert switcher.get_current_mode() == 'binary'


def test_set_mode_does_not_emit_signal(qapp):
    """测试 set_mode 不发射信号"""
    switcher = ViewModeSwitcher()
    
    signals_received = []
    switcher.mode_changed.connect(lambda mode: signals_received.append(mode))
    
    # 使用 set_mode 切换
    switcher.set_mode('original')
    
    # 不应该发射信号
    assert len(signals_received) == 0
    assert switcher.get_current_mode() == 'original'


def test_button_group_exclusivity(qapp):
    """测试按钮组的互斥性"""
    switcher = ViewModeSwitcher()
    
    # 点击原图按钮
    switcher.original_button.click()
    
    # 只有原图按钮应该被选中
    assert switcher.original_button.isChecked()
    assert not switcher.preprocessed_button.isChecked()
    assert not switcher.binary_button.isChecked()
    
    # 点击预处理按钮
    switcher.preprocessed_button.click()
    
    # 只有预处理按钮应该被选中
    assert not switcher.original_button.isChecked()
    assert switcher.preprocessed_button.isChecked()
    assert not switcher.binary_button.isChecked()


def test_button_tooltips(qapp):
    """测试按钮提示文本"""
    switcher = ViewModeSwitcher()
    
    assert "Ctrl+1" in switcher.original_button.toolTip()
    assert "Ctrl+2" in switcher.preprocessed_button.toolTip()
    assert "Ctrl+3" in switcher.binary_button.toolTip()


# ============================================================================
# Hypothesis 属性测试
# ============================================================================

# 定义有效模式的策略
valid_modes = st.sampled_from(['original', 'preprocessed', 'binary'])


@given(mode=valid_modes)
def test_property_set_mode_updates_current_mode(qapp, mode):
    """
    属性：set_mode 总是正确更新当前模式
    """
    switcher = ViewModeSwitcher()
    
    switcher.set_mode(mode)
    
    assert switcher.get_current_mode() == mode


@given(mode=valid_modes)
def test_property_set_mode_updates_button_state(qapp, mode):
    """
    属性：set_mode 总是正确更新按钮选中状态
    """
    switcher = ViewModeSwitcher()
    
    switcher.set_mode(mode)
    
    # 检查对应的按钮被选中
    if mode == 'original':
        assert switcher.original_button.isChecked()
        assert not switcher.preprocessed_button.isChecked()
        assert not switcher.binary_button.isChecked()
    elif mode == 'preprocessed':
        assert not switcher.original_button.isChecked()
        assert switcher.preprocessed_button.isChecked()
        assert not switcher.binary_button.isChecked()
    elif mode == 'binary':
        assert not switcher.original_button.isChecked()
        assert not switcher.preprocessed_button.isChecked()
        assert switcher.binary_button.isChecked()


@given(modes=st.lists(valid_modes, min_size=1, max_size=20))
def test_property_mode_sequence_consistency(qapp, modes):
    """
    属性：任意模式切换序列后，当前模式总是最后设置的模式
    """
    switcher = ViewModeSwitcher()
    
    for mode in modes:
        switcher.set_mode(mode)
    
    # 当前模式应该是最后一个
    assert switcher.get_current_mode() == modes[-1]


@given(mode=valid_modes)
def test_property_button_click_changes_mode(qapp, mode):
    """
    属性：点击按钮总是改变模式（如果不是当前模式）
    """
    switcher = ViewModeSwitcher()
    
    # 先设置为不同的模式
    if mode != 'binary':
        switcher.set_mode('binary')
    else:
        switcher.set_mode('original')
    
    initial_mode = switcher.get_current_mode()
    
    # 点击对应的按钮
    if mode == 'original':
        switcher.original_button.click()
    elif mode == 'preprocessed':
        switcher.preprocessed_button.click()
    elif mode == 'binary':
        switcher.binary_button.click()
    
    # 模式应该改变
    assert switcher.get_current_mode() == mode
    assert switcher.get_current_mode() != initial_mode


@given(modes=st.lists(valid_modes, min_size=2, max_size=10))
def test_property_signal_count_matches_mode_changes(qapp, modes):
    """
    属性：发射的信号数量等于实际的模式改变次数
    """
    switcher = ViewModeSwitcher()
    
    signals_received = []
    switcher.mode_changed.connect(lambda mode: signals_received.append(mode))
    
    # 模拟按钮点击
    for mode in modes:
        if mode == 'original':
            switcher.original_button.click()
        elif mode == 'preprocessed':
            switcher.preprocessed_button.click()
        elif mode == 'binary':
            switcher.binary_button.click()
    
    # 计算实际的模式改变次数
    actual_changes = 0
    current = 'binary'  # 初始模式
    for mode in modes:
        if mode != current:
            actual_changes += 1
            current = mode
    
    # 信号数量应该等于实际改变次数
    assert len(signals_received) == actual_changes


@given(mode=valid_modes)
def test_property_only_one_button_checked(qapp, mode):
    """
    属性：任何时候只有一个按钮被选中
    """
    switcher = ViewModeSwitcher()
    
    switcher.set_mode(mode)
    
    # 计算选中的按钮数量
    checked_count = sum([
        switcher.original_button.isChecked(),
        switcher.preprocessed_button.isChecked(),
        switcher.binary_button.isChecked()
    ])
    
    assert checked_count == 1


@given(
    mode1=valid_modes,
    mode2=valid_modes
)
def test_property_mode_transition_idempotent(qapp, mode1, mode2):
    """
    属性：从 mode1 切换到 mode2 是幂等的
    """
    switcher = ViewModeSwitcher()
    
    # 第一次切换
    switcher.set_mode(mode1)
    switcher.set_mode(mode2)
    result1 = switcher.get_current_mode()
    
    # 第二次切换（相同的序列）
    switcher.set_mode(mode1)
    switcher.set_mode(mode2)
    result2 = switcher.get_current_mode()
    
    # 结果应该相同
    assert result1 == result2 == mode2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
