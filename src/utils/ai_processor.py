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
    
    def process(self, image: np.ndarray, progress_callback=None, cancel_check=None) -> np.ndarray:
        """
        处理图像，去除背景
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            progress_callback: 进度回调函数，接收 0-100 的进度值
            cancel_check: 取消检查函数，返回True表示应该取消处理
            
        Returns:
            去除背景后的图像 (H, W, 3) RGB 格式
        """
        return self.process_with_parameters(image, progress_callback=progress_callback, cancel_check=cancel_check)
    
    def process_with_parameters(
        self,
        image: np.ndarray,
        threshold_mode: str = 'auto',
        manual_threshold: int = 127,
        edge_feather: bool = True,
        feather_strength: float = 0.5,
        background_color: str = 'white',
        progress_callback=None,
        cancel_check=None
    ) -> np.ndarray:
        """
        使用指定参数处理图像，去除背景
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            threshold_mode: 阈值模式 ('auto' 或 'manual')
            manual_threshold: 手动阈值 (0-255)
            edge_feather: 是否启用边缘羽化
            feather_strength: 羽化强度 (0.0-1.0)
            background_color: 背景颜色 ('white', 'black', 'transparent')
            progress_callback: 进度回调函数，接收 0-100 的进度值
            cancel_check: 取消检查函数，返回True表示应该取消处理
            
        Returns:
            处理后的图像 (H, W, 3 或 H, W, 4) RGB/RGBA 格式
        """
        if not self.is_loaded:
            raise RuntimeError("模型未加载，请先调用 load_model()")
        
        import cv2
        
        # 检查是否需要取消
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        # 保存原始尺寸
        original_h, original_w = image.shape[:2]
        
        if progress_callback:
            progress_callback(50)
        
        # 预处理
        input_tensor = self._preprocess(image)
        
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        if progress_callback:
            progress_callback(60)
        
        # 推理（这是最耗时的部分，无法中断）
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        mask = self.session.run([output_name], {input_name: input_tensor})[0]
        
        # 推理完成后立即检查取消
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        if progress_callback:
            progress_callback(70)
        
        # 后处理
        mask = self._postprocess(mask, (original_h, original_w))
        
        if progress_callback:
            progress_callback(80)
        
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        # 1. 阈值处理
        if threshold_mode == 'manual':
            # 使用手动阈值
            _, mask_binary = cv2.threshold(mask, manual_threshold, 255, cv2.THRESH_BINARY)
        else:
            # 使用 Otsu 自动阈值
            _, mask_binary = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        # 2. 边缘羽化
        if edge_feather:
            # 将二值掩码转换为浮点
            mask_float = mask_binary.astype(np.float32) / 255.0
            
            # 使用原始掩码的软边缘信息
            mask_soft = mask.astype(np.float32) / 255.0
            
            # 检测边缘
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            edges = cv2.Canny(mask_binary, 50, 150)
            # 根据羽化强度调整边缘扩展
            dilation_size = max(1, int(feather_strength * 5))
            edges_dilated = cv2.dilate(edges, kernel, iterations=dilation_size)
            edge_mask = (edges_dilated > 0).astype(np.float32)
            
            # 混合硬掩码和软掩码
            final_mask = mask_float * (1 - edge_mask) + mask_soft * edge_mask
            
            # 根据羽化强度调整高斯模糊
            blur_size = max(1, int(feather_strength * 5))
            if blur_size % 2 == 0:
                blur_size += 1
            sigma = feather_strength * 2
            final_mask = cv2.GaussianBlur(final_mask, (blur_size, blur_size), sigma)
        else:
            # 不羽化，直接使用二值掩码
            final_mask = mask_binary.astype(np.float32) / 255.0
        
        if cancel_check and cancel_check():
            raise RuntimeError("处理已取消")
        
        # 3. 应用背景颜色
        if background_color == 'transparent':
            # 创建 RGBA 图像
            result = np.zeros((original_h, original_w, 4), dtype=np.uint8)
            result[:, :, :3] = image
            result[:, :, 3] = (final_mask * 255).astype(np.uint8)
        else:
            # 将掩码扩展为 3 通道
            mask_3ch = np.stack([final_mask, final_mask, final_mask], axis=2)
            
            # 确定背景颜色值
            if background_color == 'black':
                bg_value = 0.0
            else:  # white
                bg_value = 255.0
            
            # 应用掩码
            result = image.astype(np.float32) * mask_3ch + bg_value * (1 - mask_3ch)
            result = result.astype(np.uint8)
        
        if progress_callback:
            progress_callback(95)
        
        return result
    
    def unload_model(self):
        """卸载模型，释放资源"""
        if self.session is not None:
            self.session = None
        self.is_loaded = False


