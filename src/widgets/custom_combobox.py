"""
自定义下拉框组件

修复下拉列表位置显示异常的问题。
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QListView, QStyle, QStyledItemDelegate


class CustomComboBoxDelegate(QStyledItemDelegate):
    """自定义下拉框项目代理，用于自定义选中样式"""

    def paint(self, painter, option, index):
        """绘制项目"""
        # 如果是分隔线，绘制一条线
        if index.data(Qt.AccessibleDescriptionRole) == "separator":
            painter.save()
            painter.setPen(QColor("#dee2e6"))
            y = option.rect.center().y()
            painter.drawLine(option.rect.left(), y, option.rect.right(), y)
            painter.restore()
            return

        # 绘制背景
        if option.state & QStyle.State_Selected:
            # 选中时使用浅蓝色背景
            painter.fillRect(option.rect, QColor("#e7f3ff"))
        elif option.state & QStyle.State_MouseOver:
            # 悬停时使用浅灰色背景
            painter.fillRect(option.rect, QColor("#e9ecef"))
        else:
            # 默认白色背景
            painter.fillRect(option.rect, QColor("#ffffff"))

        # 绘制文本
        painter.save()
        if option.state & QStyle.State_Selected:
            # 选中时使用蓝色字体
            painter.setPen(QColor("#007bff"))
        else:
            # 默认黑色字体
            painter.setPen(QColor("#212529"))

        text = index.data(Qt.DisplayRole)
        painter.drawText(option.rect.adjusted(8, 0, -8, 0), Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        """返回项目大小"""
        # 如果是分隔线，返回较小的高度
        if index.data(Qt.AccessibleDescriptionRole) == "separator":
            return QSize(option.rect.width(), 1)
        return QSize(option.rect.width(), 28)


class CustomComboBox(QComboBox):
    """
    自定义下拉框

    修复下拉列表弹出位置计算错误的问题。
    """

    def __init__(self, parent=None):
        """初始化自定义下拉框"""
        super().__init__(parent)

        # 设置下拉列表视图
        list_view = QListView()
        list_view.setStyleSheet("""
            QListView {
                border: 1px solid #dee2e6;
                background-color: #ffffff;
                outline: none;
            }
        """)

        # 设置自定义代理
        delegate = CustomComboBoxDelegate(list_view)
        list_view.setItemDelegate(delegate)

        self.setView(list_view)

    def showPopup(self):
        """显示下拉列表，修复位置计算"""
        # 调用父类方法显示弹出框
        super().showPopup()

        # 获取弹出框（QListView）
        popup = self.view()
        if popup:
            # 计算正确的位置：下拉框的左下角
            pos = self.mapToGlobal(self.rect().bottomLeft())

            # 设置弹出框位置
            popup.window().move(pos)

            # 设置弹出框宽度与下拉框一致
            popup.window().setFixedWidth(self.width())


