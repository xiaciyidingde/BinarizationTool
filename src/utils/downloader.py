"""
通用文件下载工具

支持从 ModelScope 和 HuggingFace 下载文件。
"""

import os
import shutil
import tempfile
from typing import Optional, Callable


class Downloader:
    """
    通用文件下载器
    
    支持从多个源下载文件。
    """
    
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        """
        初始化下载器
        
        Args:
            progress_callback: 进度回调函数，接收 (状态消息, 进度百分比)
        """
        self.progress_callback = progress_callback
        self.should_cancel = False
    
    def _report_progress(self, message: str, progress: int = 0):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(message, progress)
        print(f"[{progress}%] {message}")
    
    def cancel(self):
        """取消下载"""
        self.should_cancel = True
    
    def _download_from_modelscope(self, model_id: str, file_path: str, temp_dir: str) -> Optional[str]:
        """
        从 ModelScope 下载文件
        
        Args:
            model_id: 模型 ID
            file_path: 文件路径
            temp_dir: 临时目录
            
        Returns:
            下载的文件路径，失败返回 None
        """
        try:
            from modelscope.hub.file_download import model_file_download
            import threading
            import time
            
            self._report_progress("正在从 ModelScope 下载...", 10)
            
            if self.should_cancel:
                return None
            
            # 用于存储下载结果
            result = {'path': None, 'error': None, 'completed': False}
            
            def download_thread():
                try:
                    result['path'] = model_file_download(
                        model_id=model_id,
                        file_path=file_path,
                        local_dir=temp_dir
                    )
                    result['completed'] = True
                except Exception as e:
                    result['error'] = e
                    result['completed'] = True
            
            # 启动下载线程
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
            
            # 模拟进度更新（从 10% 到 75%）
            progress = 10
            while thread.is_alive() and progress < 75:
                if self.should_cancel:
                    # 不等待线程，直接返回（线程会在后台继续但不影响UI）
                    self._report_progress("取消下载...", 0)
                    return None
                time.sleep(0.5)
                progress += 2
                self._report_progress("正在从 ModelScope 下载...", progress)
            
            # 等待下载完成，但使用超时
            thread.join(timeout=300)  # 最多等待5分钟
            
            # 如果线程还在运行，说明超时了
            if thread.is_alive():
                self._report_progress("下载超时", 0)
                return None
            
            if result['error']:
                raise result['error']
            
            if self.should_cancel:
                return None
            
            self._report_progress("ModelScope 下载完成", 80)
            return result['path']
            
        except ImportError:
            self._report_progress("ModelScope 未安装，跳过", 0)
            return None
        except Exception as e:
            self._report_progress(f"ModelScope 下载失败: {e}", 0)
            return None
    
    def _download_from_huggingface(self, repo_id: str, filename: str, temp_dir: str) -> Optional[str]:
        """
        从 HuggingFace 下载文件
        
        Args:
            repo_id: 仓库 ID
            filename: 文件名
            temp_dir: 临时目录
            
        Returns:
            下载的文件路径，失败返回 None
        """
        try:
            from huggingface_hub import hf_hub_download
            import threading
            import time
            
            self._report_progress("正在从 HuggingFace 下载...", 10)
            
            if self.should_cancel:
                return None
            
            # 用于存储下载结果
            result = {'path': None, 'error': None, 'completed': False}
            
            def download_thread():
                try:
                    result['path'] = hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        local_dir=temp_dir,
                        local_dir_use_symlinks=False
                    )
                    result['completed'] = True
                except Exception as e:
                    result['error'] = e
                    result['completed'] = True
            
            # 启动下载线程
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
            
            # 模拟进度更新（从 10% 到 75%）
            progress = 10
            while thread.is_alive() and progress < 75:
                if self.should_cancel:
                    # 不等待线程，直接返回（线程会在后台继续但不影响UI）
                    self._report_progress("取消下载...", 0)
                    return None
                time.sleep(0.5)
                progress += 2
                self._report_progress("正在从 HuggingFace 下载...", progress)
            
            # 等待下载完成，但使用超时
            thread.join(timeout=300)  # 最多等待5分钟
            
            # 如果线程还在运行，说明超时了
            if thread.is_alive():
                self._report_progress("下载超时", 0)
                return None
            
            if result['error']:
                raise result['error']
            
            if self.should_cancel:
                return None
            
            self._report_progress("HuggingFace 下载完成", 80)
            return result['path']
            
        except ImportError:
            self._report_progress("HuggingFace Hub 未安装，跳过", 0)
            return None
        except Exception as e:
            self._report_progress(f"HuggingFace 下载失败: {e}", 0)
            return None
    
    def _find_onnx_file(self, directory: str) -> Optional[str]:
        """
        在目录中查找 .onnx 文件
        
        Args:
            directory: 搜索目录
            
        Returns:
            找到的 .onnx 文件路径，未找到返回 None
        """
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.onnx'):
                    return os.path.join(root, file)
        return None
    
    def download_rmbg_model(self, target_dir: str, target_filename: str = "RMBG-2.0-q4f16.onnx") -> bool:
        """
        下载 RMBG-2.0 模型
        
        Args:
            target_dir: 目标目录（程序的 data/model 目录）
            target_filename: 目标文件名
            
        Returns:
            True 如果下载成功，否则 False
        """
        self.should_cancel = False
        temp_dir = None
        
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="rmbg_download_")
            self._report_progress("创建临时目录", 5)
            
            if self.should_cancel:
                return False
            
            # 尝试从 ModelScope 下载（国内快）
            model_path = self._download_from_modelscope(
                model_id='AI-ModelScope/RMBG-2.0',
                file_path='onnx/model_q4f16.onnx',
                temp_dir=temp_dir
            )
            
            # 如果失败，尝试 HuggingFace
            if not model_path or not os.path.exists(model_path):
                if self.should_cancel:
                    return False
                
                model_path = self._download_from_huggingface(
                    repo_id='briaai/RMBG-2.0',
                    filename='onnx/model_q4f16.onnx',
                    temp_dir=temp_dir
                )
            
            if self.should_cancel:
                return False
            
            # 如果还是失败，尝试在临时目录中查找 .onnx 文件
            if not model_path or not os.path.exists(model_path):
                self._report_progress("在临时目录中查找模型文件...", 85)
                model_path = self._find_onnx_file(temp_dir)
            
            if not model_path or not os.path.exists(model_path):
                self._report_progress("下载失败：未找到模型文件", 0)
                return False
            
            if self.should_cancel:
                return False
            
            # 创建目标目录
            os.makedirs(target_dir, exist_ok=True)
            
            # 复制文件到目标位置并重命名
            target_path = os.path.join(target_dir, target_filename)
            self._report_progress("正在复制文件到目标位置...", 90)
            
            shutil.copy2(model_path, target_path)
            
            if self.should_cancel:
                # 如果取消，删除已复制的文件
                if os.path.exists(target_path):
                    os.remove(target_path)
                return False
            
            # 验证文件大小
            file_size = os.path.getsize(target_path) / (1024 ** 2)  # MB
            self._report_progress(f"下载完成！文件大小: {file_size:.1f} MB", 100)
            
            return True
            
        except Exception as e:
            self._report_progress(f"下载失败: {e}", 0)
            return False
            
        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

