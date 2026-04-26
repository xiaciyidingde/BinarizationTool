"""
模型下载对话框

提供模型下载的 UI 界面。
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QMessageBox,
)

from ..utils.translation_manager import get_translator
from ..utils.downloader import Downloader
from ..utils.window_utils import apply_dark_titlebar


class DownloadWorker(QThread):
    """下载工作线程"""
    
    progress_updated = Signal(str, int)  # 消息, 进度
    download_finished = Signal(bool)  # 成功/失败
    
    def __init__(self, model_type: str, target_dir: str, target_filename: str = None, model_variant: str = None):
        """
        初始化下载工作线程
        
        Args:
            model_type: 模型类型 ('rmbg' 或 'sam2')
            target_dir: 目标目录
            target_filename: 目标文件名（仅用于RMBG）
            model_variant: 模型变体（仅用于SAM2: 'tiny', 'small', 'base_plus', 'large'）
        """
        super().__init__()
        self.model_type = model_type
        self.target_dir = target_dir
        self.target_filename = target_filename
        self.model_variant = model_variant
        self.downloader = None
    
    def run(self):
        """执行下载"""
        def progress_callback(message, progress):
            self.progress_updated.emit(message, progress)
        
        self.downloader = Downloader(progress_callback)
        
        if self.model_type == 'rmbg':
            success = self.downloader.download_rmbg_model(self.target_dir, self.target_filename)
        elif self.model_type == 'sam2':
            success = self.downloader.download_sam2_model(self.target_dir, self.model_variant or 'small')
        else:
            success = False
        
        self.download_finished.emit(success)
    
    def cancel(self):
        """取消下载"""
        if self.downloader:
            self.downloader.cancel()


class ModelDownloadDialog(QDialog):
    """
    模型下载对话框
    """
    
    def __init__(self, model_type: str, target_dir: str, target_filename: str = None, model_variant: str = None, parent=None):
        """
        初始化对话框
        
        Args:
            model_type: 模型类型 ('rmbg' 或 'sam2')
            target_dir: 目标目录
            target_filename: 目标文件名（仅用于RMBG）
            model_variant: 模型变体（仅用于SAM2）
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.tr = get_translator()
        self.model_type = model_type
        self.target_dir = target_dir
        self.target_filename = target_filename
        self.model_variant = model_variant
        self.worker = None
        self.download_success = False
        
        # 根据模型类型设置标题
        if model_type == 'sam2':
            title = self.tr.tr('model_download.title_sam2')
        else:
            title = self.tr.tr('model_download.title')
        self.setWindowTitle(title)
        
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        apply_dark_titlebar(self)
    
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(self.tr.tr('model_download.title'))
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 根据模型类型生成说明文本
        if self.model_type == 'rmbg':
            info_text = self._get_rmbg_info_text()
        elif self.model_type == 'sam2':
            info_text = self._get_sam2_info_text()
        else:
            info_text = "未知模型类型"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_label.setObjectName("infoLabel")
        info_label.setOpenExternalLinks(True)  # 允许打开外部链接
        info_label.setTextFormat(Qt.RichText)  # 支持富文本格式
        layout.addWidget(info_label)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始隐藏
        layout.addWidget(self.progress_bar)
        
        # 日志文本框（初始隐藏）
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setVisible(False)  # 初始隐藏
        layout.addWidget(self.log_text)
        
        # 添加弹性空间，将按钮推到底部
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_btn = QPushButton(self.tr.tr('model_download.start_download'))
        self.download_btn.setMinimumSize(120, 35)
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton(self.tr.tr('model_download.cancel'))
        self.cancel_btn.setMinimumSize(120, 35)
        self.cancel_btn.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _get_rmbg_info_text(self) -> str:
        """获取RMBG模型的说明文本"""
        return (
            f"{self.tr.tr('model_download.description')}<br><br>"
            f"{self.tr.tr('model_download.model_size')}<br>"
            f"{self.tr.tr('model_download.license')}<br>"
            f"{self.tr.tr('model_download.commercial_contact')}"
            f"<a href='https://bria.ai/'>https://bria.ai/</a><br><br>"
            f"{self.tr.tr('model_download.download_hint')}<br><br>"
            f"{self.tr.tr('model_download.download_links')}<br>"
            f"{self.tr.tr('model_download.modelscope')}"
            f"<a href='https://modelscope.cn/models/AI-ModelScope/RMBG-2.0'>https://modelscope.cn/models/AI-ModelScope/RMBG-2.0</a><br>"
            f"{self.tr.tr('model_download.huggingface')}"
            f"<a href='https://huggingface.co/briaai/RMBG-2.0'>https://huggingface.co/briaai/RMBG-2.0</a><br><br>"
            f"{self.tr.tr('model_download.manual_download')}"
        )
    
    def _get_sam2_info_text(self) -> str:
        """获取SAM2模型的说明文本"""
        variant_name = self.model_variant or 'small'
        
        # 获取翻译后的变体名称和大小
        variant_key = f'sam2_variant_{variant_name}'
        size_key = f'sam2_size_{variant_name}'
        variant_display = self.tr.tr(f'model_download.{variant_key}')
        model_size = self.tr.tr(f'model_download.{size_key}')
        
        # 构建信息文本
        info_text = f"<b>{self.tr.tr('model_download.sam2_info_title')}</b><br><br>"
        info_text += self.tr.tr('model_download.sam2_variant', variant=variant_display) + "<br>"
        info_text += self.tr.tr('model_download.sam2_size', size=model_size) + "<br>"
        info_text += self.tr.tr('model_download.sam2_license') + "<br><br>"
        info_text += self.tr.tr('model_download.sam2_description') + "<br><br>"
        info_text += self.tr.tr('model_download.sam2_download_source') + "<br>"
        info_text += self.tr.tr('model_download.sam2_model_link')
        info_text += "<a href='https://huggingface.co/vietanhdev/segment-anything-2-onnx-models'>"
        info_text += "https://huggingface.co/vietanhdev/segment-anything-2-onnx-models</a><br><br>"
        info_text += self.tr.tr('model_download.sam2_download_hint') + "<br>"
        info_text += self.tr.tr('model_download.sam2_save_location')
        
        return info_text
    
    def start_download(self):
        """开始下载"""
        # 显示进度条和日志
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        
        # 禁用下载按钮
        self.download_btn.setEnabled(False)
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # 创建工作线程
        self.worker = DownloadWorker(
            self.model_type,
            self.target_dir,
            self.target_filename,
            self.model_variant
        )
        self.worker.progress_updated.connect(self.on_progress)
        self.worker.download_finished.connect(self.on_finished)
        self.worker.start()
    
    def cancel_download(self):
        """取消下载"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                self.tr.tr('model_download.confirm_cancel'),
                self.tr.tr('model_download.confirm_cancel_message'),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.log_text.append(self.tr.tr('model_download.canceling'))
                # 设置取消标志
                self.worker.cancel()
                # 等待线程结束（最多等待3秒）
                if not self.worker.wait(3000):
                    # 如果3秒后还没结束，强制终止（注意：这可能导致资源泄漏）
                    self.log_text.append("强制终止下载线程...")
                    self.worker.terminate()
                    self.worker.wait()
                self.reject()
        else:
            self.reject()
    
    def on_progress(self, message: str, progress: int):
        """进度更新"""
        self.log_text.append(f"[{progress}%] {message}")
        self.progress_bar.setValue(progress)
        
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def on_finished(self, success: bool):
        """下载完成"""
        self.download_success = success
        
        if success:
            self.log_text.append(self.tr.tr('model_download.download_success'))
            self.download_btn.setText(self.tr.tr('model_download.complete'))
            self.cancel_btn.setText(self.tr.tr('model_download.close'))
            
            # 不在这里显示提示框，让调用者处理
            self.accept()
        else:
            self.log_text.append(self.tr.tr('model_download.download_failed'))
            self.download_btn.setEnabled(True)
            
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('model_download.download_failed_message')
            )
    
    def is_download_success(self) -> bool:
        """返回下载是否成功"""
        return self.download_success
