"""
AI 模型处理器

提供通用的 AI 模型处理接口，支持多种模型的扩展。
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class AIProcessor(ABC):
    """
    AI 模型处理器基类
    
    所有 AI 模型处理器都应该继承此类并实现相应的方法。
    """
    
    def __init__(self, model_path: str):
        """
        初始化处理器
        
        Args:
            model_path: 模型文件路径
        """
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
    
    @abstractmethod
    def load_model(self, progress_callback=None) -> bool:
        """
        加载模型
        
        Args:
            progress_callback: 可选的进度回调函数，接收 0-100 的进度值
        
        Returns:
            True 如果加载成功，否则 False
        """
        pass
    
    @abstractmethod
    def process(self, image: np.ndarray) -> np.ndarray:
        """
        处理图像
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            
        Returns:
            处理后的图像 (H, W, 3) RGB 格式
        """
        pass
    
    @abstractmethod
    def unload_model(self):
        """卸载模型，释放资源"""
        pass
    
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载
        
        Returns:
            True 如果模型已加载
        """
        return self.is_loaded


class RMBGProcessor(AIProcessor):
    """
    RMBG 背景去除处理器
    
    使用 RMBG 模型进行背景去除。
    """
    
    def __init__(self, model_path: str):
        """
        初始化 RMBG 处理器
        
        Args:
            model_path: RMBG 模型文件路径（.onnx）
        """
        super().__init__(model_path)
        self.session = None
        self.input_size = (1024, 1024)  # RMBG 默认输入尺寸
    
    def load_model(self, progress_callback=None) -> bool:
        """
        加载 RMBG ONNX 模型
        
        Args:
            progress_callback: 可选的进度回调函数，接收 0-100 的进度值
        
        Returns:
            True 如果加载成功，否则 False
        """
        try:
            import onnxruntime as ort
            import os
            
            # 设置日志级别，抑制警告信息
            ort.set_default_logger_severity(3)  # 0=Verbose, 1=Info, 2=Warning, 3=Error, 4=Fatal
            
            if progress_callback:
                progress_callback(10)
            
            # 获取模型文件大小（用于估算加载进度）
            model_size = os.path.getsize(self.model_path) if os.path.exists(self.model_path) else 0
            is_large_model = model_size > 100 * 1024 * 1024  # 大于 100MB 视为大模型
            
            if progress_callback:
                progress_callback(20)
            
            # 创建 ONNX Runtime 会话
            # 对于大模型，这个过程可能需要较长时间
            if progress_callback and is_large_model:
                progress_callback(30)
            
            # 设置会话选项
            sess_options = ort.SessionOptions()
            # 对于某些模型，禁用图优化可以避免兼容性问题
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
            
            try:
                self.session = ort.InferenceSession(
                    self.model_path,
                    sess_options=sess_options,
                    providers=['CPUExecutionProvider']  # 使用 CPU，可以根据需要添加 GPU 支持
                )
            except Exception as e:
                # 如果禁用优化失败，尝试启用基本优化
                if "InsertedPrecisionFreeCast" in str(e) or "SimplifiedLayerNormFusion" in str(e):
                    print("尝试使用基本优化级别重新加载模型...")
                    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
                    self.session = ort.InferenceSession(
                        self.model_path,
                        sess_options=sess_options,
                        providers=['CPUExecutionProvider']
                    )
                else:
                    raise
            
            if progress_callback:
                progress_callback(90)
            
            self.is_loaded = True
            
            if progress_callback:
                progress_callback(100)
            
            return True
            
        except ImportError:
            print("onnxruntime 未安装")
            self.is_loaded = False
            return False
        except Exception as e:
            error_msg = str(e)
            if "InsertedPrecisionFreeCast" in error_msg or "SimplifiedLayerNormFusion" in error_msg:
                print(f"加载 RMBG 模型失败: 模型与当前 ONNX Runtime 不兼容")
            else:
                print(f"加载 RMBG 模型失败: {e}")
            self.is_loaded = False
            return False
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像
        
        Args:
            image: 输入图像 (H, W, 3) RGB
            
        Returns:
            预处理后的图像 (1, 3, H, W) 归一化到 [0, 1]
        """
        import cv2
        
        # 调整大小到模型输入尺寸
        resized = cv2.resize(image, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # 转换为 float32 并归一化到 [0, 1]
        normalized = resized.astype(np.float32) / 255.0
        
        # 转换为 (1, 3, H, W) 格式
        transposed = np.transpose(normalized, (2, 0, 1))
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def _postprocess(self, mask: np.ndarray, original_size: tuple) -> np.ndarray:
        """
        后处理掩码
        
        Args:
            mask: 模型输出的掩码 (1, 1, H, W)
            original_size: 原始图像尺寸 (H, W)
            
        Returns:
            处理后的掩码 (H, W) 值范围 [0, 255]
        """
        import cv2
        
        # 移除批次和通道维度
        mask = mask.squeeze()
        
        # 调整大小到原始尺寸
        h, w = original_size
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
        
        # 转换为 [0, 255] 范围
        mask = (mask * 255).astype(np.uint8)
        
        return mask
    
    def process(self, image: np.ndarray) -> np.ndarray:
        """
        处理图像，去除背景
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            
        Returns:
            去除背景后的图像 (H, W, 3) RGB 格式
        """
        if not self.is_loaded:
            raise RuntimeError("模型未加载，请先调用 load_model()")
        
        import cv2
        
        # 保存原始尺寸
        original_h, original_w = image.shape[:2]
        
        # 预处理
        input_tensor = self._preprocess(image)
        
        # 推理
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        mask = self.session.run([output_name], {input_name: input_tensor})[0]
        
        # 后处理
        mask = self._postprocess(mask, (original_h, original_w))
        
        # 优化掩码质量
        # 1. 使用 Otsu 自动阈值而不是固定阈值
        _, mask_binary = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 2. 形态学操作去除噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel, iterations=1)
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # 3. 边缘羽化（使用原始掩码的软边缘）
        # 将二值掩码转换为浮点
        mask_float = mask_binary.astype(np.float32) / 255.0
        
        # 使用原始掩码的软边缘信息
        mask_soft = mask.astype(np.float32) / 255.0
        
        # 在边缘区域使用软掩码，中心区域使用硬掩码
        # 检测边缘
        edges = cv2.Canny(mask_binary, 50, 150)
        edges_dilated = cv2.dilate(edges, kernel, iterations=3)
        edge_mask = (edges_dilated > 0).astype(np.float32)
        
        # 混合硬掩码和软掩码
        final_mask = mask_float * (1 - edge_mask) + mask_soft * edge_mask
        
        # 4. 轻微高斯模糊使边缘更自然
        final_mask = cv2.GaussianBlur(final_mask, (3, 3), 0.5)
        
        # 应用掩码到原始图像
        # 将掩码扩展为 3 通道
        mask_3ch = np.stack([final_mask, final_mask, final_mask], axis=2)
        
        # 应用掩码（保留前景，背景变为白色）
        # 使用浮点运算以保持精度
        result = image.astype(np.float32) * mask_3ch + 255.0 * (1 - mask_3ch)
        
        return result.astype(np.uint8)
    
    def unload_model(self):
        """卸载模型，释放资源"""
        if self.session is not None:
            self.session = None
        self.is_loaded = False


class AIProcessorFactory:
    """
    AI 处理器工厂
    
    根据模型类型创建相应的处理器。
    """
    
    @staticmethod
    def create_processor(model_type: str, model_path: str) -> Optional[AIProcessor]:
        """
        创建 AI 处理器
        
        Args:
            model_type: 模型类型（'rmbg', 'other_model', ...）
            model_path: 模型文件路径
            
        Returns:
            AI 处理器实例，如果类型不支持则返回 None
        """
        if model_type.lower() == 'rmbg':
            return RMBGProcessor(model_path)
        # 未来可以添加更多模型类型
        # elif model_type.lower() == 'other_model':
        #     return OtherModelProcessor(model_path)
        else:
            return None
    
    @staticmethod
    def detect_model_type(model_path: str) -> Optional[str]:
        """
        根据文件名检测模型类型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            模型类型字符串，如果无法识别则返回 None
        """
        import os
        filename = os.path.basename(model_path).upper()
        
        if filename.startswith('RMBG'):
            return 'rmbg'
        # 未来可以添加更多模型类型的检测
        # elif filename.startswith('OTHER'):
        #     return 'other_model'
        
        return None
