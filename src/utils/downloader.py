"""
通用文件下载工具

支持从 ModelScope 和 HuggingFace 下载文件。
"""

import os
import shutil
import tempfile
import urllib.request
import urllib.error
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
    
    def _download_with_progress(self, url: str, output_path: str, desc: str = "下载中") -> bool:
        """
        使用 urllib 下载文件，支持进度显示和取消
        
        Args:
            url: 下载 URL
            output_path: 输出文件路径
            desc: 描述文本
            
        Returns:
            True 如果下载成功，否则 False
        """
        try:
            # 发送请求
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=30) as response:
                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size == 0:
                    self._report_progress(f"{desc}（大小未知）...", 10)
                else:
                    size_mb = total_size / (1024 * 1024)
                    self._report_progress(f"{desc}（{size_mb:.1f} MB）...", 10)
                
                # 下载文件
                downloaded = 0
                chunk_size = 8192
                
                with open(output_path, 'wb') as f:
                    while True:
                        if self.should_cancel:
                            self._report_progress("下载已取消", 0)
                            # 删除未完成的文件
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            return False
                        
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新进度（10% - 75%）
                        if total_size > 0:
                            progress = 10 + int((downloaded / total_size) * 65)
                            self._report_progress(f"{desc}... {downloaded / (1024*1024):.1f}/{size_mb:.1f} MB", progress)
                
                return True
                
        except urllib.error.URLError as e:
            self._report_progress(f"下载失败: {e}", 0)
            return False
        except Exception as e:
            self._report_progress(f"下载失败: {e}", 0)
            return False
    
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
            # 尝试使用 modelscope SDK
            try:
                from modelscope.hub.file_download import model_file_download
                
                self._report_progress("正在从 ModelScope 下载...", 10)
                
                if self.should_cancel:
                    return None
                
                result_path = model_file_download(
                    model_id=model_id,
                    file_path=file_path,
                    local_dir=temp_dir
                )
                
                if self.should_cancel:
                    self._report_progress("下载已取消", 0)
                    return None
                
                self._report_progress("ModelScope 下载完成", 80)
                return result_path
                
            except ImportError:
                # 如果没有 SDK，尝试直接下载
                self._report_progress("ModelScope SDK 未安装，尝试直接下载...", 5)
                
                # 构建直接下载 URL
                # ModelScope 的文件 URL 格式：https://modelscope.cn/api/v1/models/{model_id}/repo?Revision=master&FilePath={file_path}
                url = f"https://modelscope.cn/api/v1/models/{model_id}/repo?Revision=master&FilePath={file_path}"
                
                output_path = os.path.join(temp_dir, os.path.basename(file_path))
                
                if self._download_with_progress(url, output_path, "从 ModelScope 下载"):
                    self._report_progress("ModelScope 下载完成", 80)
                    return output_path
                else:
                    return None
            
        except Exception as e:
            if self.should_cancel:
                self._report_progress("下载已取消", 0)
                return None
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
            # 尝试使用 huggingface_hub SDK
            try:
                from huggingface_hub import hf_hub_download
                
                self._report_progress("正在从 HuggingFace 下载...", 10)
                
                if self.should_cancel:
                    return None
                
                result_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=temp_dir,
                    local_dir_use_symlinks=False
                )
                
                if self.should_cancel:
                    self._report_progress("下载已取消", 0)
                    return None
                
                self._report_progress("HuggingFace 下载完成", 80)
                return result_path
                
            except ImportError:
                # 如果没有 SDK，尝试直接下载
                self._report_progress("HuggingFace Hub 未安装，尝试直接下载...", 5)
                
                # 构建直接下载 URL
                # HuggingFace 的文件 URL 格式：https://huggingface.co/{repo_id}/resolve/main/{filename}
                url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
                
                output_path = os.path.join(temp_dir, os.path.basename(filename))
                
                if self._download_with_progress(url, output_path, "从 HuggingFace 下载"):
                    self._report_progress("HuggingFace 下载完成", 80)
                    return output_path
                else:
                    return None
            
        except Exception as e:
            if self.should_cancel:
                self._report_progress("下载已取消", 0)
                return None
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