class SuperResProcessor(AIProcessor):
    """
    Real-ESRGAN 超分辨率处理器
    
    使用 Real-ESRGAN 模型进行图像超分辨率放大。
    """
    
    def __init__(self, model_path: str, scale: int = 4):
        """
        初始化超分辨率处理器
        
        Args:
            model_path: Real-ESRGAN 模型文件路径（.onnx）
            scale: 放大倍数（默认 4x）
        """
        super().__init__(model_path)
        self.session = None
        self.scale = scale
        self.input_size = 128  # 模型固定输入尺寸
        self.tile_pad = 10  # 块边界填充，避免接缝
    
    def load_model(self, progress_callback=None) -> bool:
        """
        加载 Real-ESRGAN ONNX 模型
        
        Args:
            progress_callback: 可选的进度回调函数，接收 0-100 的进度值
        
        Returns:
            True 如果加载成功，否则 False
        """
        try:
            import onnxruntime as ort
            import os
            
            # 设置日志级别
            ort.set_default_logger_severity(3)
            
            if progress_callback:
                progress_callback(10)
            
            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                print(f"模型文件不存在: {self.model_path}")
                return False
            
            if progress_callback:
                progress_callback(30)
            
            # 创建 ONNX Runtime 会话
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=['CPUExecutionProvider']
            )
            
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
            print(f"加载 Real-ESRGAN 模型失败: {e}")
            self.is_loaded = False
            return False
    
    def _preprocess_tile(self, tile: np.ndarray) -> np.ndarray:
        """
        预处理图像块
        
        Args:
            tile: 输入图像块 (H, W, 3) RGB
            
        Returns:
            预处理后的图像块 (1, 3, H, W) 归一化到 [0, 1]
        """
        # 转换为 float32 并归一化到 [0, 1]
        normalized = tile.astype(np.float32) / 255.0
        
        # 转换为 (1, 3, H, W) 格式
        transposed = np.transpose(normalized, (2, 0, 1))
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def _postprocess_tile(self, output: np.ndarray) -> np.ndarray:
        """
        后处理图像块
        
        Args:
            output: 模型输出 (1, 3, H, W)
            
        Returns:
            处理后的图像块 (H, W, 3) RGB，float32 [0, 255]
        """
        # 移除批次维度并转换为 (H, W, 3)
        output = output.squeeze(0)
        output = np.transpose(output, (1, 2, 0))
        
        # 转换到 [0, 255] 范围（保持 float32）
        output = np.clip(output, 0, 1) * 255
        
        return output
    
    def _process_tile(self, tile: np.ndarray) -> tuple:
        """
        处理单个图像块（固定128x128输入，固定512x512输出）
        
        Args:
            tile: 输入图像块 (H, W, 3) RGB，任意尺寸
            
        Returns:
            (output, actual_h, actual_w): 
                - output: 放大后的图像块 (H*scale, W*scale, 3)
        """
        import cv2
        
        original_h, original_w = tile.shape[:2]
        target_output_h = original_h * self.scale
        target_output_w = original_w * self.scale
        
        # Resize到模型要求的尺寸
        if original_h != self.input_size or original_w != self.input_size:
            tile_resized = cv2.resize(
                tile, 
                (self.input_size, self.input_size),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            tile_resized = tile
        
        # 预处理
        input_tensor = self._preprocess_tile(tile_resized)
        
        # 推理（输入128x128，输出512x512）
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        output = self.session.run([output_name], {input_name: input_tensor})[0]
        
        # 后处理（得到512x512的输出）
        result = self._postprocess_tile(output)
        
        # Resize到目标输出尺寸
        if result.shape[0] != target_output_h or result.shape[1] != target_output_w:
            result = cv2.resize(
                result,
                (target_output_w, target_output_h),
                interpolation=cv2.INTER_LINEAR
            )
        
        return result
    
    def process(self, image: np.ndarray, progress_callback=None, cancel_check=None) -> np.ndarray:
        """
        处理图像，进行超分辨率放大
        
        参考Real-ESRGAN的tile_process方法
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            progress_callback: 进度回调函数，接收 0-100 的进度值
            cancel_check: 取消检查函数，返回True表示应该取消处理
            
        Returns:
            放大后的图像 (H*scale, W*scale, 3) RGB 格式
        """
        if not self.is_loaded:
            raise RuntimeError("模型未加载，请先调用 load_model()")
        
        import math
        
        h, w = image.shape[:2]
        tile_size = self.input_size  # 128
        tile_pad = self.tile_pad  # 10
        
        # 创建输出图像
        output_h = h * self.scale
        output_w = w * self.scale
        output = np.zeros((output_h, output_w, 3), dtype=np.float32)
        
        # 计算需要多少块
        tiles_x = math.ceil(w / tile_size)
        tiles_y = math.ceil(h / tile_size)
        total_tiles = tiles_x * tiles_y
        
        # 处理每个块
        processed_tiles = 0
        for y in range(tiles_y):
            for x in range(tiles_x):
                # 检查是否需要取消
                if cancel_check and cancel_check():
                    raise RuntimeError("处理已取消")
                
                # 计算tile在输入图像上的位置（不含填充）
                input_start_x = x * tile_size
                input_end_x = min(input_start_x + tile_size, w)
                input_start_y = y * tile_size
                input_end_y = min(input_start_y + tile_size, h)
                
                # 计算tile的实际尺寸（不含填充）
                input_tile_width = input_end_x - input_start_x
                input_tile_height = input_end_y - input_start_y
                
                # 计算带填充的tile位置
                input_start_x_pad = max(input_start_x - tile_pad, 0)
                input_end_x_pad = min(input_end_x + tile_pad, w)
                input_start_y_pad = max(input_start_y - tile_pad, 0)
                input_end_y_pad = min(input_end_y + tile_pad, h)
                
                # 提取带填充的tile
                input_tile = image[input_start_y_pad:input_end_y_pad, 
                                 input_start_x_pad:input_end_x_pad].copy()
                
                # 处理tile（返回对应放大尺寸的输出）
                output_tile = self._process_tile(input_tile)
                
                # 计算输出图像上的位置（参考Real-ESRGAN原实现）
                output_start_x = input_start_x * self.scale
                output_end_x = input_end_x * self.scale
                output_start_y = input_start_y * self.scale
                output_end_y = input_end_y * self.scale
                
                # 计算在输出tile中的裁剪位置（去除填充部分）
                pad_left = input_start_x - input_start_x_pad
                pad_top = input_start_y - input_start_y_pad
                
                output_start_x_tile = pad_left * self.scale
                output_end_x_tile = output_start_x_tile + input_tile_width * self.scale
                output_start_y_tile = pad_top * self.scale
                output_end_y_tile = output_start_y_tile + input_tile_height * self.scale
                
                # 从输出tile中提取核心区域并放入最终输出
                core_region = output_tile[
                    output_start_y_tile:output_end_y_tile,
                    output_start_x_tile:output_end_x_tile
                ]
                
                output[output_start_y:output_end_y, 
                      output_start_x:output_end_x] = core_region
                
                # 更新进度
                processed_tiles += 1
                if progress_callback:
                    progress = 50 + int((processed_tiles / total_tiles) * 45)
                    progress_callback(progress)
        
        # 转换为 uint8
        output = np.clip(output, 0, 255).astype(np.uint8)
        
        if progress_callback:
            progress_callback(95)
        
        return output
    
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
    def create_processor(model_type: str, model_path: str, **kwargs) -> Optional[AIProcessor]:
        """
        创建 AI 处理器
        
        Args:
            model_type: 模型类型（'rmbg', 'superres', ...）
            model_path: 模型文件路径
            **kwargs: 额外参数
            
        Returns:
            AI 处理器实例，如果类型不支持则返回 None
        """
        if model_type.lower() == 'rmbg':
            return RMBGProcessor(model_path)
        elif model_type.lower() == 'superres':
            scale = kwargs.get('scale', 4)
            return SuperResProcessor(model_path, scale=scale)
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
        elif 'ESRGAN' in filename or 'SUPERRES' in filename:
            return 'superres'
        
        return None
